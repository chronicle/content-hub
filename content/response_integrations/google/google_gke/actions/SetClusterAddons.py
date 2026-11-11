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
from google_gke.core.GKEConsts import (
    ENABLED,
    DISABLED,
    INTEGRATION_IDENTIFIER,
    NOT_CHANGED,
    MAP_CLOUD_RUN_CONFIG_PARAMS,
    SET_CLUSTER_ADDONS_SCRIPT_NAME,
)
from google_gke.core.GKEExceptions import (
    GoogleGKEManagerError,
    GoogleGKEInvalidZoneError,
    GoogleGKEInvalidClusterNameError,
    MissingParametersException,
)
from google_gke.core.GKEManagers import GKEApiManager
from google_gke.core.GKEServices import GKEClustersService, GKEOperationService
from google_gke.core.GKEUtils import is_action_approaching_timeout


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {SET_CLUSTER_ADDONS_SCRIPT_NAME}"
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
    http_load_balancing = extract_action_param(
        siemplify,
        param_name="HTTP Load Balancing",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    horizontal_pod_autoscaling = extract_action_param(
        siemplify,
        param_name="Horizontal Pod Autoscaling",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    network_policy_config = extract_action_param(
        siemplify,
        param_name="Network Policy Config",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    cloud_run_config = extract_action_param(
        siemplify,
        param_name="Cloud Run Config",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    dns_cache_record = extract_action_param(
        siemplify,
        param_name="DNS Cache Config",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    config_connector_config = extract_action_param(
        siemplify,
        param_name="Config Connector Config",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
    )
    gce_persistent_disk_csi_driver_config = extract_action_param(
        siemplify,
        param_name="GCE Persistent Disk Csi Driver Config",
        is_mandatory=False,
        default_value=NOT_CHANGED,
        print_value=True,
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
        auth_manager = build_auth_manager(siemplify)
        api_manager = GKEApiManager(
            api_root=auth_manager.api_root,
            session=auth_manager.prepare_session(),
            project_id=target_project_id or auth_manager.project_id,
        )

        cluster_manager = GKEClustersService(
            api_manager=api_manager, logger=siemplify.LOGGER, zone_name=cluster_location
        )
        operation_manager = GKEOperationService(
            api_manager=api_manager, logger=siemplify.LOGGER, zone_name=cluster_location
        )

        if is_first_run:
            try:
                if not any(
                    conf != NOT_CHANGED
                    for conf in [
                        http_load_balancing,
                        horizontal_pod_autoscaling,
                        network_policy_config,
                        cloud_run_config,
                        dns_cache_record,
                        config_connector_config,
                        gce_persistent_disk_csi_driver_config,
                    ]
                ):
                    raise MissingParametersException(
                        "Provided parameters must specify at least one addon config."
                    )

                cloud_run_config_is_disabled, cloud_run_config_load_balancer_type = (
                    MAP_CLOUD_RUN_CONFIG_PARAMS.get(cloud_run_config, (None, None))
                )
                operation = cluster_manager.update_addons(
                    cluster_name,
                    http_load_balancing_disabled=(
                        http_load_balancing == DISABLED
                        if http_load_balancing != NOT_CHANGED
                        else None
                    ),
                    horizontal_pod_autoscaling_disabled=(
                        horizontal_pod_autoscaling == DISABLED
                        if horizontal_pod_autoscaling != NOT_CHANGED
                        else None
                    ),
                    network_policy_config_disabled=(
                        network_policy_config == DISABLED
                        if network_policy_config != NOT_CHANGED
                        else None
                    ),
                    cloud_run_config_disabled=cloud_run_config_is_disabled,
                    cloud_run_config_load_balancer_type=cloud_run_config_load_balancer_type,
                    dns_cache_config_enabled=(
                        dns_cache_record == ENABLED
                        if dns_cache_record != NOT_CHANGED
                        else None
                    ),
                    config_connector_config_enabled=(
                        config_connector_config == ENABLED
                        if config_connector_config != NOT_CHANGED
                        else None
                    ),
                    gce_persistent_disk_csi_driver_config_enabled=(
                        gce_persistent_disk_csi_driver_config == ENABLED
                        if gce_persistent_disk_csi_driver_config != NOT_CHANGED
                        else None
                    ),
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
                    output_message = (
                        "Successfully created cluster configuration change operation."
                    )
                    result_value = True
            except (GoogleGKEInvalidClusterNameError, GoogleGKEInvalidZoneError):
                raise
            except GoogleGKEManagerError as error:
                output_message = f"Failed to execute the action because API returned error, please see action logs: {error}"
                siemplify.LOGGER.error(
                    f"Failed to update cluster with specified addons"
                )
                siemplify.LOGGER.exception(error)
        else:
            operation_name = json.loads(siemplify.parameters["additional_data"])
            operation = operation_manager.get(
                operation_name=operation_name, cluster_name=cluster_name
            )
            output_message, result_value, status = operation_manager.check_status(
                operation,
                is_action_approaching_timeout(
                    siemplify.execution_deadline_unix_time_ms
                ),
            )

        # append json results only if action's execution is finished
        if operation and status != EXECUTION_STATE_INPROGRESS:
            siemplify.result.add_result_json(operation.to_json())

    except (GoogleGKEInvalidClusterNameError, MissingParametersException) as error:
        output_message = f"{error}"
        status = EXECUTION_STATE_FAILED

    except GoogleGKEInvalidZoneError:
        output_message = (
            f'Provided cluster location "{cluster_location}" does not exist.'
        )
        status = EXECUTION_STATE_FAILED

    except Exception as error:
        output_message = f'Error execution action "{SET_CLUSTER_ADDONS_SCRIPT_NAME}". Reason: {error}'
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
