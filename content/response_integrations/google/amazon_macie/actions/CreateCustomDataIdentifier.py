from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import utils
from ..core.AmazonMacieManager import AmazonMacieManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME

SCRIPT_NAME = "Create Custom Data Identifier"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    name = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Name",
        is_mandatory=True,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Description",
        is_mandatory=False,
        print_value=True,
    )
    regex = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Regular Expression",
        is_mandatory=True,
        print_value=True,
    )

    keywords = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Keywords",
        is_mandatory=False,
        print_value=True,
    )
    ignore_words = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Ignore Words",
        is_mandatory=False,
        print_value=True,
    )
    max_match_distance = extract_action_param(
        siemplify,
        param_name="Custom Data Identifier Maximum Match Distance",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=50,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {"customDataIdentifierId": ""}

    try:
        # Split the CSVs
        keywords = (
            utils.load_csv_to_list(keywords, "Custom Data Identifier Keywords")
            if keywords
            else []
        )
        ignore_words = (
            utils.load_csv_to_list(ignore_words, "Custom Data Identifier Ignore Words")
            if ignore_words
            else []
        )

        siemplify.LOGGER.info("Connecting to Amazon Macie Service")
        manager = AmazonMacieManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to Amazon Macie service")

        try:
            siemplify.LOGGER.info(f"Creating custom data identifier {name}")
            custom_data_identifier = manager.create_custom_data_identifier(
                name=name,
                description=description,
                regex=regex,
                maximum_match_distance=max_match_distance,
                keywords=keywords,
                ignore_words=ignore_words,
            )
            siemplify.LOGGER.info(
                f"Successfully created custom data identifier {custom_data_identifier.id} in Amazon Macie"
            )
            json_results["customDataIdentifierId"] = custom_data_identifier.id
            result_value = "true"
            output_message = f"New Amazon Macie custom data identifier created: {custom_data_identifier.id}"
        except Exception as error:  # action failed
            siemplify.LOGGER.error(
                f"Failed to create Amazon Macie Identifier. Error is {error}"
            )
            siemplify.LOGGER.exception(error)
            output_message = (
                f"Failed to create Amazon Macie Identifier. Error is {error}"
            )

    except Exception as error:  # critical error
        siemplify.LOGGER.error(
            f"Failed to connect to the Amazon Macie service! Error is {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the Amazon Macie service! Error is {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
