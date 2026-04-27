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
from ..core.datamodels import DownloadedBlob


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{consts.INTEGRATION_NAME} - {consts.DOWNLOAD_OBJECT_FROM_BUCKET}"
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
    download_path = extract_action_param(
        siemplify,
        param_name="Download Path",
        is_mandatory=True,
        print_value=True,
        default_value=consts.DEFAULT_PATH,
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
                f"Successfully fetched bucket with name {bucket_name} from "
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

        bucket_google_obj = bucket.bucket_data
        file_object = bucket_google_obj.get_blob(object_name)

        if not file_object:  # Check blob existence
            siemplify.LOGGER.info(
                f"There is no such blob with name {object_name} in the bucket "
                f"{bucket_name} "
            )
            raise exceptions.GoogleCloudStorageNotFoundError("No such object.")

        if not os.path.exists(download_path):
            raise exceptions.GoogleCloudStorageNotFoundError(
                f"No such file or directory: {download_path}"
            )

        if not os.path.isdir(download_path):
            raise exceptions.GoogleCloudStorageValidationException(
                "Download path must be a folder."
            )

        download_path = os.path.join(download_path, object_name)

        siemplify.LOGGER.info(
            f"Downloading '{object_name}' from '{bucket_name}' to '{download_path}'"
        )
        manager.download_file(file_object=file_object, download_path=download_path)
        siemplify.LOGGER.info(
            f"Successfully downloaded '{object_name}' from '{bucket_name}' "
            f"to '{download_path}'"
        )

        downloaded_blob = DownloadedBlob(
            object_name=object_name, download_path=download_path
        )
        siemplify.result.add_result_json(downloaded_blob.as_json())

        result_value = True
        output_message = (
            f"Blob {object_name} successfully downloaded to {download_path}"
        )

    except (
        exceptions.GoogleCloudStorageNotFoundError,
        exceptions.GoogleCloudStorageValidationException,
    ) as error:
        output_message = (
            f"Action wasn't able to download '{object_name}'. Reason: {error}"
        )
        siemplify.LOGGER.error(
            f"Action wasn't able to download '{object_name}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {consts.DOWNLOAD_OBJECT_FROM_BUCKET}. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
