import json
from typing import Any, Dict, List, Optional

import requests
import typer
from controller import log
from controller.app import Application, Configuration


def get_nifi_api_uri():
    if Configuration.production:
        return "https://localhost:8070/nifi-api"
    else:
        return "http://localhost:8070/nifi-api"


def get_nifi_token():
    NIFI_API_URI = get_nifi_api_uri()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": Configuration.hostname,
    }
    token_url = f"{NIFI_API_URI}/access/token"
    username = Application.env.get("NIFI_USERNAME")
    pw = Application.env.get("NIFI_PASSWORD")
    params = f"username={username}&password={pw}"
    r = requests.post(token_url, data=params, headers=headers, verify=False)
    if r.status_code != 201:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return None
    return r.text


@Application.app.command(help="disable all the controllers of a specific template")
def disable_nifi_controllers(
    template: str = typer.Argument(
        ...,
        help="Name of the template",
    ),
) -> None:
    Application.print_command(
        # Application.serialize_parameter("--force", force, IF=force),
    )
    Application.get_controller().controller_init()
    NIFI_API_URI = get_nifi_api_uri()
    # check if an access token is needed
    access_url = f"{NIFI_API_URI}/access/config"
    headers = {"Host": Configuration.hostname}
    r = requests.get(access_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return
    res = r.json()
    if res["config"]["supportsLogin"] is True:
        token = get_nifi_token()
        if not token:
            log.error("Fail in getting the access token")
            return
        headers["Authorization"] = f"Bearer {token}"
        log.info("Access token successfully retrieved")

    # get the process-group id of the selected template
    resources_url = f"{NIFI_API_URI}/resources"
    r = requests.get(resources_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: Status: {r.status_code}, Response: {r.text}"
        )
        return
    resources = r.json()
    process_group: Optional[Dict[str, str]] = None
    for el in resources["resources"]:
        if el["name"] == template:
            process_group = el
            break
    if not process_group:
        log.error(f"No process group with name '{template}' was found")
        return

    process_groups_ids: List[str] = []
    # get the process group id of the template main process group
    p_group_url = f"{NIFI_API_URI}{process_group['identifier']}"
    r = requests.get(p_group_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in getting process group entity of the tempolate process group: Status: {r.status_code}, Response: {r.text}"
        )
        return
    res = r.json()
    process_groups_ids.append(res["id"])

    # get all the ids of the process groups contained in the template
    process_groups_url = f"{NIFI_API_URI}{process_group['identifier']}/process-groups"
    r = requests.get(process_groups_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing process group children list: Status: {r.status_code}, Response: {r.text}"
        )
        return
    res = r.json()
    for el in res["processGroups"]:
        process_groups_ids.append(el["id"])

    # get all the controllers enabled
    controllers_to_disable: Dict[str, Any] = {}
    for p_id in process_groups_ids:
        get_controller_url = (
            f"{NIFI_API_URI}/flow/process-groups/{p_id}/controller-services"
        )
        r = requests.get(get_controller_url, headers=headers, verify=False)
        if r.status_code != 200:
            log.error(
                f"Error in accessing controller list: Status: {r.status_code}, Response: {r.text}"
            )
            return
        res = r.json()
        for el in res["controllerServices"]:
            if (
                el["parentGroupId"] in process_groups_ids
                and el["status"]["runStatus"] != "DISABLED"
            ):
                # the controller is used in the specified template
                if el["id"] not in controllers_to_disable.keys():
                    controllers_to_disable[el["id"]] = el["revision"]
                    # log.debug(f"Appended {el['component']['name']}")

    if controllers_to_disable:
        # disable the controllers
        controller_header = {**headers}
        controller_header["Content-Type"] = "application/json"
        for c_id, props in controllers_to_disable.items():
            status_body = {
                "revision": props,
                "state": "DISABLED",
            }
            status_url = f"{NIFI_API_URI}/controller-services/{c_id}/run-status"
            dis_r = requests.put(
                status_url,
                data=json.dumps(status_body),
                headers=controller_header,
                verify=False,
            )
            if dis_r.status_code != 200:
                log.warning(
                    f"Error in disabling the controller element (id:{c_id}): Status: {dis_r.status_code}, Response: {dis_r.text}"
                )
                continue
            log.info(f"controller with id {c_id} successfully disabled")

    else:
        log.info("No controllers to disable were found")
