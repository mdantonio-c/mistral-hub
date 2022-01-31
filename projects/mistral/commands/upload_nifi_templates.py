import xml.etree.ElementTree as readXml
from typing import Any, Dict, Optional

import requests
import typer
from controller import PROJECT_DIR, log
from controller.app import Application, Configuration

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
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return None
    return r.text()


@Application.app.command(help="upload template in nifi from the versioned folder")
def upload_nifi_templates(
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-f",
        help="Overwrite the existing templates if they have the same name",
        show_default=False,
    )
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
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
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

    # get the list of nifi resources
    resources_url = f"{NIFI_API_URI}/resources"
    r = requests.get(resources_url, headers=headers)
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

    # get the list of the versioned templates
    template_dir = PROJECT_DIR.joinpath(Configuration.project, "nifi", "templates")

    upload_url = f"{NIFI_API_URI}{process_group['identifier']}/templates/upload"

    for t in template_dir.iterdir():
        if t.suffix == ".xml":
            r = requests.post(
                upload_url, files={"template": open(t, "rb")}, headers=headers
            )

        if r.status_code == 201:
            log.info(f"Template '{t.name}' uploaded successfully")
        elif r.status_code == 409 and "already exists" in r.text:
            if overwrite:
                # get the template name
                tree = readXml.parse(t)
                root = tree.getroot()
                for node in root.findall("name"):
                    template_name = node.text

                # get the template identifier
                for el in resources["resources"]:
                    if el["name"] == template_name:
                        template_id = el["identifier"]
                        break

                # delete the existing template
                delete_url = f"{NIFI_API_URI}{template_id}"
                del_r = requests.delete(delete_url, headers=headers)
                if del_r.status_code != 200:
                    log.error(
                        f"Error in delete '{t.name}' template: Status: {del_r.status_code}, Response:{del_r.text}"
                    )
                    log.error(f"Fail in Update '{t.name}' template")
                    continue
                # retry uploading the updated template
                r = requests.post(
                    upload_url, files={"template": open(t, "rb")}, headers=headers
                )
                if r.status_code != 201:
                    log.error(
                        f"Fail in Update '{t.name}' template. Status: {r.status_code}, Response: {r.text}"
                    )
                    return
                log.info(f"Template '{t.name}' updated successfully")

            else:
                log.warning(f"Template '{t.name}' cannot be uploaded: {r.text}")
        else:
            log.error(
                f"Fail in upload template '{t.name}'Status: {r.status_code}, Response: {r.text}"
            )
