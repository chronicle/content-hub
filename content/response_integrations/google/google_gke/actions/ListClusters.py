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
    LIST_CLUSTERS_SCRIPT_NAME,
    NOT_SPECIFIED,
)
from google_gke.core.GKEDatamodels import FilterLogicParam, KubeCluster
from google_gke.core.GKEExceptions import GoogleGKEInvalidZoneError
from google_gke.core.GKEServices import GKEClustersService
from google_gke.core.GKEUtils import get_filtered_objects


class ListClusters(GKEBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            "Successfully found operations for cluster for the provided criteria in "
            f"{INTEGRATION_DISPLAY_NAME}."
        )
        self._gke_service_class = GKEClustersService

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

    def _perform_action(
        self, manager: GKEClustersService | None = None, _=None
    ) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        try:
            clusters = manager.list()
            self.logger.info(
                f"Found {len(clusters)} cluster in {INTEGRATION_DISPLAY_NAME}"
            )

            if self.params.filter_logic != NOT_SPECIFIED and self.params.filter_value:
                filtered_clusters = get_filtered_objects(
                    clusters,
                    KubeCluster.get_name_attribute(),
                    self.params.filter_logic,
                    self.params.filter_value,
                )
                self.logger.info(
                    f"Filtered {len(filtered_clusters)} clusters by "
                    f'filter logic "{self.params.filter_logic}" '
                    f"and value {self.params.filter_value}"
                )
            else:
                filtered_clusters = clusters
            filtered_clusters = filtered_clusters[: self.params.max_records_to_return]

            if not filtered_clusters:
                self.output_message = (
                    f"No clusters were found for the provided criteria "
                    f"in {INTEGRATION_DISPLAY_NAME}."
                )
                self.result_value = False
                return

            self.data_tables.append(
                DataTable(
                    title="Found Clusters",
                    data_table=construct_csv(
                        [cluster.to_csv() for cluster in filtered_clusters]
                    ),
                )
            )
            self.json_results = {
                "clusters": [cluster.to_json() for cluster in filtered_clusters]
            }

        except GoogleGKEInvalidZoneError as e:
            raise GoogleGKEInvalidZoneError(
                f'Provided cluster location "{self._service_params.zone_name}" '
                f"does not exist."
            ) from e


def main() -> None:
    ListClusters(f"{INTEGRATION_IDENTIFIER} - {LIST_CLUSTERS_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()
