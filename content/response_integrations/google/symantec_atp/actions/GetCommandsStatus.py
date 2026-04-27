from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv

ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Get Command Status."
COMMAND_ID_TABLE_NAME = "Command - {0}"  # {0} - Command ID.


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    errors = []
    status_messages = []

    # Parameters.
    command_ids = siemplify.parameters.get("Commands IDs")
    command_ids_list = command_ids.split(",") if command_ids else []

    for command_id in command_ids_list:
        try:
            result = atp_manager.get_command_status_report_by_id(command_id)

            if result:
                result_flat = dict_to_flat(result)
                result_csv = flat_dict_to_csv(result_flat)
                siemplify.result.add_data_table(
                    COMMAND_ID_TABLE_NAME.format(command_id), result_csv
                )
                status_messages.append(result["status"].get("message"))

        except Exception as err:
            error_message = f"Error fetching command status with id: {command_id}, ERROR: {str(err)}"
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if status_messages:
        output_message = "Got status for command IDs."
    else:
        output_message = "No statuses were fetched."

    if errors:
        output_message = "{0} \n \n ERRORs: \n {1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, ",".join(status_messages))


if __name__ == "__main__":
    main()
