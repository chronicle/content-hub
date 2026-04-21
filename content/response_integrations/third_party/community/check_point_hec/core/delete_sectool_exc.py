from .base_action import BaseAction


class DeleteSectoolException(BaseAction):

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
        self.params.entity_type = self.soar_action.extract_action_param(
            param_name="Entity Type",
            print_value=True,
            is_mandatory=False
        )
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=False
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        exception_string = self.params.exception_string
        entity_type = self.params.entity_type
        entity_id = self.params.entity_id

        exception = {
            'exceptionType':exception_type,
            'exceptionStr':exception_string,
            'entityType':entity_type,
            'entityId':entity_id
        }
        self.json_results = self.api_client.delete_sectool_exception(
            sectool=self.sectool_name,
            exception=exception
        )
