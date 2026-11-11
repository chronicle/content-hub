from __future__ import annotations

from TIPCommon.base.action.data_models import DataTable
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator

from google_gke.core.GKEBaseAction import GKEBaseAction
from google_gke.core.GKEConsts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    LIST_NODE_POOLS_SCRIPT_NAME,
    ALL_CLUSTERS,
    NOT_SPECIFIED,
)
from google_gke.core.GKEDatamodels import FilterLogicParam, KubeClusterNodePool
from google_gke.core.GKEExceptions import GoogleGKEInvalidZoneError
from google_gke.core.GKEServices import GKEClusterNodesService
from google_gke.core.GKEUtils import get_filtered_objects


class ListNodePools(GKEBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self._gke_service_class = GKEClusterNodesService

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        try:
            self.params.max_records_to_return = validator.validate_positive(
                param_name="Max Records To Return",
                value=self.params.max_records_to_return,
            )
        except Exception as err:
            self.result_value = False
            self.error_output_message = (
                'Invalid value was provided for "Max Records to Return": '
                f"{self.params.max_records_to_return}. Positive number should be "
                "provided."
            )
            raise err from err

    def _extract_action_params(self) -> None:
        self.params.filter_logic = extract_action_param(
            self.soar_action,
            param_name="Filter Logic",
            default_value=f"{FilterLogicParam.EQUAL}",
            print_value=True,
        )
        self.params.filter_value = extract_action_param(
            self.soar_action, param_name="Filter Value", print_value=True
        )
        self.params.max_records_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Records To Return",
            print_value=True,
            default_value="50",
        )

    def _extract_service_params(self) -> None:
        self._service_params.target_project_id = extract_action_param(
            self.soar_action, param_name="Project ID", print_value=True
        )
        self._service_params.zone_name = extract_action_param(
            self.soar_action,
            param_name="Cluster Location",
            is_mandatory=True,
            print_value=True,
        )
        self._service_params.cluster_name = extract_action_param(
            self.soar_action,
            param_name="Cluster Name",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(
        self, manager: GKEClusterNodesService | None = None, _=None
    ) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        try:
            node_pools = manager.list()
            zone_name_str = (
                f"zone {self._service_params.zone_name}"
                if self._service_params.zone_name != ALL_CLUSTERS
                else "all zones"
            )
            self.logger.info(
                f"Found {len(node_pools)} node pools in cluster "
                f"{self._service_params.cluster_name} of {zone_name_str} in "
                f"{INTEGRATION_DISPLAY_NAME}"
            )

            filtered_node_pools = node_pools
            if self.params.filter_logic != NOT_SPECIFIED and self.params.filter_value:
                filtered_node_pools = get_filtered_objects(
                    node_pools,
                    KubeClusterNodePool.get_name_attribute(),
                    self.params.filter_logic,
                    self.params.filter_value,
                )
                self.logger.info(
                    f"Filtered {len(filtered_node_pools)} node pools by "
                    f'filter logic "{self.params.filter_logic}" '
                    f"and value {self.params.filter_value}"
                )

            filtered_node_pools = filtered_node_pools[
                : self.params.max_records_to_return
            ]

            if not filtered_node_pools:
                self.output_message = (
                    f"No node pools were found for cluster "
                    f'"{self._service_params.cluster_name}" for the provided '
                    f"criteria in {INTEGRATION_DISPLAY_NAME}."
                )
                self.result_value = False
                return

            self.output_message = (
                f"Successfully found node pools for cluster "
                f'"{self._service_params.cluster_name}" for the provided criteria '
                f"in {INTEGRATION_DISPLAY_NAME}."
            )
            self.data_tables.append(
                DataTable(
                    title="Found Node Pools",
                    data_table=construct_csv(
                        [node_pool.to_csv() for node_pool in filtered_node_pools]
                    ),
                )
            )
            self.json_results = {
                "nodePools": [node_pool.to_json() for node_pool in filtered_node_pools],
                "cluster_name": self._service_params.cluster_name,
            }

        except GoogleGKEInvalidZoneError as e:
            raise GoogleGKEInvalidZoneError(
                f'Provided cluster location "{self._service_params.cluster_location}"'
                f" does not exist."
            ) from e


def main() -> None:
    ListNodePools(f"{INTEGRATION_IDENTIFIER} - {LIST_NODE_POOLS_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()
