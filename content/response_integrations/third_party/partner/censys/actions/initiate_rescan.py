from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException, InvalidIntegerException
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INITIATE_RESCAN_SCRIPT_NAME,
    IOC_TYPE_SERVICE_ID,
    MAX_INT_VALUE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    TRANSPORT_PROTOCOL_UNKNOWN,
)
from ..core.utils import get_integration_params, validate_integer_param, validate_ip_address


def validate_rescan_params(
    ioc_type: str,
    ioc_value: str,
    protocol: str,
    transport_protocol: str,
) -> None:
    """Validate required parameters for rescan based on IOC type.

    Args:
        ioc_type: Type of IOC (Host or Web Properties)
        ioc_value: IP address or domain name
        protocol: Service protocol
        transport_protocol: Transport protocol

    Raises:
        ValueError: If required parameters are missing for Service
    """
    if ioc_type == IOC_TYPE_SERVICE_ID:
        # Validate IP address for Host
        validate_ip_address(ioc_value, "IOC Value")

        if not protocol or not protocol.strip():
            raise ValueError("Protocol is required when IOC Type is Service.")


@output_handler
def main():
    """Initiate a live rescan for a known host service.

    This action initiates a rescan for a host service at a specific IP:port or hostname:port.
    The scan may take several minutes to complete and returns a scan ID that can be used
    to monitor the scan's status.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the rescan results
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        Exception: If rescan initiation fails for any reason
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = INITIATE_RESCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    ioc_type = siemplify.extract_action_param(
        param_name="IOC Type", input_type=str, is_mandatory=True
    )
    ioc_value = siemplify.extract_action_param(
        param_name="IOC Value", input_type=str, is_mandatory=True
    )
    port_param = siemplify.extract_action_param(
        param_name="Port", input_type=str, is_mandatory=True, default_value="443"
    )
    protocol = siemplify.extract_action_param(
        param_name="Protocol", input_type=str, is_mandatory=False
    )
    transport_protocol = siemplify.extract_action_param(
        param_name="Transport Protocol",
        input_type=str,
        is_mandatory=False,
        default_value=TRANSPORT_PROTOCOL_UNKNOWN,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # Validate port parameter
        port = validate_integer_param(
            port_param,
            "Port",
            default_value="443",
            zero_allowed=False,
            allow_negative=False,
            min_value=1,
            max_value=MAX_INT_VALUE,
        )

        # Validate required parameters for Host (includes IP validation)
        validate_rescan_params(ioc_type, ioc_value, protocol, transport_protocol)

        # Initialize API Manager
        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Initiating rescan for {ioc_type}: {ioc_value}:{port}")

        # Call Censys API
        response = censys_manager.initiate_rescan(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            port=port,
            protocol=protocol,
            transport_protocol=transport_protocol,
        )

        # Extract scan information
        result = response.get("result", {})
        tracked_scan_id = result.get("tracked_scan_id")
        tasks = result.get("tasks", [])
        create_time = result.get("create_time")

        # Add JSON result
        siemplify.result.add_result_json(response)

        # Build output message
        if tracked_scan_id:
            output_message = f"Successfully initiated rescan. Scan ID: {tracked_scan_id}"
            if create_time:
                output_message += f", Created: {create_time}"
            if tasks:
                task_count = len(tasks)
                output_message += f", Tasks: {task_count}"

            siemplify.LOGGER.info(output_message)
        else:
            output_message = "Rescan initiated but no scan ID returned."
            siemplify.LOGGER.info(output_message)

    except (InvalidIntegerException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(INITIATE_RESCAN_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
