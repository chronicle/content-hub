from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.AWSS3Manager import AWSS3Manager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import AWSS3PathException

SCRIPT_NAME = "UploadFile"


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

    bucket_file_path = extract_action_param(
        siemplify, param_name="Bucket Upload Path", is_mandatory=True, print_value=True
    )
    upload_path = extract_action_param(
        siemplify, param_name="File Path", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {}

    bucket_name, bucket_filename = AWSS3Manager.parse_bucket_file_path(bucket_file_path)

    try:
        siemplify.LOGGER.info("Connecting to AWSS3 Service")
        s3_client = AWSS3Manager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        s3_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWSS3 service")

        siemplify.LOGGER.info(f"Uploading file {upload_path} to AWS S3")
        s3_client.upload_file(
            bucket_file_path=bucket_file_path, upload_file_path=upload_path
        )
        siemplify.LOGGER.info(
            f"Successfully uploaded {upload_path} to AWS S3 {bucket_name} bucket"
        )
        output_message += (
            f"Successfully uploaded {upload_path} to AWS S3 {bucket_name} bucket"
        )

        json_results = {
            "bucket_upload_path": bucket_file_path,
            "file_path": upload_path,
        }

    except AWSS3PathException as error:
        result_value = "false"
        siemplify.LOGGER.error(
            f"Action wasn’t able to upload {upload_path} from AWS S3 {bucket_name} "
            f"bucket. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        output_message += (
            f"Action wasn’t able to upload {upload_path} from AWS S3 {bucket_name} "
            f"bucket. Reason: {error}"
        )

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action 'Upload File From Bucket'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Error executing action 'Upload File From Bucket'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
