from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifySdkConfig import SiemplifySdkConfig
from ..core.RunnersManager import RunnersManagerBuilder, PermissionError


@output_handler
def main():
    siemplify = SiemplifyAction()
    command = siemplify.parameters["Command"]
    username = siemplify.parameters["Username"]
    password = siemplify.parameters["Password"]
    domain = siemplify.parameters.get("Domain")
    daemon = siemplify.parameters["Daemon"].lower() == "true"

    run_as_manager = RunnersManagerBuilder.create_manager(SiemplifySdkConfig.is_linux())
    try:
        return_code, stdout, stderr = run_as_manager.run_command_as_user(
            command, username, domain, password, daemon
        )
    except PermissionError as e:
        raise e
    except Exception as e:
        raise e

    if return_code:
        siemplify.end(stderr, "false")

    siemplify.end(stdout, "true")


if __name__ == "__main__":
    main()
