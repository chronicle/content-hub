from ..core.base_action import BaseAction
from ..core.constants import DOWNLOAD_EMAIL_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully downloaded email file!"
ERROR_MESSAGE: str = "Failed downloading email file!"


class DownloadEmail(BaseAction):

    def __init__(self) -> None:
        super().__init__(DOWNLOAD_EMAIL_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.entity_id = self.soar_action.extract_action_param(
            param_name="Entity ID",
            print_value=True,
            is_mandatory=True
        )
        self.params.original = self.soar_action.extract_action_param(
            param_name="Original",
            print_value=True,
            is_mandatory=False,
            input_type=bool
        )

    def _perform_action(self, _=None) -> None:
        entity_id = self.params.entity_id
        original = self.params.original
        self.json_results = self.api_client.download_email(entity_id=entity_id, original=original)


def main() -> None:
    DownloadEmail().run()


if __name__ == "__main__":
    main()
