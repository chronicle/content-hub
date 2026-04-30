from ..core.base_action import BaseAction
from ..core.constants import GET_ACTION_RESULT_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got action result!"
ERROR_MESSAGE: str = "Failed getting action result!"


class GetActionResult(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_ACTION_RESULT_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.task_id = self.soar_action.extract_action_param(
            param_name="Task ID",
            print_value=True,
            is_mandatory=True
        )

    def _perform_action(self, _=None) -> None:
        task_id = self.params.task_id
        self.json_results = self.api_client.get_task(task_id=task_id)


def main() -> None:
    GetActionResult().run()


if __name__ == "__main__":
    main()
