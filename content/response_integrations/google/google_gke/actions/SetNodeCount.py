from __future__ import annotations
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from google_gke.core.GKEAuth import build_auth_manager
from google_gke.core.GKEConsts import INTEGRATION_IDENTIFIER, SET_NODE_POOL_COUNT_SCRIPT_NAME
from google_gke.core.GKEExceptions import (
    GoogleGKEManagerError,
    GoogleGKEInvalidZoneError,
    GoogleGKEInvalidClusterNameError,
    GoogleGKEInvalidNodePoolNameError,
    MissingParametersException,
    NonPositiveValueException,
)
from google_gke.core.GKEManagers import GKEApiManager
from google_gke.core.GKEServices import GKEClusterNodesService, GKEOperationService
from google_gke.core.GKEUtils import is_action_approaching_timeout


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {SET_NODE_POOL_COUNT_SCRIPT_NAME}"
    )
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Action parameters
    target_project_id = extract_action_param(
        siemplify, param_name="Project ID", print_value=True
    )
    cluster_location = extract_action_param(
        siemplify, param_name="Cluster Location", is_mandatory=True, print_value=True
    )
    cluster_name = extract_action_param(
        siemplify, param_name="Cluster Name", is_mandatory=True, print_value=True
    )
    node_pool_name = extract_action_param(
        siemplify, param_name="Node Pool Name", is_mandatory=True, print_value=True
    )
    wait_for_operation_to_finish = extract_action_param(
        siemplify,
        param_name="Wait for cluster configuration change operation to finish",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    # Action results
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    operation = None

    try:
        node_count = extract_action_param(
            siemplify,
            param_name="Node Count",
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )
        if node_count < 0:
            raise NonPositiveValueException(
                f'Invalid value was provided for "Node Count": {node_count}. Value should be a positive number.'
            )

        auth_manager = build_auth_manager(siemplify)
        api_manager = GKEApiManager(
            api_root=auth_manager.api_root,
            session=auth_manager.prepare_session(),
            project_id=target_project_id or auth_manager.project_id,
        )

        node_manager = GKEClusterNodesService(
            api_manager=api_manager,
            logger=siemplify.LOGGER,
            zone_name=cluster_location,
            cluster_name=cluster_name,
        )
        operation_manager = GKEOperationService(
            api_manager=api_manager, logger=siemplify.LOGGER, zone_name=cluster_location
        )

        if is_first_run:
            try:
                operation = node_manager.set_pool_size(
                    node_pool_name=node_pool_name, node_count=node_count
                )

                if wait_for_operation_to_finish:
                    output_message, result_value, status = (
                        operation_manager.check_status(
                            operation,
                            is_action_approaching_timeout(
                                siemplify.execution_deadline_unix_time_ms
                            ),
                        )
                    )
                else:
                    output_message = "Successfully created cluster node pool configuration change operation."
                    result_value = True
            except (
                GoogleGKEInvalidZoneError,
                GoogleGKEInvalidClusterNameError,
                GoogleGKEInvalidNodePoolNameError,
            ):
                raise
            except GoogleGKEManagerError as error:
                output_message = f"Failed to execute the action because API returned error, please see action logs: {error}"
                siemplify.LOGGER.error(f"Failed to set node autoscaling config")
                siemplify.LOGGER.exception(error)
        else:
            operation_name = json.loads(siemplify.parameters["additional_data"])
            operation = operation_manager.get(operation_name, cluster_name)
            output_message, result_value, status = operation_manager.check_status(
                operation,
                is_action_approaching_timeout(
                    siemplify.execution_deadline_unix_time_ms
                ),
            )

        # append json results only if action's execution is finished
        if operation and status != EXECUTION_STATE_INPROGRESS:
            siemplify.result.add_result_json(operation.to_json())

    except (
        GoogleGKEInvalidNodePoolNameError,
        GoogleGKEInvalidClusterNameError,
        MissingParametersException,
    ) as error:
        output_message = f"{error}"
        status = EXECUTION_STATE_FAILED

    except GoogleGKEInvalidZoneError:
        output_message = (
            f'Provided cluster location "{cluster_location}" does not exist.'
        )
        status = EXECUTION_STATE_FAILED

    except Exception as error:
        output_message = f'Error execution action "{SET_NODE_POOL_COUNT_SCRIPT_NAME}". Reason: {error}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
