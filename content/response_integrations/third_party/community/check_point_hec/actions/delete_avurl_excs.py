"""Delete Avanan URL Exceptions action – bulk-removes Avanan URL sectool exceptions."""
from ..core.delete_sectool_excs import DeleteSectoolExceptions
from ..core.constants import AVANAN_URL_SAAS_NAME, DELETE_AVURL_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan URL exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan URL exception!"


class DeleteAVURLExceptions(DeleteSectoolExceptions):
    """Delete multiple Avanan URL (``avanan_url``) sectool exceptions in one call.

    Accepts a comma-separated list of exception strings and delegates bulk
    deletion to :class:`~core.delete_sectool_excs.DeleteSectoolExceptions`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=DELETE_AVURL_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    DeleteAVURLExceptions().run()


if __name__ == "__main__":
    main()
