"""Delete Avanan DLP Exceptions action – bulk-removes Avanan DLP sectool exceptions."""
from ..core.delete_sectool_excs import DeleteSectoolExceptions
from ..core.constants import AVANAN_DLP_SAAS_NAME, DELETE_AVDLP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan DLP exception!"


class DeleteAVDLPExceptions(DeleteSectoolExceptions):
    """Delete multiple Avanan DLP (``avanan_dlp``) sectool exceptions in a single call.

    Accepts a comma-separated list of exception strings and delegates bulk
    deletion to :class:`~core.delete_sectool_excs.DeleteSectoolExceptions`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan DLP sectool name and action messages."""
        super().__init__(
            name=DELETE_AVDLP_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    DeleteAVDLPExceptions().run()


if __name__ == "__main__":
    main()
