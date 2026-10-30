from __future__ import annotations

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from ..core.constants import (
    DEFAULT_PASSWORD_LENGTH,
    GENERATE_RANDOM_PASSWORD_SCRIPT_NAME,
    MIN_PASSWORD_LENGTH,
)
from ..core.utils import generate_random_password


class GenerateRandomPassword(Action):
    """Generate a temporary password that meets Okta complexity rules."""

    def __init__(self) -> None:
        super().__init__(GENERATE_RANDOM_PASSWORD_SCRIPT_NAME)
        self.length: int = DEFAULT_PASSWORD_LENGTH

    def _init_api_clients(self) -> None:
        """No remote API client."""

    def _extract_action_parameters(self) -> None:
        raw_length = extract_action_param(
            self.soar_action,
            param_name="Length",
            default_value=str(DEFAULT_PASSWORD_LENGTH),
            print_value=True,
        )
        try:
            self.length = int(str(raw_length or DEFAULT_PASSWORD_LENGTH).strip())
        except ValueError as error:
            raise ValueError("Length must be an integer.") from error

    def _perform_action(self, _=None) -> None:
        if self.length < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password length must be at least {MIN_PASSWORD_LENGTH} characters.")
        password = generate_random_password(self.length)
        self.json_results = {"password": password}
        self.output_message = f"Generated a {self.length}-character temporary password."


def main() -> None:
    GenerateRandomPassword().run()


if __name__ == "__main__":
    main()
