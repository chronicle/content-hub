from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.bloodhound_manager import BloodhoundManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.constants import ( INTEGRATION_NAME, GET_OBJECT_ID_SCRIPT_NAME)

@output_handler
def main():
    """
    Main function to fetch object IDs from BloodHound Enterprise based on provided object names.

    This script:
    - Extracts configuration parameters from the Siemplify platform.
    - Parses the input 'name' parameter, which should be a comma-separated list of entity names.
    - Initializes the BloodHoundManager with the required credentials.
    - Iterates through each name and fetches the corresponding object ID using the helper function.
    - Logs and stores the results, and sends a consolidated JSON response.
    
    Ends with:
    - EXECUTION_STATE_COMPLETED if successful.
    - EXECUTION_STATE_FAILED if any required parameter is missing or an error occurs during execution.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_OBJECT_ID_SCRIPT_NAME

    # Extract config
    tenant_domain = siemplify.extract_configuration_param(INTEGRATION_NAME, "BloodHound Enterprise Server")
    token_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token ID")
    token_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token Key")

    # Extract and split the comma-separated names
    names_param = siemplify.extract_action_param(param_name="Object Names", print_value=False)

    if not names_param:
        error_message = "The 'Object Names' parameter is required and cannot be empty."
        siemplify.LOGGER.error(error_message)
        status = EXECUTION_STATE_FAILED
        siemplify.end(error_message, "false", status)

    names = list(set([n.strip() for n in names_param.split(",") if n.strip()]))

    if not names:
        status = EXECUTION_STATE_FAILED
        siemplify.end("No valid names provided after parsing input.", "false", status)

    bhe_manager = BloodhoundManager(tenant_domain, token_id, token_key, logger=siemplify.LOGGER)
    response_payload = {}
    messages = []
    consolidated_result = {}

    for name in names:
        siemplify.LOGGER.info(f"Processing name: {name}")
        encoded_name = name.strip().replace(" ", "%20").replace("@", "%40")
        object_id_info = _handle_get_object_id(bhe_manager, encoded_name, siemplify)
        response_payload[name] = object_id_info
        messages.append(f"{name}: {object_id_info.get('message')}")

    # Final Output
    consolidated_result["objects_info"] = response_payload
    result_value = "true" 
    output_message = " | ".join(messages)
    siemplify.result.add_result_json(consolidated_result)

    siemplify.LOGGER.info(f"result is : {response_payload}")
    status = EXECUTION_STATE_COMPLETED
    siemplify.end(output_message, result_value, status)

# Get Object ID by Name
def _handle_get_object_id(manager, name: str, siemplify) -> dict:
    """
    Helper function to fetch object ID for a given name from BloodHound Enterprise.

    Args:
        manager (BloodhoundManager): The initialized manager instance used to make API calls.
        name (str): The entity name for which to retrieve the object ID.
        siemplify (SiemplifyAction): The Siemplify action instance for logging and reporting.

    Returns:
        dict: A dictionary containing status, message, and data (object ID or error info).
    """
    try:
        response = manager.get_object_id_by_name(name)

        return {
            "status": "success",
            "message": "Object ID found.",
            "data": response.get("data")
        }
            

    except Exception as error:
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        return {
            "status": "error",
            "message": str(error),
            "data": None
        }

if __name__ == "__main__":
    main()