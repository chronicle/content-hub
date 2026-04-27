from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from TIPCommon import validation
from TIPCommon.utils import is_empty_string_or_none
from ..core import consts
from ..core import utils
from ..core.GoogleCloudStorageManager import GoogleCloudStorageManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.exceptions import (
    GoogleCloudStorageBadRequestError,
    GoogleCloudStorageNotFoundError,
    GoogleCloudStorageForbiddenError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{consts.INTEGRATION_NAME} - {consts.GET_BUCKETS_ACLS}"
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

    bucket_names = extract_action_param(
        siemplify,
        param_name="Bucket Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    found_buckets = []
    not_found_buckets = []
    uniform_buckets = []
    output_message = ""

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

        bucket_names = utils.load_csv_to_list(bucket_names, "Bucket Name")

        for bucket_name in bucket_names:
            try:
                siemplify.LOGGER.info(
                    f"Fetching ACLs of bucket with name: {bucket_name}"
                )
                acl = manager.get_acl(bucket_name)
                siemplify.LOGGER.info(
                    f"Successfully fetched ACLs of bucket with name: {bucket_name}"
                )

                json_results.append(
                    {"BucketName": bucket_name, "BucketACLs": acl.as_json()}
                )

                found_buckets.append(bucket_name)

            except GoogleCloudStorageBadRequestError as error:
                uniform_buckets.append(bucket_name)
                siemplify.LOGGER.error(f"Failed to fetch bucket with name: {error}")
                siemplify.LOGGER.exception(error)
            except (
                GoogleCloudStorageNotFoundError,
                GoogleCloudStorageForbiddenError,
            ) as error:
                not_found_buckets.append(bucket_name)
                siemplify.LOGGER.error(f"Failed to find bucket with name: {error}")
                siemplify.LOGGER.exception(error)
            except Exception as error:
                raise Exception(error)

        if json_results:
            siemplify.result.add_result_json(json_results)
            output_message = (
                f"Successfully retrieved the access control list (ACL) for the Cloud "
                f"Storage buckets: {', '.join(found_buckets)}\n"
            )

        if uniform_buckets:
            output_message += (
                f"Action wasn't able to return the access control list(ACL) for the "
                f"Cloud Storage buckets {', '.join(uniform_buckets)} Reason: Cannot "
                f"get legacy ACL for a bucket that has uniform bucket-level access. "
                f"Read more at "
                f"https://cloud.google.com/storage/docs/uniform-bucket-level-access\n"
            )

        if not_found_buckets:
            output_message += (
                f"Action wasn't able to return the access control list(ACL) for the "
                f"Cloud Storage buckets: {', '.join(not_found_buckets)}\n"
            )

        result_value = True if json_results else False

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{consts.GET_BUCKETS_ACLS}'. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
