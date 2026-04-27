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

    status_code, output, error = ssh_wrapper.list_connections()
    json_results = {}

    if status_code == 0:
        json_results = {"Results": output}
        siemplify.result.add_data_table("Results:", output)
        results = "True"
        output_message = "Successfully added list of connections in CSV format"
    else:
        results = "False"
        output_message = error.read().decode("utf-8")

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, results)


if __name__ == "__main__":
    main()
