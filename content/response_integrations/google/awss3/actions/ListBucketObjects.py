from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.AWSS3Manager import AWSS3Manager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import AWSS3StatusCodeException

SCRIPT_NAME = "ListBucketObjects"
DEFAULT_MAX_BUCKET_OBJECTS = 50


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

    bucket_name = extract_action_param(
        siemplify, param_name="Bucket Name", is_mandatory=True, print_value=True
    )
    bucket_name = bucket_name.lower()

    max_objects_to_return = extract_action_param(
        siemplify,
        param_name="Max Objects to Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_BUCKET_OBJECTS,
    )

    if max_objects_to_return < 0:
        max_objects_to_return = DEFAULT_MAX_BUCKET_OBJECTS
        siemplify.LOGGER.info(
            "Max Objects to Return parameter is negative. Using default Max Objects "
            f"to Return parameter of {DEFAULT_MAX_BUCKET_OBJECTS}"
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWSS3 Service")
        s3_client = AWSS3Manager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        s3_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWSS3 service")

        siemplify.LOGGER.info(
            f"Fetching list of bucket objects for bucket {bucket_name}"
        )
        bucket_contents = s3_client.list_bucket_objects(
            bucket_name=bucket_name, max_objects_to_return=max_objects_to_return
        )
        siemplify.LOGGER.info(
            f"Successfully returned objects of the {bucket_name} bucket in AWS S3"
        )
        output_message += (
            f"Successfully returned objects of the {bucket_name} bucket in AWS S3"
        )

        json_results["Contents"] = []
        for content in bucket_contents:
            json_results["Contents"].append(content.to_dict())
        siemplify.result.add_data_table(
            title=f"{bucket_name} Bucket Objects",
            data_table=construct_csv([content.to_csv() for content in bucket_contents]),
        )

    except AWSS3StatusCodeException as error:
        result_value = "false"
        siemplify.LOGGER.error(
            f"”Action wasn’t able to return objects of the {bucket_name} bucket in "
            "AWS S3"
        )
        siemplify.LOGGER.exception(error)
        output_message += (
            f"”Action wasn’t able to return objects of the {bucket_name} bucket in "
            "AWS S3"
        )

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action 'List Bucket Objects'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Error executing action 'List Bucket Objects'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
