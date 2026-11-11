from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import is_valid_email
from proofpoint_threat_protection.core import constants
from proofpoint_threat_protection.core.base_action import ProofpointThreatProtectionAction
from proofpoint_threat_protection.core.exceptions import ProofpointTPError

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from TIPCommon.types import SingleJson


class AddIocToAllowListAction(ProofpointThreatProtectionAction):
    """
    Add IOC To Allow List action implementation.
    """

    def __init__(self) -> None:
        super().__init__(constants.ADD_IOC_TO_ALLOW_LIST_SCRIPT_NAME)
        self.failed_entries: list[str] = []
        self.total_iocs: int = constants.NULL

    def _extract_action_parameters(self) -> None:
        self.params.cluster_id = extract_action_param(
            self.soar_action,
            param_name="Cluster ID",
            print_value=True,
        )
        self.params.recipient_email = extract_action_param(
            self.soar_action,
            param_name="Recipient Email Address",
            print_value=True,
        )
        self.params.sender_email = extract_action_param(
            self.soar_action,
            param_name="Sender Email Address",
            print_value=True,
        )
        self.params.sender_ip = extract_action_param(
            self.soar_action,
            param_name="Sender IP Address",
            print_value=True,
        )
        self.params.sender_hostname = extract_action_param(
            self.soar_action,
            param_name="Sender Hostname",
            print_value=True,
        )
        self.params.sender_helo = extract_action_param(
            self.soar_action,
            param_name="Sender HELO Domain Name",
            print_value=True,
        )
        self.params.header_from = extract_action_param(
            self.soar_action,
            param_name="Message Header From (Address Only)",
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        cluster_id: str = self._get_cluster_id()

        ioc_payloads = self._prepare_ioc_payloads()

        if not ioc_payloads:
            raise ProofpointTPError(
                "No IOCs provided. Please specify at least one IOC to add."
            )
        self.logger.info(f"Adding IOCs to allow list for cluster {cluster_id}")
        self._add_iocs_to_allow_list(ioc_payloads, cluster_id)

        if self.failed_entries:
            self._failed_message()

        self._set_action_result()

    def _get_cluster_id(self) -> str:
        return self.params.cluster_id or self.api_client.cluster_id

    def _add_iocs_to_allow_list(
        self,
        ioc_payloads: list[SingleJson],
        cluster_id: str,
    ) -> None:
        self.logger.info(f"Found {len(ioc_payloads)} IOCs to add.")

        for payload in ioc_payloads:
            self._add_single_ioc(payload, cluster_id)

    def _add_single_ioc(
        self,
        payload: SingleJson,
        cluster_id: str,
    ) -> None:
        try:
            self.api_client.add_allow_list_entry(cluster_id, payload)
        except ProofpointTPError as error:
            self._handle_add_error(error, payload)

    def _handle_add_error(
        self,
        error: ProofpointTPError,
        payload: SingleJson,
    ) -> None:
        error_str: str = str(error).lower()

        if constants.DUPLICATE_ENTRY_ERROR in error_str:
            self.logger.info(
                f"Entry with value '{payload['value']}' and attribute "
                f"'{payload['attribute']}' already exists. Skipping."
            )
            return

        if str(constants.INVALID_ID_STATUS_CODE) in error_str:
            raise ProofpointTPError(
                "invalid cluster ID provided or "
                "credentials in the integration configuration."
            ) from error

        self.failed_entries.append(f"{payload['attribute']}: {payload['value']}")
        self.logger.error(f"Failed to add entry: {payload['value']}. Error: {error}")

    def _prepare_ioc_payloads(self) -> list[SingleJson]:
        payloads: list[SingleJson] = []

        for ioc_values_csv, attribute in self._build_ioc_map():
            if not ioc_values_csv:
                continue

            self._process_ioc_values(ioc_values_csv, attribute, payloads)

        if self.failed_entries and not payloads:
            self._failed_message()

        return payloads

    def _build_ioc_map(self) -> list[tuple[str | None, str]]:
        return [
            (
                self.params.recipient_email,
                constants.IOC_TYPE_MAPPING["Recipient Email Address"],
            ),
            (
                self.params.sender_email,
                constants.IOC_TYPE_MAPPING["Sender Email Address"],
            ),
            (
                self.params.sender_ip,
                constants.IOC_TYPE_MAPPING["Sender IP Address"],
            ),
            (
                self.params.sender_hostname,
                constants.IOC_TYPE_MAPPING["Sender Hostname"],
            ),
            (
                self.params.sender_helo,
                constants.IOC_TYPE_MAPPING["Sender HELO Domain Name"],
            ),
            (
                self.params.header_from,
                constants.IOC_TYPE_MAPPING["Message Header From (Address Only)"],
            ),
        ]

    def _process_ioc_values(
        self,
        ioc_values_csv: str,
        attribute: str,
        payloads: list[SingleJson],
    ) -> None:
        for value in string_to_multi_value(ioc_values_csv):
            self.total_iocs += 1

            if not self._is_valid_ioc(attribute, value):
                continue

            payloads.append(self._build_payload(attribute, value))

    def _is_valid_ioc(self, attribute: str, value: str) -> bool:
        if attribute not in constants.EMAIL_ATTRIBUTES_TO_VALIDATE:
            return True

        if is_valid_email(value):
            return True

        self.logger.error(
            f"Invalid email address '{value}' provided for attribute " f"'{attribute}'."
        )
        self.failed_entries.append(f"{attribute}: {value}")
        return False

    def _build_payload(self, attribute: str, value: str) -> SingleJson:
        return {
            "action": constants.ADD_ACTION,
            "attribute": attribute,
            "operator": "equal",
            "value": value,
            "comment": self.params.comment or "",
        }

    def _failed_message(self) -> None:
        raise ProofpointTPError(
            "The following entries couldn’t be added to the allow list: "
            f"{', '.join(self.failed_entries)}. Please check the spelling and try "
            "again."
            + (
                " All other entries were added."
                if self.total_iocs > len(self.failed_entries)
                else ""
            )
        )

    def _set_action_result(self) -> None:
        self.result_value = True
        self.output_message = "Successfully added new entries to the allow list."


def main() -> NoReturn:
    AddIocToAllowListAction().run()


if __name__ == "__main__":
    main()
