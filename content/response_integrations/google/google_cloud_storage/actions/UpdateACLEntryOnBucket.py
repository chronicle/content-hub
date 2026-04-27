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
from ..core.exceptions import GoogleCloudStorageInvalidParameterError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{consts.INTEGRATION_NAME} - {consts.UPDATE_AN_ACL_ENTRY_ON_BUCKET}"
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

    entity = extract_action_param(
        siemplify,
        param_name="Entity",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    role = extract_action_param(
        siemplify,
        param_name="Role",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
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

        siemplify.LOGGER.info(f"Fetching ACL of bucket with name: {bucket_name}")
        acl = manager.get_acl(bucket_name)
        siemplify.LOGGER.info(
            f"Successfully fetched ACL of bucket with name: {bucket_name}"
        )

        acl = acl.acl_data
        acl_entity = acl.get_entity(entity)

        #  Check if need to update: new_role > current_roles ?
        should_update, current_highest_role = (
            utils.should_update(acl_entity.roles, role) if acl_entity else (True, -1)
        )

        if not utils.is_entity_valid(entity):
            output_message += (
                f"Action wasn't able to update the ACL entity: '{entity}' to role: "
                f"'{role}' in bucket: '{bucket_name}'. The entity holding the "
                f"permission can be user-userId, user-emailAddress, group-groupId, "
                f"group-emailAddress, allUsers, or allAuthenticatedUsers."
            )
            status = EXECUTION_STATE_FAILED

        elif not acl.get_entity(entity):
            raise GoogleCloudStorageInvalidParameterError(
                f"Entity {entity} does not exist in the ACL of bucket {bucket_name} "
            )

        elif not should_update:
            result_value = True
            output_message += (
                f"Action wasn't able to update the ACL entity: '{entity}' to role: "
                f"'{role}' in bucket '{bucket_name}' Reason: '{current_highest_role}s'"
                f" are '{role}s'"
            )

        else:
            siemplify.LOGGER.info(
                f"Grant {role} permission to entity: {entity} ACL of bucket with "
                f"name: {bucket_name}"
            )

            # Revoke previous roles
            current_roles_set = set(acl.entities.get(entity).roles)
            for curr_role in current_roles_set:
                acl.entity(entity).revoke(curr_role)

            acl.entity(entity).grant(role)

            siemplify.LOGGER.info(
                f"Save updated ACL of bucket with name: {bucket_name} "
            )
            manager.update_acl(acl=acl)
            siemplify.LOGGER.info(
                f"Successfully Saved updated ACL of bucket with name: {bucket_name}"
            )

            output_message += (
                f"Successfully updated ACL entity: '{entity}' to role: '{role}' "
                f"in bucket: '{bucket_name}'"
            )

            result_value = True

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{consts.UPDATE_AN_ACL_ENTRY_ON_BUCKET}'. "
            f"Reason: {error}"
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
