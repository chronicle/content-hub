"""Get Anti-Malware Exceptions action – retrieves a filtered list of CP2 exceptions."""
from ..core.get_sectool_excs import GetSectoolExceptions
from ..core.constants import ANTI_MALWARE_SAAS_NAME, GET_CP2_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anti-Malware exceptions!"
ERROR_MESSAGE: str = "Failed getting Anti-Malware exceptions!"


class GetCP2Exceptions(GetSectoolExceptions):
    """Retrieve a list of Check Point Anti-Malware (``checkpoint2``) sectool exceptions.

    Supports optional filtering and pagination parameters inherited from
    :class:`~core.get_sectool_excs.GetSectoolExceptions`.
    """

    def __init__(self) -> None:
        """Initialise with the Anti-Malware sectool name and action messages."""
        super().__init__(
            name=GET_CP2_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    GetCP2Exceptions().run()


if __name__ == "__main__":
    main()
