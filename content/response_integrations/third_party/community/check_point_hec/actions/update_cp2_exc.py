"""Update Anti-Malware Exception action – modifies an existing CP2 sectool exception."""
from ..core.update_sectool_exc import UpdateSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, UPDATE_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed updating Anti-Malware exception!"


class UpdateCP2Exception(UpdateSectoolException):
    """Update an existing Check Point Anti-Malware (``checkpoint2``) sectool exception.

    Delegates parameter extraction and the API call to
    :class:`~core.update_sectool_exc.UpdateSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Anti-Malware sectool name and action messages."""
        super().__init__(
            name=UPDATE_CP2_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    UpdateCP2Exception().run()


if __name__ == "__main__":
    main()
