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
    """Enrich an IP address with Ransomware Resilience Service data.

    Extracts the target IP address from the action parameters, queries the RRS
    API for enrichment data, and attaches the results to the SOAR action output.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Enrich IP: Init -----------------")

    enrich_results = None
    ip_address = None
    try:
        rrsManager = ApiManager(siemplify)
        ip_address = siemplify.extract_action_param("IP Address", print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Enrich IP: Started -----------------")

        # call enrich api
        enrich_results = rrsManager.enrich_ip(ip_address)

        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = f"Successfully enriched IP - {ip_address}"
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = str(e)
        siemplify.LOGGER.error(
            f"Enrich IP: RrsException: Failed to enrich IP - {ip_address}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        enrich_results = []

    except Exception as e:
        output_message = f"Failed to enrich IP - {ip_address}. Error: {e}"
        siemplify.LOGGER.error(f"Enrich IP: Failed to enrich IP - {ip_address}. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        enrich_results = []

    siemplify.LOGGER.info("----------------- RRS - Enrich IP: End -----------------")
    siemplify.LOGGER.info(
        f"Enrich IP output: \n  status: {status}\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(enrich_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
