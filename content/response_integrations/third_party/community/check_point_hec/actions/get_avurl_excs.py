"""Get Avanan URL Exceptions action – retrieves a filtered list of Avanan URL exceptions."""
from ..core.get_sectool_excs import GetSectoolExceptions
from ..core.constants import AVANAN_URL_SAAS_NAME, GET_AVURL_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Avanan URL exceptions!"
ERROR_MESSAGE: str = "Failed getting Avanan URL exceptions!"


class GetAVURLExceptions(GetSectoolExceptions):
    """Retrieve a list of Avanan URL (``avanan_url``) sectool exceptions.

    Supports optional filtering and pagination parameters inherited from
    :class:`~core.get_sectool_excs.GetSectoolExceptions`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=GET_AVURL_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    GetAVURLExceptions().run()


if __name__ == "__main__":
    main()
