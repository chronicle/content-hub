from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.HibobManager import HibobManager

INTEGRATION_NAME = "Hibob"


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Extracting the integration params.
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    # The api_root is the url of the integration :https://api.hibob.com/
    api_root = "https://api.hibob.com"
    # The api_token generated from hibob site
    api_token = conf.get("API Token")

    # Creating an instance of hibobmanager object
    hibob_manager = HibobManager(api_root, api_token)

    # Extracting the action params= The employee's email
    user_email = siemplify.extract_action_param("Employee's Email")

    # Extracting the employee id(the employee id is a serial number that is generated automatically when creating the user)
    employee_details = hibob_manager.get_user_details(user_email)

    json_result = {}

    # If the user doesnt contains data
    if not employee_details:
        return_value = False
        json_result["exists"] = "False"
        json_result["revokwWasDone"] = "False"
        output_message = (
            f"{user_email} wasn't revoked as the employee doesn't exists in Hibob"
        )

    # If the user was revoked already
    if employee_details:
        # Extracting the employee invite status
        employee_invite_status = employee_details.get("state")

        # Extracting the employee id
        employee_identifier = employee_details.get("id")

        if employee_invite_status == "uninvited":
            return_value = False
            json_result["exists"] = "True"
            json_result["revokwWasDone"] = "False"
            output_message = (
                f"{user_email} wasn't revoked as the employee was already revoked"
            )

        else:
            # Calling the revoke_user_response function from the HibobManager
            revoke_user_response = hibob_manager.revoke_access_to_hibob(
                employee_identifier,
            )
            return_value = True
            json_result["exists"] = "True"
            json_result["revokwWasDone"] = "True"
            output_message = f"The employee {user_email} was revoked successfully"

    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
