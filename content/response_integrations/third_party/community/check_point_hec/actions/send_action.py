from ..core.base_action import BaseAction
from ..core.constants import SEND_ACTION_SCRIPT_NAME, SAAS_APPS_TO_SAAS_NAMES

SUCCESS_MESSAGE: str = "Action sent successfully!"
ERROR_MESSAGE: str = "Failed sending action!"


class SendAction(BaseAction):

    def __init__(self) -> None:
        super().__init__(SEND_ACTION_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.entity_list = self.soar_action.extract_action_param(
            param_name="Entities",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.saas = self.soar_action.extract_action_param(
            param_name="SaaS",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.action = self.soar_action.extract_action_param(
            param_name="Action",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.restore_decline_reason = self.soar_action.extract_action_param(
            param_name="Restore Decline Reason",
            print_value=True,
            is_mandatory=False
        )

    def _perform_action(self, _=None) -> None:
        entities = self.params.entity_list.split(',')
        entity_type = SAAS_APPS_TO_SAAS_NAMES[self.params.saas] + "_email"
        action = self.params.action
        restore_decline_reason = self.params.restore_decline_reason

        self.json_results = self.api_client.entity_action(
            entity_list=entities,
            entity_type=entity_type,
            action=action,
            restore_decline_reason=restore_decline_reason
        )


def main() -> None:
    SendAction().run()


if __name__ == "__main__":
    main()
