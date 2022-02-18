from pathlib import Path
from typing import Dict, List, Optional

import requests
import typer
from controller import PROJECT_DIR, log
from controller.app import Application, Configuration

if Configuration.production:
    NIFI_API_URI = "https://localhost:8070/nifi-api"
else:
    NIFI_API_URI = "http://localhost:8070/nifi-api"


def get_nifi_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": Configuration.hostname,
    }
    token_url = f"{NIFI_API_URI}/access/token"
    username = Application.env.get("NIFI_USERNAME")
    pw = Application.env.get("NIFI_PASSWORD")
    params = f"username={username},&password={pw}"
    r = requests.post(token_url, data=params, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return None
    return r.text()


@Application.app.command(help="save nifi templates in the versioned folder")
def save_nifi_template(
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Name of the template to save",
        show_default=False,
    ),
) -> None:
    Application.print_command(
        # Application.serialize_parameter("--force", force, IF=force),
    )
    Application.get_controller().controller_init()

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

    # get the template list
    resources_url = f"{NIFI_API_URI}/resources"
    r = requests.get(resources_url, headers=headers, verify=False)
    if r.status_code != 200:
        log.error(
            f"Error in accessing Nifi API: status {r.status_code}, response {r.text}"
        )
        return
    resources = r.json()
    templates: Optional[List[Dict[str, str]]] = []
    for el in resources["resources"]:
        if "templates" in el["identifier"] and "policies" not in el["identifier"]:
            if template:
                # get only the requested template
                if el["name"] == template:
                    templates.append(el)
                    break
            else:
                templates.append(el)
    if not templates:
        if template:
            log.warning(f"Template '{template}' not found")
        log.info("No templates found to save")
        return

    template_dir = PROJECT_DIR.joinpath(Configuration.project, "nifi", "templates")

    for t in templates:
        # choose the file name
        filename = typer.prompt(
            f"Name of the file (without the extension) for '{t['name']}' template ?"
        )
        export_file = Path(template_dir, f"{filename}.xml")
        # download the template
        download_url = f'{NIFI_API_URI}{t["identifier"]}/download'
        t_request = requests.get(download_url, headers=headers, verify=False)
        # save the template
        with open(export_file, "w") as fileout:
            fileout.write(t_request.text)
        log.info(f"Template '{t['name']}' successfully saved in {export_file}")
