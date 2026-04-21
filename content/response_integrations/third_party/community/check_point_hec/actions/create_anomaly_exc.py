import json

from TIPCommon.validation import ParameterValidator

from ..core.base_action import BaseAction
from ..core.constants import CREATE_ANOMALY_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Anomaly exception!"
ERROR_MESSAGE: str = "Failed creating Anomaly exception!"


class CreateAnomalyException(BaseAction):

    def __init__(self) -> None:
        super().__init__(CREATE_ANOMALY_EXC_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.request_json = self.soar_action.parameters.get(
            siemplify=self.soar_action,
            param_name="Request JSON",
            print_value=True,
            is_mandatory=True
        )
        self.params.added_by = self.soar_action.extract_action_param(
            param_name="Added By",
            print_value=True,
            is_mandatory=False
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        validator.validate_json(param_name="Request JSON", json_string=self.params.request_json)

    def _perform_action(self, _=None) -> None:
        request_json = json.loads(self.params.request_json)
        added_by = self.params.added_by
        self.json_results = self.api_client.create_anomaly_exception(request_json=request_json, added_by=added_by)


def main() -> None:
    CreateAnomalyException().run()


if __name__ == "__main__":
    main()
