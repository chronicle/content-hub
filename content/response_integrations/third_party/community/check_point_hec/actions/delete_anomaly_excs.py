"""Delete Anomaly Exceptions action – removes one or more anomaly exception rules by ID."""
from ..core.base_action import BaseAction
from ..core.constants import DELETE_ANOMALY_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anomaly exceptions!"
ERROR_MESSAGE: str = "Failed deleting Anomaly exceptions!"


class DeleteAnomalyExceptions(BaseAction):
    """Delete anomaly detection exceptions by their rule IDs.

    Accepts a comma-separated list of rule IDs via the *Rule IDs* parameter
    and submits a bulk-delete request to the anomaly exceptions API.
    """

    def __init__(self) -> None:
        """Initialize the action with its script name and output messages."""
        super().__init__(DELETE_ANOMALY_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract the mandatory *Rule IDs* comma-separated string."""
        self.params.rule_ids = self.soar_action.extract_action_param(
            param_name="Rule IDs",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )

    def _perform_action(self, _=None) -> None:
        """Split the rule-ID string and call the API to delete the exceptions."""
        rule_ids = self.params.rule_ids.split(',')
        self.json_results = self.api_client.delete_anomaly_exceptions(rule_ids=rule_ids)


def main() -> None:
    DeleteAnomalyExceptions().run()


if __name__ == "__main__":
    main()
