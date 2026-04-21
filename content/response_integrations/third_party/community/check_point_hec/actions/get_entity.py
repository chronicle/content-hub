from ..core.base_action import BaseAction
from ..core.constants import GET_ENTITY_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Entity!"
ERROR_MESSAGE: str = "Failed getting Entity!"


class GetEntity(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_ENTITY_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        entity_id = self.params.entity_id
        self.json_results = self.api_client.get_entity(entity_id)


def main() -> None:
    GetEntity().run()


if __name__ == "__main__":
    main()
