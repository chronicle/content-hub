from __future__ import annotations

import os

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import (
    ADD_ATTACHMENT_SCRIPT_NAME,
    ADD_NEW_ATTACHMENT_MODE,
    INTEGRATION_NAME,
    OVERWRITE_EXISTING_ATTACHMENT,
)
from ..core.exceptions import ServiceNowNotFoundException, ServiceNowTableNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ATTACHMENT_SCRIPT_NAME
    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )

    default_incident_table = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Incident Table",
        print_value=True,
        default_value=DEFAULT_TABLE,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Parameters
    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True, print_value=True
    )
    record_sys_id = extract_action_param(
        siemplify, param_name="Record Sys ID", is_mandatory=True, print_value=True
    )
    file_paths_string = extract_action_param(
        siemplify, param_name="File Path", is_mandatory=True, print_value=True
    )
    file_paths = (
        [file_path.strip() for file_path in file_paths_string.split(",") if file_path]
        if file_paths_string
        else []
    )
    mode = extract_action_param(
        siemplify,
        param_name="Mode",
        print_value=True,
        default_value=ADD_NEW_ATTACHMENT_MODE,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    execution_status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_files, failed_files, successful_file_results = [], [], []

    try:
        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )
        service_now_manager.is_exists_in_table(sys_id=record_sys_id, table_name=table_name)

        for file_path in file_paths:
            try:
                if mode == OVERWRITE_EXISTING_ATTACHMENT:
                    existing_attachments = service_now_manager.get_attachments_info(
                        table_name=table_name,
                        sys_id=record_sys_id,
                        attachment_name=os.path.basename(file_path),
                        download_folder_path="tmp",
                    )
                    for existing_attachment in existing_attachments:
                        service_now_manager.delete_attachment(sys_id=existing_attachment.sys_id)

                uploaded_file = service_now_manager.upload_attachment(
                    table_name=table_name,
                    record_sys_id=record_sys_id,
                    file_path=file_path,
                )
                successful_file_results.append(uploaded_file)
                successful_files.append(file_path)
            except Exception as err:
                failed_files.append(file_path)
                siemplify.LOGGER.error(
                    f"Action was not able to process the following file: {file_path}"
                )
                siemplify.LOGGER.exception(err)

        if successful_files:
            output_message += (
                "Successfully added the following attachments to the record with Sys ID {} from table "
                "{} in Service Now: \n{}\n".format(
                    record_sys_id, table_name, "\n".join(successful_files)
                )
            )

        if failed_files:
            output_message += (
                "Action wasn't able to add the following attachments to the record with Sys ID {} "
                "from table {} in Service Now: \n{}\n".format(
                    record_sys_id, table_name, "\n".join(failed_files)
                )
            )

        if not successful_files:
            output_message = (
                "No attachments were added to the record with Sys ID {} from table "
                "{} in Service Now: \n{}\n".format(
                    record_sys_id, table_name, "\n".join(failed_files)
                )
            )
            result_value = False

        if successful_file_results:
            siemplify.result.add_result_json([
                result.to_json() for result in successful_file_results
            ])
    except ServiceNowNotFoundException as e:
        output_message = (
            str(e)
            if isinstance(e, ServiceNowTableNotFoundException)
            else "Action wasn't able to add attachments to the record with Sys ID {sys_id} from table {table} in Service "
            "Now. Reason: Record with Sys ID {sys_id} was not found in table {table}".format(
                sys_id=record_sys_id, table=table_name
            )
        )
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = f'General error performing action "Add Attachment". Reason: {e}'
        result_value = False
        execution_status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {execution_status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, execution_status)


if __name__ == "__main__":
    main()
