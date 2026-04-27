from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.LogPointManager import LogPointManager
from ..core.consts import INTEGRATION_NAME, LIST_REPOS, MIN_REPOS, REPOS_TABLE
from ..core.exceptions import LogPointInvalidParametersException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_REPOS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    ip_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret",
        is_mandatory=True,
    )

    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    max_repos = extract_action_param(
        siemplify,
        param_name="Max Repos To Return",
        print_value=True,
        input_type=int,
        default_value=100,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""

    try:
        if max_repos < MIN_REPOS:
            raise LogPointInvalidParametersException(
                f"'Max Repos To Return' must be an integer greater or equals "
                f"to '{MIN_REPOS}'"
            )

        manager = LogPointManager(
            ip_address=ip_address,
            username=username,
            secret=secret,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(f"Fetching Repos from {INTEGRATION_NAME}")
        repos = manager.list_repos(max_repos_to_return=max_repos)
        siemplify.LOGGER.info(f"Successfully fetched Repos from {INTEGRATION_NAME}")

        json_results = [repo.as_json() for repo in repos]
        csv_list = [repo.as_csv() for repo in repos]

        if json_results:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(REPOS_TABLE, construct_csv(csv_list))

        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message += "Successfully retrieve available repos query from Logpoint"

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {LIST_REPOS} Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
