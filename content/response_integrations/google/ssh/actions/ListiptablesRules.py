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

    if "Chain" in siemplify.parameters and siemplify.parameters["Chain"]:
        chain = siemplify.parameters["Chain"]
    else:
        chain = ""

    json_results = {}
    status_code, output, error = ssh_wrapper.list_iptables_rules(chain)

    if status_code == 0:
        siemplify.result.add_data_table("Results:", output)
        json_results = {"-,Chain,Rule": output[1:]}
        results = "True"
        output_message = "Successfully Added results in CSV format"
    else:
        results = "False"
        output_message = error.read().decode("utf-8")

    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, results)


if __name__ == "__main__":
    main()
