from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from proofpoint_threat_protection.core import constants
from proofpoint_threat_protection.core.base_action import ProofpointThreatProtectionAction
from proofpoint_threat_protection.core.exceptions import ProofpointTPError

if TYPE_CHECKING:
    from typing import Never, NoReturn
    from proofpoint_threat_protection.core.data_models import BlockEntry


class GetBlockListEntriesAction(ProofpointThreatProtectionAction):
    """
    Get Block List Entries action implementation.
    """

    def __init__(self) -> None:
        super().__init__(constants.GET_BLOCK_LIST_ENTRIES_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.cluster_id = extract_action_param(
            self.soar_action,
            param_name="Cluster ID",
            print_value=True,
        )
        self.params.ioc_type = extract_action_param(
            self.soar_action,
            param_name="IOC Type To Return",
            default_value=constants.IOC_TYPE_ALL,
            print_value=True,
        )
        self.params.max_iocs = extract_action_param(
            self.soar_action,
            param_name="Max IOCs To Return",
            input_type=int,
            default_value=100,
            print_value=True,
        )

    def _validate_params(self) -> None:
        ParameterValidator(self.soar_action).validate_range(
            "Max IOCs To Return",
            self.params.max_iocs,
            constants.MIN_ENTRIES_LIMIT,
            constants.MAX_ENTRIES_LIMIT,
        )

    def _perform_action(self, _: Never) -> None:
        try:
            cluster_id = self._get_cluster_id()

            entries = self._fetch_block_entries(cluster_id)
            filtered_entries = self._filter_entries(entries)

            self._set_action_result(filtered_entries)

        except ProofpointTPError as error:
            self._handle_proofpoint_error(error)

    def _get_cluster_id(self) -> str:
        return self.params.cluster_id or self.api_client.cluster_id

    def _fetch_block_entries(self, cluster_id: str) -> list[BlockEntry]:
        self.logger.info(f"Fetching block list entries for cluster {cluster_id}")
        return self.api_client.get_block_list_entries(cluster_id)

    def _filter_entries(self, entries: list[BlockEntry]) -> list[BlockEntry]:

        if self.params.ioc_type == constants.IOC_TYPE_ALL:
            return entries[: self.params.max_iocs]

        attribute_to_filter = constants.IOC_TYPE_MAPPING[self.params.ioc_type]

        filtered = [
            entry for entry in entries if entry.attribute == attribute_to_filter
        ]

        return filtered[: self.params.max_iocs]

    def _handle_proofpoint_error(self, error: ProofpointTPError) -> None:
        error_str = str(error)

        if str(constants.INVALID_ID_STATUS_CODE) in error_str:
            raise ProofpointTPError(
                "invalid cluster ID provided or "
                "credentials in the integration configuration."
            ) from error

        raise ProofpointTPError(f"Error: {error}") from error

    def _set_action_result(self, entries: list[BlockEntry]) -> None:
        if not entries:
            self.output_message = (
                "No entries were found in the block list for the provided criteria."
            )
            return

        self.json_results = [entry.to_json() for entry in entries]
        self.output_message = (
            "Successfully listed entries in the "
            "block list based on the provided criteria."
        )


def main() -> NoReturn:
    GetBlockListEntriesAction().run()


if __name__ == "__main__":
    main()
