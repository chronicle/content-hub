from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from proofpoint_threat_protection.core import constants
from proofpoint_threat_protection.core.base_action import ProofpointThreatProtectionAction
from proofpoint_threat_protection.core.exceptions import ProofpointTPError

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from proofpoint_threat_protection.core.data_models import AllowEntry
    from TIPCommon.types import SingleJson


class RemoveEntryFromAllowListAction(ProofpointThreatProtectionAction):
    """
    Remove Entry From Allow List action implementation.
    """

    def __init__(self) -> None:
        super().__init__(constants.REMOVE_ENTRY_FROM_ALLOW_LIST_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.cluster_id = extract_action_param(
            self.soar_action,
            param_name="Cluster ID",
            print_value=True,
        )
        self.params.ioc_type = extract_action_param(
            self.soar_action,
            param_name="IOC Type To Search",
            default_value=constants.IOC_TYPE_ALL,
            print_value=True,
        )
        self.params.value = extract_action_param(
            self.soar_action,
            param_name="Value",
            is_mandatory=True,
            print_value=True,
        )
        self.params.case_insensitive = extract_action_param(
            self.soar_action,
            param_name="Case Insensitive Search",
            input_type=bool,
            default_value=True,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        cluster_id = self._get_cluster_id()

        attributes_to_remove = self._resolve_attributes(cluster_id)

        removed_count = self._remove_entries(attributes_to_remove, cluster_id)
        self._set_action_result(removed_count > 0)

    def _get_cluster_id(self) -> str:
        return self.params.cluster_id or self.api_client.cluster_id

    def _resolve_attributes(self, cluster_id: str) -> list[str]:
        if self.params.case_insensitive:
            return self._get_attributes_to_remove()

        return self._get_exact_match_attributes(cluster_id)

    def _get_exact_match_attributes(self, cluster_id: str) -> list[str]:
        self.logger.info(f"Fetching allow list entries for cluster {cluster_id}")

        all_entries: list[AllowEntry] = self.api_client.get_allow_list_entries(
            cluster_id
        )

        def is_match(entry: AllowEntry) -> bool:
            value_match = entry.value == self.params.value
            if self.params.ioc_type == constants.IOC_TYPE_ALL:
                return value_match

            attribute_to_search = constants.IOC_TYPE_MAPPING.get(self.params.ioc_type)
            if not attribute_to_search:
                raise ProofpointTPError(f"Invalid IOC Type: {self.params.ioc_type}")

            return value_match and entry.attribute == attribute_to_search

        matching_entry = next(
            (entry for entry in all_entries if is_match(entry)),
            None,
        )

        if not matching_entry:
            return []

        return [matching_entry.attribute]

    def _remove_entries(self, attributes_to_remove: list[str], cluster_id: str) -> int:
        removed_count = 0

        for attribute in attributes_to_remove:
            payload: SingleJson = {
                "action": "delete",
                "attribute": attribute,
                "operator": "equal",
                "value": self.params.value,
            }

            try:
                self.logger.info(
                    f"Removing entry from allow list for cluster {cluster_id}"
                )
                self.api_client.remove_allow_list_entry(cluster_id, payload)
                removed_count += 1

            except ProofpointTPError as error:
                error_str = str(error)

                if "error.api.emailprotection.lists.invalid.entry" in error_str:
                    self.logger.error(
                        f"Failed to remove entry with attribute '{attribute}' "
                        f"and value '{self.params.value}' or value is not found."
                    )
                    continue

                if str(constants.INVALID_ID_STATUS_CODE) in error_str:
                    raise ProofpointTPError(
                        "invalid cluster ID provided or "
                        "credentials in the integration configuration."
                    ) from error

                raise ProofpointTPError(f"Error: {error}") from error

        return removed_count

    def _get_attributes_to_remove(self) -> list[str]:
        if self.params.ioc_type == constants.IOC_TYPE_ALL:
            return list(constants.IOC_TYPE_MAPPING.values())

        attribute = constants.IOC_TYPE_MAPPING.get(self.params.ioc_type)
        if not attribute:
            raise ProofpointTPError(f"Invalid IOC Type: {self.params.ioc_type}")

        return [attribute]

    def _set_action_result(self, was_removed: bool) -> None:
        self.result_value = True

        if was_removed:
            self.output_message = (
                "Successfully deleted entry in the allow list "
                "based on the provided criteria"
            )
            return

        self.output_message = (
            "No matching entries were found to remove from the allow list "
            "for the provided criteria."
        )


def main() -> NoReturn:
    RemoveEntryFromAllowListAction().run()


if __name__ == "__main__":
    main()
