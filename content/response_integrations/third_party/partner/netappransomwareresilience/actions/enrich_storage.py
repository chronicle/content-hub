from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Enrich storage information using the Ransomware Resilience Service.

    Queries the RRS API for storage enrichment data and attaches the results
    to the SOAR action output.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Enrich Storage: Init -----------------")

    enrich_results = None
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        agent_id = siemplify.extract_action_param("Agent ID", print_value=True)
        system_id = siemplify.extract_action_param("System ID", print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Enrich Storage: Started -----------------")

        # call enrich storage api
        enrich_results = rrsManager.enrich_storage(agent_id, system_id)
        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = "Successfully enriched storage information"
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = str(e)
        siemplify.LOGGER.error(f"Enrich Storage: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        enrich_results = []

    except Exception as e:
        siemplify.LOGGER.error(f"Enrich Storage: Failed to enrich storage. Error: {e}")
        output_message = f"Failed to enrich storage. Error: {e}"
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        enrich_results = []

    siemplify.LOGGER.info("----------------- RRS - Enrich Storage: End -----------------")
    siemplify.LOGGER.info(
        f"Enrich Storage output: \n  status: {status}\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(enrich_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
