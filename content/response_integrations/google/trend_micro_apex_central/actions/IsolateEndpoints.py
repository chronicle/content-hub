from __future__ import annotations
import copy
import json
import sys

import requests
from TIPCommon import extract_configuration_param

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.TrendMicroApexCentralManager import TrendMicroApexCentralManager
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
    ISOLATE_ENDPOINTS_SCRIPT_NAME,
    ISOLATION_STATUS_ISOLATED,
    ISOLATION_STATUS_PENDING,
    ISOLATION_STATUS_NOT_SUPPORTED,
)
from ..core.exceptions import TrendMicroApexCentralAuthorizationError
from ..core.utils import is_approaching_timeout

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.MACADDRESS, EntityTypes.HOSTNAME]


def start_operation(siemplify, manager):
    """
    Main part of the action that requests endpoints isolation
    :param siemplify: SiemplifyAction object.
    :param manager: {TrendMicroApexCentralManager} TrendMicroApexCentralManager manager object.
    :return: {output message, json result, execution_state} Output message, results value and execution state of the operation
    """
    supported_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]
    output_message = ""
    endpoints_initial_info = {
        "pending_endpoints": {"ip": [], "mac": [], "hostname": []},
        "isolated_endpoints": [],
        "failed_endpoints": [],
    }

    for entity in supported_entities:
        entity.identifier = entity.identifier.strip()
        try:
            siemplify.LOGGER.info(f"Isolating endpoint {entity.identifier}")
            if entity.entity_type == EntityTypes.ADDRESS:
                manager.isolate_endpoint(ip_address=entity.identifier)
                endpoints_initial_info["pending_endpoints"]["ip"].append(
                    entity.identifier
                )
            if entity.entity_type == EntityTypes.HOSTNAME:
                manager.isolate_endpoint(host_name=entity.identifier)
                endpoints_initial_info["pending_endpoints"]["hostname"].append(
                    entity.identifier
                )
            if entity.entity_type == EntityTypes.MACADDRESS:
                manager.isolate_endpoint(mac_address=entity.identifier)
                endpoints_initial_info["pending_endpoints"]["mac"].append(
                    entity.identifier
                )

        except (
            requests.exceptions.ConnectionError,
            TrendMicroApexCentralAuthorizationError,
        ):
            raise
        except Exception as error:
            endpoints_initial_info["failed_endpoints"].append(entity.identifier)
            siemplify.LOGGER.error(f"Failed to isolate endpoint")
            siemplify.LOGGER.exception(error)

    all_pending_endpoints = []
    for _endpoint_type, endpoints in endpoints_initial_info[
        "pending_endpoints"
    ].items():
        all_pending_endpoints.extend(endpoints)

    if all_pending_endpoints:
        status = EXECUTION_STATE_INPROGRESS
        output_message = f"Initiated endpoint isolation on the following endpoints: {',  '.join(all_pending_endpoints)}. Waiting for the isolation to finish."
        result_value = json.dumps(endpoints_initial_info)
    else:
        if endpoints_initial_info["failed_endpoints"]:
            output_message += f"Action wasn't able to isolate the following endpoints in {INTEGRATION_DISPLAY_NAME}:\n  {',  '.join(endpoints_initial_info['failed_endpoints'])}\n\n"
        output_message += f"No endpoints were isolated in {INTEGRATION_DISPLAY_NAME}."
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(siemplify, manager):
    """
    Part of the action that periodically fetches endpoint isolation status
    :param siemplify: SiemplifyAction object.
    :param manager: {TrendMicroApexCentralManager} TrendMicroApexCentralManager manager object.
    :return: {output message, json result, execution_state} Output message, results value and execution state of the operation
    """
    endpoints_isolation_info = copy.deepcopy(
        json.loads(siemplify.extract_action_param("additional_data"))
    )

    pending_endpoints = endpoints_isolation_info.get("pending_endpoints", {})
    failed_endpoints = endpoints_isolation_info.get("failed_endpoints", [])
    isolated_endpoints = endpoints_isolation_info.get("isolated_endpoints", [])
    new_pending_isolations = {"ip": [], "mac": [], "hostname": []}
    output_message = ""

    try:
        if pending_endpoints:
            for endpoint_type, endpoints in pending_endpoints.items():
                for endpoint in endpoints:
                    try:
                        endpoint_details = None
                        if endpoint_type == "ip":
                            endpoint_details = manager.get_security_agent(
                                ip_address=endpoint
                            )
                        if endpoint_type == "hostname":
                            endpoint_details = manager.get_security_agent(
                                host_name=endpoint
                            )
                        if endpoint_type == "mac":
                            endpoint_details = manager.get_security_agent(
                                mac_address=endpoint
                            )

                        if not endpoint_details:
                            siemplify.LOGGER.info(
                                f"Failed to find details for endpoint {endpoint}"
                            )
                            failed_endpoints.append(endpoint)
                            continue

                        if (
                            endpoint_details.isolation_status
                            == ISOLATION_STATUS_PENDING
                        ):
                            new_pending_isolations[endpoint_type].append(endpoint)

                        elif (
                            endpoint_details.isolation_status
                            == ISOLATION_STATUS_ISOLATED
                        ):
                            isolated_endpoints.append(endpoint)

                        elif (
                            endpoint_details.isolation_status
                            == ISOLATION_STATUS_NOT_SUPPORTED
                        ):
                            siemplify.LOGGER.info(
                                f"Endpoint {endpoint} does not support isolation"
                            )
                            failed_endpoints.append(endpoint)

                        else:
                            siemplify.LOGGER.info(
                                f"Endpoint {endpoint} has isolation status {endpoint_details.isolation_status}. "
                                f"Considering as failed"
                            )
                            failed_endpoints.append(endpoint)

                    except Exception as error:
                        failed_endpoints.append(endpoint)
                        siemplify.LOGGER.error(
                            f"Failed to check isolation status for endpoint {endpoint}"
                        )
                        siemplify.LOGGER.exception(error)

        all_pending_endpoints = []
        for _endpoint_type, endpoints in new_pending_isolations.items():
            all_pending_endpoints.extend(endpoints)

        if all_pending_endpoints:
            output_message = f"Initiated endpoint isolation on the following endpoints: {',  '.join(all_pending_endpoints)}. Waiting for the isolation to finish."

            result_value = json.dumps(
                {
                    "pending_endpoints": new_pending_isolations,
                    "isolated_endpoints": isolated_endpoints,
                    "failed_endpoints": failed_endpoints,
                }
            )
            status = EXECUTION_STATE_INPROGRESS

        elif isolated_endpoints:
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            output_message += "Successfully isolated the following endpoints in {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n  ".join(isolated_endpoints)
            )
            if failed_endpoints:
                output_message += "Action wasn't able to isolate the following endpoints in {}:\n   {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(failed_endpoints)
                )
        else:
            output_message += (
                f"No endpoints were isolated in {INTEGRATION_DISPLAY_NAME}."
            )
            result_value = False
            status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = (
            f"Error executing action {ISOLATE_ENDPOINTS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {ISOLATE_ENDPOINTS_SCRIPT_NAME}"
    )
    action_start_time = unix_now()
    mode = "Main" if is_first_run else "Check isolation status"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    application_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Application ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    result_value = False
    output_message = ""

    try:
        manager = TrendMicroApexCentralManager(
            api_root=api_root,
            application_id=application_id,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        if is_first_run:
            output_message, result_value, status = start_operation(siemplify, manager)
        elif is_approaching_timeout(
            action_start_time, siemplify.execution_deadline_unix_time_ms
        ):
            endpoints_isolation_info = json.loads(
                siemplify.extract_action_param("additional_data")
            )
            pending_endpoints = endpoints_isolation_info.get("pending_endpoints", {})
            failed_endpoints = endpoints_isolation_info.get("failed_endpoints", [])
            isolated_endpoints = endpoints_isolation_info.get("isolated_endpoints", [])
            if isolated_endpoints:
                output_message += "Successfully isolated the following endpoints in {}:\n  {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(isolated_endpoints)
                )
            if failed_endpoints:
                output_message += "Action wasn't able to isolate the following endpoints in {}:\n  {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(failed_endpoints)
                )
            all_pending_endpoints = []
            for _endpoint_type, endpoints in pending_endpoints.items():
                all_pending_endpoints.extend(endpoints)
            output_message += (
                "Action initiated isolation, but it's still pending for the following endpoints: {}\nPlease consider "
                "increasing the timeout in the IDE".format(
                    "\n  ".join(all_pending_endpoints)
                )
            )
            status = EXECUTION_STATE_TIMEDOUT
            result_value = True
        else:
            output_message, result_value, status = query_operation_status(
                siemplify, manager
            )

    except Exception as error:
        output_message = f'Error executing action "{ISOLATE_ENDPOINTS_SCRIPT_NAME}". Reason: {error}.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
