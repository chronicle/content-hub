from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    from ..core.constants import (
        DEFAULT_PASSWORD_LENGTH,
        GENERATE_RANDOM_PASSWORD_SCRIPT_NAME,
        MIN_PASSWORD_LENGTH,
    )
    from ..core.utils import format_user_facing_error, generate_random_password

    siemplify.script_name = GENERATE_RANDOM_PASSWORD_SCRIPT_NAME
    try:
        raw_length = siemplify.extract_action_param("Length", default_value=str(DEFAULT_PASSWORD_LENGTH))
        try:
            length = int(str(raw_length or DEFAULT_PASSWORD_LENGTH).strip())
        except ValueError as error:
            raise ValueError("Length must be an integer.") from error
        if length < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password length must be at least {MIN_PASSWORD_LENGTH} characters.")
        password = generate_random_password(length)
        siemplify.result.add_result_json({"password": password})
        siemplify.end(
            f"Generated a {length}-character temporary password.",
            password,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as error:
        message = f'Error executing action "Generate Random Password". Reason: {format_user_facing_error(error)}'
        siemplify.LOGGER.error(message)
        siemplify.end(message, False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
