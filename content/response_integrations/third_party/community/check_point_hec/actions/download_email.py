"""Download Email action – retrieves the raw email file for a given entity ID."""
from ..core.base_action import BaseAction
from ..core.constants import DOWNLOAD_EMAIL_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully downloaded email file!"
ERROR_MESSAGE: str = "Failed downloading email file!"


class DownloadEmail(BaseAction):
    """Download the email file associated with a SaaS entity.

    Supports downloading the email either in its original form or with
    Check Point HEC modifications applied, controlled by the *Original*
    boolean parameter.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(DOWNLOAD_EMAIL_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract the mandatory *Entity ID* and optional *Original* flag."""
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
        """Call the download API and store the result in ``json_results``."""
        entity_id = self.params.entity_id
        original = self.params.original
        self.json_results = self.api_client.download_email(entity_id=entity_id, original=original)


def main() -> None:
    DownloadEmail().run()


if __name__ == "__main__":
    main()
