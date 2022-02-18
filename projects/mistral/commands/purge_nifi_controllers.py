import json
from typing import Any, Dict, Optional

import requests
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
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return None
    return r.text()


@Application.app.command(help="delete all the unused controller services")
def purge_nifi_controllers() -> None:
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

    # get the list of nifi resources
    resources_url = f"{NIFI_API_URI}/resources"
    r = requests.get(resources_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return
    resources = r.json()
    # get the id of the main nifi process group
    process_group: Optional[Dict[str, Any]] = None
    for el in resources["resources"]:
        if "process-group" in el["identifier"] and el["name"] == "NiFi Flow":
            process_group = el
            break
    if not process_group:
        log.error("No main Nifi process group was found in the resources list")
        return

    # get the controller services
    get_controller_url = (
        f"{NIFI_API_URI}/flow{process_group['identifier']}/controller-services"
    )
    r = requests.get(get_controller_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing controller list: Status: {r.status_code}, Response: {r.text}"
        )
        return
    res = r.json()
    controller_header = {**headers}
    controller_header["Content-Type"] = "application/json"
    for el in res["controllerServices"]:
        if len(el["component"]["referencingComponents"]) == 0:
            revision = el["revision"]
            # check if the controller is disabled
            if el["status"]["runStatus"] != "DISABLED":
                # disable the component
                status_body = {
                    "revision": revision,
                    "state": "DISABLED",
                }
                status_url = f"{NIFI_API_URI}/controller-services/{el['id']}/run-status"
                dis_r = requests.put(
                    status_url,
                    data=json.dumps(status_body),
                    headers=controller_header,
                    verify=False,
                )
                if dis_r.status_code != 200:
                    log.warning(
                        f"Error in disabling the controller element (id:{el['id']}): Status: {dis_r.status_code}, Response: {dis_r.text}"
                    )
                    return
                dis_res = dis_r.json()
                # update the revision
                revision = dis_res["revision"]
            # delete the controller
            delete_url = f"{el['uri']}?version={revision['version']}"
            del_r = requests.delete(delete_url, headers=headers, verify=False)
            if del_r.status_code != 200:
                log.error(
                    f"Error in deleting controller named {el['component']['name']} (id: {el['id']}): Status: {del_r.status_code}, Response: {del_r.text}"
                )
                return
            else:
                log.info(
                    f"Controller named {el['component']['name']} (id: {el['id']}) successfully deleted"
                )
