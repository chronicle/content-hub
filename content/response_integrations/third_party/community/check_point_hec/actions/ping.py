"""Ping action – verifies connectivity and API key permissions for Check Point HEC."""
from ..core.base_action import BaseAction
from ..core.constants import PING_SCRIPT_NAME
from ..core.exceptions import CheckPointHECPermissionsError

SUCCESS_MESSAGE: str = "Successfully connected to the Smart API Service with the provided connection parameters!"
ERROR_MESSAGE: str = "Failed to connect to the Smart API Service!"


class Ping(BaseAction):
    """Verify that the configured credentials can reach the Check Point HEC Smart API.

    The action calls the *scopes* endpoint and validates that exactly one scope
    is returned in the expected ``<farm>:<customer>`` format.  If the API key
    lacks sufficient permissions, a :class:`~core.exceptions.CheckPointHECPermissionsError`
    is raised.
    """

    def __init__(self) -> None:
        """Initialise the Ping action with its script name and output messages."""
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Call the scopes endpoint and validate the returned scope list.

        Raises:
            CheckPointHECPermissionsError: If the API key does not return exactly
                one scope in ``<farm>:<customer>`` format.
        """
        result = self.api_client.get_scopes()
        scopes = result.get("responseData")

        if not isinstance(scopes, list) or len(scopes) != 1 or len(scopes[0].split(":")) != 2:
            raise CheckPointHECPermissionsError(
                "The provided API Key does not have sufficient permissions to access the Smart API Service."
            )


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
