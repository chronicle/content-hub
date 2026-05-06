"""Get Avanan DLP Exceptions action – retrieves a filtered list of Avanan DLP exceptions."""
from ..core.get_sectool_excs import GetSectoolExceptions
from ..core.constants import AVANAN_DLP_SAAS_NAME, GET_AVDLP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Avanan DLP exceptions!"
ERROR_MESSAGE: str = "Failed getting Avanan DLP exceptions!"


class GetAVDLPExceptions(GetSectoolExceptions):
    """Retrieve a list of Avanan DLP (``avanan_dlp``) sectool exceptions.

    Supports optional filtering and pagination parameters inherited from
    :class:`~core.get_sectool_excs.GetSectoolExceptions`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan DLP sectool name and action messages."""
        super().__init__(
            name=GET_AVDLP_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    GetAVDLPExceptions().run()


if __name__ == "__main__":
    main()
