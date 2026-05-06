"""Get Avanan URL Exception action – retrieves a single Avanan URL sectool exception."""
from ..core.get_sectool_exc import GetSectoolException
from ..core.constants import AVANAN_URL_SAAS_NAME, GET_AVURL_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Avanan URL exception!"
ERROR_MESSAGE: str = "Failed getting Avanan URL exception!"


class GetAVURLException(GetSectoolException):
    """Retrieve a single Avanan URL (``avanan_url``) sectool exception by type and string.

    Delegates parameter extraction and the API call to
    :class:`~core.get_sectool_exc.GetSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=GET_AVURL_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    GetAVURLException().run()


if __name__ == "__main__":
    main()
