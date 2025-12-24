from __future__ import annotations

from requests import HTTPError
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DockerHubManager import DockerHub

INTEGRATION_NAME = "Docker Hub"
SCRIPT_NAME = "Invite User"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    output_message = ""
    result_value = False
    status = EXECUTION_STATE_FAILED
    conf = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    username = conf["Username"]
    password = conf["Password"]

    try:
        docker_client = DockerHub(
            username=username,
            password=password,
            delete_creds=True,
        )
        docker_client.test_connectivity()
    except HTTPError as e:
        if "404 Client Error" in str(e):
            pass
        else:
            raise

    siemplify.end("success", True)


if __name__ == "__main__":
    main()
