from __future__ import annotations
import os

from TIPCommon import extract_configuration_param, extract_action_param
from TIPCommon import validation
from TIPCommon.utils import is_empty_string_or_none
from ..core import consts
from ..core import exceptions
from ..core.GoogleCloudStorageManager import GoogleCloudStorageManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.datamodels import Blob


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{consts.INTEGRATION_NAME} - {consts.UPLOAD_OBJECT_TO_BUCKET}"
    )
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    service_account = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Service Account",
        is_mandatory=False,
    )
    workload_identity_email = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Workload Identity Email",
        is_mandatory=False,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=False,
    )
    project_id = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Project ID",
        is_mandatory=False,
        print_value=True,
    )
    quota_project_id = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Quota Project ID",
        is_mandatory=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    bucket_name = extract_action_param(
        siemplify,
        param_name="Bucket Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    object_name = extract_action_param(
        siemplify,
        param_name="Object Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    source_file_path = extract_action_param(
        siemplify,
        param_name="Source File Path",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        validator = validation.ParameterValidator(siemplify)

        if not is_empty_string_or_none(service_account):
            service_account = validator.validate_json(
                param_name="Service Account",
                json_string=service_account,
                print_value=False,
            )
        if not is_empty_string_or_none(workload_identity_email):
            workload_identity_email = validator.validate_email(
                param_name="Workload Identity Email",
                email=workload_identity_email,
                print_value=True,
            )

        manager = GoogleCloudStorageManager(
            service_account=service_account,
            workload_identity_email=workload_identity_email,
            api_root=api_root,
            project_id=project_id,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
            logger=siemplify.logger,
        )

        try:
            siemplify.LOGGER.info(
                f"Fetching bucket with name {bucket_name} from "
                f"{consts.INTEGRATION_DISPLAY_NAME}"
            )
            bucket = manager.get_bucket(bucket_name=bucket_name)
            siemplify.LOGGER.info(
                f"Successfully fetched bucket from with name {bucket_name} from "
                f"{consts.INTEGRATION_DISPLAY_NAME}"
            )
        except (
            exceptions.GoogleCloudStorageNotFoundError,
            exceptions.GoogleCloudStorageForbiddenError,
            exceptions.GoogleCloudStorageBadRequestError,
        ) as exc:
            raise exceptions.GoogleCloudStorageNotFoundError(
                f"Bucket {bucket_name} Not found."
            ) from exc

        if not os.path.exists(source_file_path):
            raise exceptions.GoogleCloudStorageNotFoundError(
                f"No such file or directory: {source_file_path}"
            )

        if os.path.isdir(source_file_path):
            raise exceptions.GoogleCloudStorageValidationException(
                "Upload source file path must be a file."
            )

        bucket_google_obj = bucket.bucket_data
        blob = bucket_google_obj.blob(object_name)

        siemplify.LOGGER.info(
            f"Uploading local file path '{source_file_path}' to '{object_name}'"
        )
        manager.upload_file(file_object=blob, upload_path=source_file_path)
        siemplify.LOGGER.info(
            f"Successfully uploaded local file path '{source_file_path}' to "
            f"'{object_name}'"
        )
        blob.reload()

        created_blob = Blob(
            id=blob.id, name=blob.name, md5_hash=blob.md5_hash, object_path=blob.path
        )
        siemplify.result.add_result_json(created_blob.as_json())

        result_value = True
        output_message = (
            f"Successfully uploaded '{source_file_path}' to bucket: {bucket_name}"
        )

    except (
        exceptions.GoogleCloudStorageNotFoundError,
        exceptions.GoogleCloudStorageValidationException,
    ) as error:
        output_message = (
            f"Action wasn't able to upload '{source_file_path}' to "
            f"{consts.INTEGRATION_DISPLAY_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(
            f"Action wasn't able to upload '{object_name}' to "
            f"{consts.INTEGRATION_DISPLAY_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{consts.UPLOAD_OBJECT_TO_BUCKET}'. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
