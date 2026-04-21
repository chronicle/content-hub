import json

from ..core.base_action import BaseAction
from ..core.constants import GET_SCAN_INFO_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Scan Info!"
ERROR_MESSAGE: str = "Failed getting Scan Info!"


class GetScanInfo(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_SCAN_INFO_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
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
