from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from TIPCommon import validation
from TIPCommon.utils import is_empty_string_or_none
from ..core import consts
from ..core.GoogleCloudStorageManager import GoogleCloudStorageManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.exceptions import GoogleCloudStorageBadRequestError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{consts.INTEGRATION_NAME} - {consts.LIST_BUCKET_OBJECTS}"
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
    max_objects_to_return = extract_action_param(
        siemplify,
        param_name="Max Objects to Return",
        is_mandatory=False,
        print_value=True,
        default_value=50,
        input_type=int,
    )
    retrieve_acl = extract_action_param(
        siemplify,
        param_name="Retrieves the Access Control List of an object",
        is_mandatory=False,
        print_value=True,
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {"Objects": []}
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

        if max_objects_to_return < consts.MIN_LIST_SIZE:
            siemplify.LOGGER.info(
                f"'Max Objects to Return' value must be equals or greater than: "
                f"{consts.MIN_LIST_SIZE}. The default value: {consts.DEFAULT_PAGE_SIZE}"
                f" will be assigned instead"
            )
            max_objects_to_return = consts.DEFAULT_PAGE_SIZE

        siemplify.LOGGER.info(
            f"Fetching buckets objects from {consts.INTEGRATION_DISPLAY_NAME}"
        )
        objects = manager.list_buckets_objects(
            bucket_name=bucket_name,
            max_objects_to_return=max_objects_to_return,
            retrieve_acl=retrieve_acl,
        )
        siemplify.LOGGER.info(
            f"Successfully fetched buckets objects from "
            f"{consts.INTEGRATION_DISPLAY_NAME}"
        )

        for obj in objects:
            json_results["Objects"].append(obj.as_json())

        if json_results["Objects"]:
            convert_dict_to_json_result_dict(json_results)
            siemplify.result.add_result_json(json_results)

        result_value = True
        output_message = (
            f"Successfully returned objects of the '{bucket_name}' bucket in "
            f"{consts.INTEGRATION_DISPLAY_NAME}."
        )

    except GoogleCloudStorageBadRequestError as error:
        output_message = (
            f"Action wasn't able to return objects of the '{bucket_name}' bucket in "
            f"{consts.INTEGRATION_DISPLAY_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.info(
            f"Action wasn't able to return objects of the '{bucket_name}' bucket in "
            f"{consts.INTEGRATION_DISPLAY_NAME}. Reason: {error}"
        )

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {consts.LIST_BUCKET_OBJECTS}. Reason: {error}"
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
