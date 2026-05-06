"""Get Entity action – retrieves full details for a single SaaS entity by ID."""
from ..core.base_action import BaseAction
from ..core.constants import GET_ENTITY_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Entity!"
ERROR_MESSAGE: str = "Failed getting Entity!"


class GetEntity(BaseAction):
    """Retrieve detailed information for a single SaaS entity.

    The entity ID typically comes from a security event and can be used to look
    up the full email or file record associated with that event.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_ENTITY_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract the mandatory *Entity ID* parameter."""
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=True,
            default_value=None
        )

    def _perform_action(self, _=None) -> None:
        """Call the entity search API and store the result in ``json_results``."""
        entity_id = self.params.entity_id
        self.json_results = self.api_client.get_entity(entity_id)


def main() -> None:
    GetEntity().run()


if __name__ == "__main__":
    main()
