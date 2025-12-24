from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AsanaManager import AsanaManager

IDENTIFIER = "Asana"


@output_handler
def main():
    siemplify = SiemplifyAction()

    personal_access_token = siemplify.extract_configuration_param(IDENTIFIER, "Token")
    base_url = siemplify.extract_configuration_param(IDENTIFIER, "Base URL")

    workspace_name = siemplify.extract_action_param("Workspace Name")
    user_to_add = siemplify.extract_action_param("User's Email")

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    workspace_id = asana_manager.get_workspace_id_by_name(workspace_name)

    added_user_details = asana_manager.add_user_to_workspace(workspace_id, user_to_add)

    if added_user_details["data"] is not None:
        output_message = f"The user {user_to_add} was added to the workspace: {workspace_name} successfully"
        return_value = True

    else:
        output_message = (
            f"The user {user_to_add} wasn't added to the workspace: {workspace_name} "
        )
        return_value = False

    # Adding json result to the action
    siemplify.result.add_result_json(added_user_details)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()
