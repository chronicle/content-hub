"""Get Scan Info action – extracts per-tool security verdicts for a SaaS entity."""
import json

from ..core.base_action import BaseAction
from ..core.constants import GET_SCAN_INFO_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Scan Info!"
ERROR_MESSAGE: str = "Failed getting Scan Info!"


class GetScanInfo(BaseAction):
    """Return the security scan results for each active tool on a given entity.

    Fetches the entity by ID and iterates over ``combinedVerdict`` to collect
    per-tool details.  ``clean`` verdicts are included only when *Include Clean*
    is ``True``.  Tools with a ``None`` verdict (not applicable) are always
    skipped.

    The raw entity response is stored in ``json_results`` and the per-tool
    breakdown is returned as a dict mapping tool name → JSON string.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_SCAN_INFO_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract mandatory *Entity ID* and optional *Include Clean* flag."""
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )
        self.params.include_clean = self.soar_action.extract_action_param(
            param_name="Include Clean",
            print_value=True,
            is_mandatory=False,
            default_value=False,
            input_type=bool
        )

    def _perform_action(self, _=None) -> dict:
        """Fetch entity details and build a tool-verdict mapping.

        Returns:
            dict: Mapping of tool name to JSON-serialised tool-level scan data
                for all tools whose verdict is not ``None`` and (optionally)
                not ``clean``.
        """
        entity_id = self.params.entity_id
        include_clean = self.params.include_clean

        result = self.api_client.get_entity(entity_id)
        self.json_results = result
        outputs = {}

        if entities := result.get("responseData"):
            sec_result = entities[0]["entitySecurityResult"]
            for tool, verdict in sec_result["combinedVerdict"].items():
                if verdict is not None and (include_clean or verdict != "clean"):
                    outputs[tool] = json.dumps(sec_result[tool])

        return outputs


def main() -> None:
    GetScanInfo().run()


if __name__ == "__main__":
    main()
