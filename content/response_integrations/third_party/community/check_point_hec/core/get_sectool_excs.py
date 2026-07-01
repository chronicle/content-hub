from .base_action import BaseAction


class GetSectoolExceptions(BaseAction):

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
        self.params.filter_string = self.soar_action.extract_action_param(
            param_name="Filter String",
            print_value=True,
            is_mandatory=False
        )
        self.params.filter_index = self.soar_action.extract_action_param(
            param_name="Filter Index",
            print_value=True,
            is_mandatory=False
        )
        self.params.sort_direction = self.soar_action.extract_action_param(
            param_name="Sort Direction",
            print_value=True,
            is_mandatory=False
        )
        self.params.last_evaluated_key = self.soar_action.extract_action_param(
            param_name="Last Evaluated Key",
            print_value=True,
            is_mandatory=False
        )
        self.params.insert_time_gte = self.soar_action.extract_action_param(
            param_name="Insert Time GTE",
            print_value=True,
            is_mandatory=False,
            default_value=False,
            input_type=bool
        )
        self.params.limit = self.soar_action.extract_action_param(
            param_name="Limit",
            print_value=True,
            is_mandatory=False,
            input_type=int
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        filter_string = self.params.filter_string
        filter_index = self.params.filter_index
        sort_direction = self.params.sort_direction
        last_evaluated_key = self.params.last_evaluated_key
        insert_time_gte = self.params.insert_time_gte
        limit = self.params.limit

        exception_data = {
            'filterStr': filter_string,
            'filterIndex': filter_index,
            'sortDir': sort_direction,
            'lastEvaluatedKey': last_evaluated_key,
            'insertTimeGte': insert_time_gte,
            'limit': limit
        }
        self.json_results = self.api_client.get_sectool_exceptions(
            sectool=self.sectool_name,
            exception_type=exception_type,
            exception_data=exception_data
        )
