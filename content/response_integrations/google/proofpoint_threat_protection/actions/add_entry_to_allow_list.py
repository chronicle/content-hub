from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_valid_email
from proofpoint_threat_protection.core import constants
from proofpoint_threat_protection.core.base_action import ProofpointThreatProtectionAction
from proofpoint_threat_protection.core.exceptions import ProofpointTPError


if TYPE_CHECKING:
    from typing import Any, Never, NoReturn

    from TIPCommon.types import SingleJson


class AddEntryToAllowListAction(ProofpointThreatProtectionAction):
    """
    Add Entry To Allow List action implementation.
    """

    def __init__(self) -> None:
        super().__init__(constants.ADD_ENTRY_TO_ALLOW_LIST_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.cluster_id = extract_action_param(
            self.soar_action,
            param_name="Cluster ID",
            print_value=True,
        )
        self.params.allowlist_item = extract_action_param(
            self.soar_action,
            param_name="Allowlist Item",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        validator = ParameterValidator(self.soar_action)
        self.params.allowlist_item = validator.validate_json(
            param_name="Allowlist Item",
            json_string=self.params.allowlist_item,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        try:
            cluster_id = self._get_cluster_id()
            payload = self._prepare_payload()
            self._validate_payload(payload)
            self.api_client.add_allow_list_entry(cluster_id, payload)
            self._set_action_result()

        except ProofpointTPError as error:
            self._handle_proofpoint_error(error)

    def _get_cluster_id(self) -> str:
        return self.params.cluster_id or self.api_client.cluster_id

    def _prepare_payload(self) -> SingleJson | Any:
        payload: SingleJson | Any = self.params.allowlist_item

        if isinstance(payload, dict) and "action" not in payload:
            payload["action"] = constants.ADD_ACTION

        return payload

    def _validate_payload(self, payload: SingleJson | Any) -> None:
        if not isinstance(payload, dict):
            return

        attribute: str = payload.get("attribute")
        value: str = payload.get("value", "")

        if attribute not in constants.EMAIL_ATTRIBUTES_TO_VALIDATE:
            return

        if is_valid_email(value):
            return

        raise ProofpointTPError(
            f"Invalid email address '{value}' provided for "
            f"attribute '{attribute}' in allowlist Item."
        )

    def _handle_proofpoint_error(self, error: ProofpointTPError) -> None:
        error_str: str = str(error).lower()

        if constants.DUPLICATE_ENTRY_ERROR in error_str:
            self.output_message = "The provided entry already exists in the allow list."
            return

        if str(constants.INVALID_ID_STATUS_CODE) in error_str:
            raise ProofpointTPError(
                "invalid cluster ID provided or "
                "credentials in the integration configuration."
            ) from error

        raise ProofpointTPError(f"Error: {error}") from error

    def _set_action_result(self) -> None:
        self.output_message = "Successfully added a new entry to the allow list."


def main() -> NoReturn:
    AddEntryToAllowListAction().run()


if __name__ == "__main__":
    main()
