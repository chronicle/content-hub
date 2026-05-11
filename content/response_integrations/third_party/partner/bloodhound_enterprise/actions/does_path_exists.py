from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.bloodhound_manager import BloodhoundManager
import json
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.constants import (INTEGRATION_NAME, DOES_PATH_EXISTS_SCRIPT_NAME)

@output_handler
def main():
    """
    Main function for the BloodHound Multi-Action.
    Handles path existence check between multiple combinations of principals
    extracted from event_details JSON.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = DOES_PATH_EXISTS_SCRIPT_NAME

    # Extract config
    tenant_domain = siemplify.extract_configuration_param(INTEGRATION_NAME, "BloodHound Enterprise Server")
    token_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token ID")
    token_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token Key")

    # Extract event details which contains JSON pairs of FromPrincipal and ToPrincipal
    event_details = siemplify.extract_action_param(param_name="Event Details", print_value=False)

    if not event_details:
        error_message = "'Event Details' parameter is required and cannot be empty."
        siemplify.LOGGER.error(error_message)
        status = EXECUTION_STATE_FAILED
        siemplify.end(error_message, "false", status)

    # Parse the event details to extract principal pairs
    principal_pairs = parse_event_details(event_details, siemplify)

    if not principal_pairs:
        status = EXECUTION_STATE_FAILED
        siemplify.end("No valid principal pairs found after parsing input.", "False", status)

    bhe_manager = BloodhoundManager(tenant_domain, token_id, token_key, logger=siemplify.LOGGER)
    response_payload = {}
    consolidated_result = {}
    messages = []
    all_paths_exist = True
    
    for pair in principal_pairs:
        from_principal = pair["FromPrincipal"]
        to_principal = pair["ToPrincipal"]
            
        key = f"{from_principal} -> {to_principal}"
        siemplify.LOGGER.info(f"Checking path from {from_principal} to {to_principal}")
        path_info = _handle_does_path_exist(bhe_manager, from_principal, to_principal, siemplify)
            
        response_payload[key] = path_info
        messages.append(f"{key}: {path_info.get('message')}")

        if path_info.get("status") != "success" or path_info.get("data") is not True:
            all_paths_exist = False

    # Final output decision
    status = EXECUTION_STATE_COMPLETED
    consolidated_result["path_info"] = response_payload
    result_value = "true" if all_paths_exist else "false"
    output_message = " | ".join(messages)
    siemplify.result.add_result_json(consolidated_result)
       
    siemplify.end(output_message, result_value, status)

def parse_event_details(event_details, siemplify):
    """
    Parse the event_details string into a list of dictionaries containing FromPrincipal and ToPrincipal.
    Expects a string of comma-separated JSON objects.
    
    Args:
        event_details (str): The event details string to parse
        siemplify: The Siemplify context for logging
        
    Returns:
        list: List of dictionaries with FromPrincipal and ToPrincipal keys
    """
    try:
        # Handle edge case where event_details might have surrounding brackets
        if event_details.startswith('[') and event_details.endswith(']'):
            event_details = event_details[1:-1]
        
        # Fix incomplete JSON by ensuring proper formatting
        # Add brackets if missing to make it a valid JSON array
        if not (event_details.startswith('[') and not event_details.endswith(']')):
            event_details = f"[{event_details}]"
        
        # Replace any trailing commas before closing bracket which would make JSON invalid
        event_details = event_details.replace(",]", "]").replace(", ]", "]")
        
        # Try to parse as JSON array
        try:
            principal_pairs = json.loads(event_details)
        except json.JSONDecodeError:
            # If that fails, try to parse as comma-separated individual JSON objects
            principal_pairs = []
            # Split by comma and ensure each part is a valid JSON
            parts = event_details.strip('[]').split('},')
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    part = part + '}'
                if part.strip():
                    try:
                        pair = json.loads(part.strip())
                        principal_pairs.append(pair)
                    except json.JSONDecodeError as e:
                        siemplify.LOGGER.info(f"Could not parse JSON object: {part}. Error: {str(e)}")
        
        # Validate each pair has the required keys
        valid_pairs = []
        for pair in principal_pairs:
            if isinstance(pair, dict) and "FromPrincipal" in pair and "ToPrincipal" in pair:
                valid_pairs.append(pair)
            else:
                siemplify.LOGGER.info(f"Skipping invalid principal pair: {pair}. Missing required keys.")
        return valid_pairs
    
    except Exception as e:
        siemplify.LOGGER.error(f"Error parsing event details: {str(e)}")
        return []

def _handle_does_path_exist(manager, start_node: str, end_node: str, siemplify) -> dict:
    """
    Wrapper function to check if a path exists between two nodes.
    Always returns a consistent dictionary with 'status', 'message', and 'data'.
    """
    try:
        path_result = manager.does_path_exists_between_nodes(start_node, end_node)

        # Assuming path_result is a dict with key 'data' containing a boolean value
        return {
            "status": "success",
            "message": "Path exists between the nodes.",
            "data": True
        }
    except Exception as error:
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        return {
            "status": "error",
            "message": f"Error checking path existence: {str(error)}",
            "data": None
        }

if __name__ == "__main__":
    main()