from __future__ import annotations
from TIPCommon import extract_configuration_param

from ..core.AWSS3Manager import AWSS3Manager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import AWSS3StatusCodeException

SCRIPT_NAME = "ListBuckets"


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
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = []

    try:
        siemplify.LOGGER.info("Connecting to AWSS3 Service")
        s3_client = AWSS3Manager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        s3_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWSS3 service")

        siemplify.LOGGER.info("Fetching list of buckets")
        owner, buckets = s3_client.get_list_buckets()
        siemplify.LOGGER.info("Successfully listed available buckets in AWS S3\n")
        output_message += "Successfully listed available buckets in AWS S3\n"

        json_results.append(
            {
                "Owner": owner.to_dict(),
                "Buckets": [bucket.to_dict() for bucket in buckets],
            }
        )

    except AWSS3StatusCodeException as error:
        result_value = "false"
        siemplify.LOGGER.error(
            "Action wasn’t able to list available buckets in AWS S3\n"
        )
        siemplify.LOGGER.exception(error)
        output_message += "Action wasn’t able to list available buckets in AWS S3\n"

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action 'List Buckets'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action 'List Buckets'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
