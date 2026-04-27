from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Get Command Status"


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
    result_value = False

    # Parameters.
    commands_ids = siemplify.parameters.get("Commands IDs")
    commands_ids_list = commands_ids.split(",") if commands_ids else []

    for command_id in commands_ids_list:
        try:
            command_status = atp_manager.get_command_status(command_id)
            siemplify.result.add_data_table(
                command_id, flat_dict_to_csv(dict_to_flat(command_status))
            )
            result_value = True
        except Exception as err:
            error_message = f'Error fetching command result for command id "{command_id}", ERROR: {command_id}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = "Found status for target IDs."
    else:
        output_message = "Not found statuses for target IDs."

    if errors:
        output_message = "{0} \n \n Errors: \n {1}".format(
            output_message, "\n".join(errors)
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
