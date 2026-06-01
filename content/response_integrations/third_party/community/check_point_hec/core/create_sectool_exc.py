from .base_action import BaseAction


class CreateSectoolException(BaseAction):

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
        self.params.comment = self.soar_action.extract_action_param(
            param_name="Comment",
            print_value=True,
            is_mandatory=False
        )
        self.params.exception_payload_condition = self.soar_action.extract_action_param(
            param_name="Exception Payload Condition",
            print_value=True,
            is_mandatory=False
        )
        self.params.file_name = self.soar_action.extract_action_param(
            param_name="File Name",
            print_value=True,
            is_mandatory=False
        )
        self.params.created_by_email = self.soar_action.extract_action_param(
            param_name="Created By Email",
            print_value=True,
            is_mandatory=False
        )
        self.params.is_exclusive = self.soar_action.extract_action_param(
            param_name="Is Exclusive",
            print_value=True,
            is_mandatory=False,
            input_type=bool
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        exception_string = self.params.exception_string
        entity_type = self.params.entity_type
        entity_id = self.params.entity_id
        comment = self.params.comment
        exception_payload_condition = self.params.exception_payload_condition
        file_name = self.params.file_name
        created_by_email = self.params.created_by_email
        is_exclusive = self.params.is_exclusive

        exception = {
            'exceptionType':exception_type,
            'exceptionStr':exception_string,
            'entityType':entity_type,
            'entityId':entity_id,
            'fileName':file_name,
            'createdByEmail':created_by_email,
            'isExclusive':is_exclusive,
            'comment':comment
        }
        if exception_payload_condition:
            exception["exceptionPayload"] = {
                "condition": exception_payload_condition
            }
        self.json_results = self.api_client.create_sectool_exception(
            self.sectool_name,
            exception
        )
