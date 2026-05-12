from __future__ import annotations
import asyncio
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, EXECUTION_STATE_INPROGRESS
from ..core.constants import INTEGRATION_NAME, FETCH_ASSET_INFO_SCRIPT_NAME
from ..core.bloodhound_manager import BloodhoundManager
import json

@output_handler
def main():
    """
    Main function for fetching asset information from BloodHound Enterprise based on object IDs.
    
    This function handles both initial and iterative executions in Siemplify by using the `additional_data` field
    to maintain execution state (like remaining IDs, partial results, and messages). It processes one object ID
    per run to avoid timeouts and supports INPROGRESS state handling.

    Steps:
    - Extracts configuration and parameters from Siemplify.
    - Parses additional data to resume partial executions.
    - Initializes BloodHoundManager to communicate with the BloodHound Enterprise API.
    - Fetches asset information for the current object ID.
    - Saves the result and updates state if more IDs are remaining.
    - Ends the action with either COMPLETED, INPROGRESS, or FAILED state.

    Raises:
        Ends execution with Siemplify status and logs errors if encountered.
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = FETCH_ASSET_INFO_SCRIPT_NAME

    try:
        # Extract configuration parameters
        tenant_domain = siemplify.extract_configuration_param(INTEGRATION_NAME, "BloodHound Enterprise Server")
        token_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token ID")
        token_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "Token Key")

        consolidated_result = {}

        # Parse additional_data for state information
        additional_data_raw = siemplify.parameters.get("additional_data", "{}")
        additional_data = {}
        
        try:
            if additional_data_raw and additional_data_raw not in (True, False):
                additional_data = json.loads(additional_data_raw)
        except json.JSONDecodeError:
            siemplify.LOGGER.warning(f"Could not parse additional_data: {additional_data_raw}. Starting fresh.")
            additional_data = {}
        
        # Extract ongoing state or initialize new state
        remaining_ids = additional_data.get("remaining_ids", [])
        results = additional_data.get("results", {})
        messages = additional_data.get("messages", [])
        
        # If no remaining IDs (first run), get from parameters
        if not remaining_ids:
            object_id_param = siemplify.extract_action_param(param_name="Object IDs", print_value=False)
            if not object_id_param:
                siemplify.LOGGER.error("'Object IDs' parameter is required.")
                siemplify.end("'Object IDs' parameter is required.", "false", EXECUTION_STATE_FAILED)
                return

            # Parse and deduplicate object IDs
            remaining_ids = list({oid.strip() for oid in object_id_param.split(",") if oid.strip()})
            
        # Validate IDs
        if not remaining_ids:
            siemplify.end("No valid 'Object IDs' to process.", "false", EXECUTION_STATE_COMPLETED)
            return
        
        # Process one ID per execution (to avoid timeouts)
        current_id = remaining_ids.pop(0)
        siemplify.LOGGER.info(f"Processing Object ID: {current_id}")
        
        # Initialize BloodHound Manager
        bhe_manager = BloodhoundManager(tenant_domain, token_id, token_key, logger=siemplify.LOGGER)
        
        # Fetch asset information
        try:
            asset_info = bhe_manager._handle_fetch_asset_information(current_id)
            siemplify.LOGGER.info(f"Successfully processed {current_id}")
        except Exception as e:
            siemplify.LOGGER.error(f"Error processing {current_id}: {e}")
            asset_info = {
                "status": "error", 
                "message": str(e), 
                "data": None
            }
        
        # Record results
        results[current_id] = asset_info
        messages.append(f"{current_id}: {asset_info.get('message', '')}")
        
        # If more IDs to process, prepare for next iteration
        if remaining_ids:
            next_state = {
                "remaining_ids": remaining_ids,
                "results": results,
                "messages": messages
            }
            
            # Add current results to the output
            consolidated_result["assets_info"] = results
            siemplify.result.add_result_json(consolidated_result)
            
            # Return INPROGRESS state with next_state as additional_data
            siemplify.end(
                f"Processing in progress... ({len(remaining_ids)} IDs remaining)", 
                json.dumps(next_state), 
                EXECUTION_STATE_INPROGRESS
            )
            return
        
        # All IDs processed
        output_message = " | ".join(messages)
        consolidated_result["assets_info"] = results
        siemplify.result.add_result_json(consolidated_result)
        siemplify.end(output_message, "true", EXECUTION_STATE_COMPLETED)

    except Exception as e:
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error is {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        siemplify.end(f"Unexpected error: {str(e)}", "false", EXECUTION_STATE_FAILED)

if __name__ == "__main__":
    main()