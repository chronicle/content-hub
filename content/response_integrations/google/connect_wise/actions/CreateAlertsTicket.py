from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from connect_wise.core.ConnectWiseManager import ConnectWiseManager

if TYPE_CHECKING:
    from typing import Any

    from TIPCommon.types import SingleJson


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    # Configuration.
    configuration_settings = siemplify.get_configuration("ConnectWise")
    company_url = configuration_settings["Api Root"]
    company_name = configuration_settings["Company Name"]
    public_key = configuration_settings["Public Key"]
    private_key = configuration_settings["Private Key"]
    client_id = configuration_settings["Client Id"]
    connectwise_manager = ConnectWiseManager(
        company_url, company_name, public_key, private_key, client_id
    )

    # Parameters.
    company = siemplify.parameters["Company"]
    owner_name = siemplify.parameters.get("Owner Name")
    board = siemplify.parameters["Board"]
    status = siemplify.parameters["Status"]
    priority_id = siemplify.parameters["Priority"]
    initial_description = siemplify.parameters["Initial Description"]

    # Fetch scope data.
    target_alerts: list[Any] = []
    execution_scope: ExecutionScope = getattr(siemplify, "execution_scope", ExecutionScope.Alert)

    if execution_scope.value == ExecutionScope.Alert.value:
        target_alerts = [siemplify.current_alert]
    else:
        target_alerts = getattr(
            siemplify.case,
            "open_alerts",
            siemplify.case.alerts,
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    created_tickets: SingleJson = {}
    errors: list[str] = []

    for alert in target_alerts:
        summary: str = alert.external_id
        if not summary:
            siemplify.LOGGER.info(
                f"Alert {alert.identifier} has no external ID for summary. "
                "Using identifier."
            )
            summary = alert.identifier

        try:
            ticket_id: str = connectwise_manager.create_ticket(
                summary, company, board, status, priority_id, owner_name
            )

            if ticket_id:
                # Add initial description to ticket (as first comment)
                connectwise_manager.add_comment_to_ticket(
                    ticket_id,
                    initial_description,
                )
                created_tickets[alert.identifier] = ticket_id
        except Exception as e:
            error_msg: str = (
                f"Failed to create CW ticket for alert {alert.identifier}: {str(e)}"
            )
            siemplify.LOGGER.error(error_msg)
            errors.append(error_msg)

    result_value = False
    if created_tickets:
        # Attach CW ticket ids to alerts in batch.
        siemplify.update_alerts_additional_data(created_tickets)
        output_message: str = (
            f"Created {len(created_tickets)} tickets: {list(created_tickets.values())}"
        )
        if execution_scope.value == ExecutionScope.Alert.value:
            result_value = str(list(created_tickets.values())[0])
        else:
            result_value = ",".join([str(id) for id in created_tickets.values()])
    else:
        output_message: str = "There was a problem creating ticket(s)."

    if errors:
        newline: str = "\n"
        output_message += f"\nErrors:\n{newline.join(errors)}"

    siemplify.LOGGER.info(output_message)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nresult_value: {result_value}" f"\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
