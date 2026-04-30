from ..core.base_action import BaseAction
from ..core.constants import DELETE_ANOMALY_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anomaly exceptions!"
ERROR_MESSAGE: str = "Failed deleting Anomaly exceptions!"


class DeleteAnomalyExceptions(BaseAction):

    def __init__(self) -> None:
        super().__init__(DELETE_ANOMALY_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.rule_ids = self.soar_action.extract_action_param(
            param_name="Rule IDs",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )

    def _perform_action(self, _=None) -> None:
        rule_ids = self.params.rule_ids.split(',')
        self.json_results = self.api_client.delete_anomaly_exceptions(rule_ids=rule_ids)


def main() -> None:
    DeleteAnomalyExceptions().run()


if __name__ == "__main__":
    main()
