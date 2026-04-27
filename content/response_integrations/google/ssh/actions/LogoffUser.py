from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import *
from ..core.SshManager import SshManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    server = siemplify.parameters.get("Remote Server")
    username = siemplify.parameters.get("Remote Username")
    password = siemplify.parameters.get("Remote Password")
    port = (
        int(siemplify.parameters.get("Remote Port"))
        if siemplify.parameters.get("Remote Port")
        else 22
    )
    ssh_wrapper = SshManager(server, username, password, port)

    username = siemplify.parameters["Logoff Username"]
    status_code = ssh_wrapper.logoff_user(username)

    if status_code == 0:
        results = "True"
        output_message = f"Successfully logged off: {username}"
    else:
        results = "False"
        output_message = f"Failed to log off: {username}"
    siemplify.end(output_message, results)


if __name__ == "__main__":
    main()
