from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_CDM_CLUSTER_CONNECTION_STATE_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import CDMClusterConnectionStateDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    get_integration_params,
    validate_required_string,
)


@output_handler
def main():
    """Retrieve CDM Cluster Connection State from Rubrik Security Cloud.

    This action retrieves the connection state information for a specific CDM
    (Cloud Data Management) cluster, including details about all nodes in the cluster.

    Action Parameters:
        Cluster ID (str, required): The unique identifier of the CDM cluster

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the retrieval results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If the Cluster ID parameter is invalid or empty
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CDM_CLUSTER_CONNECTION_STATE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    cluster_id = siemplify.extract_action_param(
        param_name="Cluster ID", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        cluster_id = validate_required_string(cluster_id, "Cluster ID")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(
            f"Retrieving CDM Cluster Connection State for Cluster ID: {cluster_id}"
        )
        response = rubrik_manager.get_cdm_cluster_connection_state(cluster_id=cluster_id)

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        data = response.get("data", {})
        cluster_connection = data.get("clusterConnection", {})
        nodes = cluster_connection.get("nodes", [])

        connection_state_data = CDMClusterConnectionStateDatamodel(cluster_id, nodes)

        output_message = (
            f"Successfully retrieved CDM Cluster Connection State for Cluster ID: {cluster_id}"
        )
        table_data = connection_state_data.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table(
                "CDM Cluster Connection State", construct_csv(consise_table_data), "RSC"
            )

    except (RubrikException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_CDM_CLUSTER_CONNECTION_STATE_SCRIPT_NAME, str(e)
        )
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
