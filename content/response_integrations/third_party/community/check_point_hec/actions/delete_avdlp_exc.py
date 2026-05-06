"""Delete Avanan DLP Exception action – removes a single Avanan DLP sectool exception."""
from ..core.delete_sectool_exc import DeleteSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, DELETE_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan DLP exception!"


class DeleteAVDLPException(DeleteSectoolException):
    """Delete a single Avanan DLP (``avanan_dlp``) sectool exception by type and string.

    Delegates parameter extraction and the API call to
    :class:`~core.delete_sectool_exc.DeleteSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan DLP sectool name and action messages."""
        super().__init__(
            name=DELETE_AVDLP_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    DeleteAVDLPException().run()


if __name__ == "__main__":
    main()
