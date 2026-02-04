from __future__ import annotations

import os

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import DOWNLOAD_ATTACHMENTS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import (
    AttachmentExistsException,
    FolderNotFoundException,
    ServiceNowNotFoundException,
    ServiceNowTableNotFoundException,
)
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from ..core.UtilsManager import save_attachment


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_ATTACHMENTS_SCRIPT_NAME

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
        siemplify, param_name="Table Name", print_value=True, is_mandatory=True
    )
    record_sys_id = extract_action_param(
        siemplify, param_name="Record Sys ID", print_value=True, is_mandatory=True
    )
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        print_value=True,
        is_mandatory=True,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_downloads = []
    failed_downloads = []

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = ServiceNowManager(
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

        if download_folder_path[0] != "/":
            raise FolderNotFoundException

        manager.is_exists_in_table(sys_id=record_sys_id, table_name=table_name)
        attachments_result = manager.get_attachments_info(
            table_name=table_name,
            sys_id=record_sys_id,
            download_folder_path=download_folder_path,
        )
        if not overwrite:
            existing_files = []
            for attachment in attachments_result:
                if os.path.exists(f"{download_folder_path}/{attachment.filename}"):
                    existing_files.append(attachment.filename)

            if existing_files:
                raise AttachmentExistsException(
                    "the following files already exist: \n {0}. "
                    "Please delete them or set ‘Overwrite’ action parameter to true.".format(
                        ", ".join(existing_files)
                    )
                )

        for attachment in attachments_result:
            try:
                content = manager.get_attachment_content(download_link=attachment.download_link)
                # Save attachment to given path
                save_attachment(
                    path=attachment.download_path,
                    name=attachment.filename,
                    content=content,
                )
                successful_downloads.append(attachment.filename)
            except Exception as err:
                failed_downloads.append(attachment.filename)
                siemplify.LOGGER.error(f"Failed request: Reason: {err}")
                siemplify.LOGGER.exception(err)

        if successful_downloads:
            output_message = (
                "Successfully downloaded the following attachments related to the record with Sys "
                "ID {} from table {} in ServiceNow:\n {} \n".format(
                    record_sys_id, table_name, ", ".join(successful_downloads)
                )
            )

            siemplify.result.add_result_json([
                result.to_json()
                for result in attachments_result
                if result.filename in successful_downloads
            ])

        if failed_downloads:
            output_message += (
                "Action wasn’t able to download the following attachments related to the "
                "record with Sys ID {} from table {} in ServiceNow: \n {} \n".format(
                    record_sys_id, table_name, ", ".join(failed_downloads)
                )
            )

        if not successful_downloads:
            output_message = (
                "Action wasn't able to download attachments related to the record with Sys ID "
                "{} from table {} in ServiceNow.".format(record_sys_id, table_name)
            )
            result_value = False

    except FolderNotFoundException as err:
        output_message = "Folder not found."
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except ServiceNowNotFoundException as e:
        output_message = (
            str(e)
            if isinstance(e, ServiceNowTableNotFoundException)
            else "Action wasn't able to download attachments from the record with Sys ID {sys_id} from table {table} in "
            "Service Now. Reason: Record with Sys ID {sys_id} was not found in table {table}".format(
                sys_id=record_sys_id, table=table_name
            )
        )
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as err:
        output_message = (
            f"Error executing action '{DOWNLOAD_ATTACHMENTS_SCRIPT_NAME}'. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
