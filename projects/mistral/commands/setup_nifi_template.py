import json
from typing import Any, Dict, List, Optional

import requests
import typer
from controller import log
from controller.app import Application

NIFI_API_URI = "http://localhost:8070/nifi-api"


def get_nifi_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_url = f"{NIFI_API_URI}/access/token"
    username = Application.env.get("NIFI_USERNAME")
    pw = Application.env.get("NIFI_PASSWORD")
    params = f"username={username},&password={pw}"
    r = requests.post(token_url, data=params, headers=headers)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: Status: {r.status_code}, Response: {r.text}"
        )
        return None
    return r.text()


@Application.app.command(help="set up an istanced nifi template")
def setup_nifi_template(
    template: str = typer.Argument(
        ...,
        help="Name of the template to setup",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        help="Name of the parameter context to applye",
    ),
) -> None:
    Application.print_command(
        # Application.serialize_parameter("--force", force, IF=force),
    )
    Application.get_controller().controller_init()

    # check if an access token is needed
    access_url = f"{NIFI_API_URI}/access/config"
    r = requests.get(access_url)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: Status: {r.status_code}, Response: {r.text}"
        )
        return
    res = r.json()
    headers = {}
    if res["config"]["supportsLogin"] is True:
        token = get_nifi_token()
        if not token:
            log.error("Fail in getting the access token")
            return
        headers = {"Authorization": f"Bearer {token}"}
        log.info("Access token successfully retrieved")

    # get the process-group id of the selected template
    resources_url = f"{NIFI_API_URI}/resources"
    r = requests.get(resources_url, headers=headers)
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

    if context:
        # get all the parameter contexts
        context_url = f"{NIFI_API_URI}/flow/parameter-contexts"
        r = requests.get(context_url, headers=headers)
        if r.status_code != 200:
            log.error(
                f"Error in accessing parameter contexts list: Status: {r.status_code}, Response: {r.text}"
            )
            return
        context_list = r.json()
        # get the chosen parameter context
        context_el: Optional[Dict[str, str]] = None
        for el in context_list["parameterContexts"]:
            if el["component"]["name"] == context:
                context_el = el
                break
        if not context_el:
            log.error(f"No parameter context with name '{context}' was found")
            return
        process_group_entities: List[Dict[str, Any]] = []
        # get the process group entity of the template main process group
        p_group_url = f"{NIFI_API_URI}{process_group['identifier']}"
        r = requests.get(p_group_url, headers=headers)
        if r.status_code != 200:
            log.error(
                f"Error in getting process group entity of the tempolate process group: Status: {r.status_code}, Response: {r.text}"
            )
            return
        process_group_entities.append(r.json())

        # get all the process groups entities contained in the template
        process_groups_url = (
            f"{NIFI_API_URI}{process_group['identifier']}/process-groups"
        )
        r = requests.get(process_groups_url, headers=headers)
        if r.status_code != 200:
            log.error(
                f"Error in accessing process group children list: Status: {r.status_code}, Response: {r.text}"
            )
            return
        res = r.json()
        for el in res["processGroups"]:
            process_group_entities.append(el)

        # assign the chosen parameter context at all process groups
        p_group_header = {**headers}
        p_group_header["Content-Type"] = "application/json"
        for p_group in process_group_entities:
            body = p_group
            # assign the id of the chosen parameter context
            body["component"]["parameterContext"] = {}
            body["component"]["parameterContext"]["id"] = context_el["id"]
            data = json.dumps(body)
            r = requests.put(p_group["uri"], data=data, headers=p_group_header)
            if r.status_code != 200:
                log.error(
                    f"Error in setting the parameter context: Status: {r.status_code}, Response: {r.text}"
                )
                return
        log.info(
            f"Parameter context '{context}' successfully assigned to all template '{template}' process groups"
        )

    log.info("Setup controllers")
    # get all the controllers of the template
    get_controller_url = (
        f"{NIFI_API_URI}/flow{process_group['identifier']}/controller-services"
    )
    r = requests.get(get_controller_url, headers=headers)
    if r.status_code != 200:
        log.error(
            f"Error in accessing template controller list: Status: {r.status_code}, Response: {r.text}"
        )
        return
    res = r.json()
    controllers_id_list: List[str] = []
    for el in res["controllerServices"]:
        if el["parentGroupId"] in process_group["identifier"]:
            # the controller is used in the specified template
            controllers_id_list.append(el["id"])

    controller_header = {**headers}
    controller_header["Content-Type"] = "application/json"
    for c_id in controllers_id_list:
        # check the status
        controller_url = f"{NIFI_API_URI}/controller-services/{c_id}"
        r = requests.get(controller_url, headers=headers)
        if r.status_code != 200:
            log.error(
                f"Error in accessing the controller element: Status: {r.status_code}, Response: {r.text}"
            )
            return
        controller_el = r.json()
        to_update = False
        if controller_el["status"]["validationStatus"] == "INVALID":
            to_update = True
            # check the passwords
            log.info(f"Checking passwords for {controller_el['component']['name']}")
            password_params: Dict[str, str] = {}
            for p, values in controller_el["component"]["properties"].items():
                if "password" in p.lower():
                    new_p = typer.prompt(
                        f"Value for '{p}' in {controller_el['component']['name']} ? (type q to skip)"
                    )
                    if new_p != "q":
                        password_params[p] = new_p
            # apply the changes
            if password_params:

                if controller_el["status"]["runStatus"] != "DISABLED":
                    # controller status has to be set to disabled in order to be allowed to modify its properties
                    status_body = {
                        "revision": controller_el["revision"],
                        "state": "DISABLED",
                    }
                    status_url = f"{NIFI_API_URI}/controller-services/{c_id}/run-status"
                    dis_r = requests.put(
                        status_url,
                        data=json.dumps(status_body),
                        headers=controller_header,
                    )
                    if dis_r.status_code != 200:
                        log.error(
                            f"Error in disabling the controller element to update the passwords: Status: {r.status_code}, Response: {r.text}"
                        )
                        return
                    controller_el = dis_r.json()

                controller_el["component"]["properties"] = password_params
                r = requests.put(
                    controller_url,
                    data=json.dumps(controller_el),
                    headers=controller_header,
                )
                if r.status_code != 200:
                    log.error(
                        f"Error in updating {controller_el['component']['name']} : Status: {r.status_code}, Response: {r.text}"
                    )
                    return
                log.info(
                    f"Passwords for {controller_el['component']['name']} successfully updated"
                )
        if to_update:
            # update the controller element
            controller_el = r.json()
            # check if the problem is solved
            if controller_el["status"]["validationStatus"] == "INVALID":
                log.warning(
                    f"Validation problems with controller {controller_el['component']['name']} (id: {controller_el['component']['id']}):{controller_el['component']['validationErrors']}."
                )
                log.warning("Enabling Skipped")
                continue
        if controller_el["status"]["runStatus"] == "DISABLED":
            log.info(f"Enabling {controller_el['component']['name']}")
            status_body = {"revision": controller_el["revision"], "state": "ENABLED"}
            status_url = f"{NIFI_API_URI}/controller-services/{c_id}/run-status"
            r = requests.put(
                status_url, data=json.dumps(status_body), headers=controller_header
            )
            if r.status_code != 200:
                log.error(
                    f"Error in enabling the controller element: Status: {r.status_code}, Response: {r.text}"
                )
                return

    log.info("Controllers successfully set up")
