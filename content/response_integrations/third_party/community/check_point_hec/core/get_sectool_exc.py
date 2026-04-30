from .base_action import BaseAction


class GetSectoolException(BaseAction):

    def __init__(
            self,
            name: str,
            output_message: str,
            error_output: str,
            sectool_name: str
    ) -> None:
        super().__init__(name)
        self.output_message: str = output_message
        self.error_output_message: str = error_output
        self.sectool_name: str = sectool_name

    def _extract_action_parameters(self) -> None:
        self.params.exception_type = self.soar_action.extract_action_param(
            param_name="Exception Type",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.exception_string = self.soar_action.extract_action_param(
            param_name="Exception String",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        exception_string = self.params.exception_string

        self.json_results = self.api_client.get_sectool_exception(
            sectool=self.sectool_name,
            exception_type=exception_type,
            exception_string=exception_string
        )
