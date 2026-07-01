"""Get Avanan DLP Exception action – retrieves a single Avanan DLP sectool exception."""
from ..core.get_sectool_exc import GetSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, GET_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan DLP exception!"


class GetAVDLPException(GetSectoolException):
    """Retrieve a single Avanan DLP (``avanan_dlp``) sectool exception by type and string.

    Delegates parameter extraction and the API call to
    :class:`~core.get_sectool_exc.GetSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan DLP sectool name and action messages."""
        super().__init__(
            name=GET_AVDLP_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    GetAVDLPException().run()


if __name__ == "__main__":
    main()
