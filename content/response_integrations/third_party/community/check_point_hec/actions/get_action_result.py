"""Get Action Result action – polls the status of a previously submitted entity action task."""
from ..core.base_action import BaseAction
from ..core.constants import GET_ACTION_RESULT_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got action result!"
ERROR_MESSAGE: str = "Failed getting action result!"


class GetActionResult(BaseAction):
    """Retrieve the current state of an asynchronous entity or event action task.

    Check Point HEC action endpoints (quarantine, restore, etc.) return a task
    ID.  Use this action to poll that task and check whether it has completed.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_ACTION_RESULT_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract the mandatory *Task ID* parameter."""
        self.params.task_id = self.soar_action.extract_action_param(
            param_name="Task ID",
            print_value=True,
            is_mandatory=True
        )

    def _perform_action(self, _=None) -> None:
        """Query the task endpoint and store the task status in ``json_results``."""
        task_id = self.params.task_id
        self.json_results = self.api_client.get_task(task_id=task_id)


def main() -> None:
    GetActionResult().run()


if __name__ == "__main__":
    main()
