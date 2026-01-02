from __future__ import annotations

import time

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    allowed_values = ["Informative", "Low", "Medium", "High", "Critical"]

    current_alert_identifier = siemplify.current_alert.identifier
    if not current_alert_identifier:
        siemplify.end("No current alert identifier available.", "false")
        return

    priority = siemplify.extract_action_param(
        "Priority",
        print_value=True,
        is_mandatory=True,
    )
    if priority not in allowed_values:
        message = f"The specied priority name is not allowed. Please specify one of the following values: {allowed_values}"
        siemplify.end(message, "false")
        return

    current_version = siemplify.get_system_info(int(time.time())).get("version_number")
    if current_version < "5.6":
        message = "Changing alert priority is not available for Siemplify versions lower than 5.6"
        siemplify.end(message, "false")
        return

    address = f"{siemplify.API_ROOT}/external/v1/sdk/UpdateAlertPriority"
    request_dict = {
        "caseId": siemplify.case_id,
        "alertIdentifier": current_alert_identifier,
        "alertName": siemplify.current_alert.name,
        "priority": priority,
    }
    response = siemplify.session.post(address, json=request_dict)
    siemplify.validate_siemplify_error(response)
    siemplify.end(
        f"The alert priority was set to {priority}. siemplify response: {response}",
        "true",
    )
    return


if __name__ == "__main__":
    main()
