"""Delete Avanan URL Exception action – removes a single Avanan URL sectool exception."""
from ..core.delete_sectool_exc import DeleteSectoolException
from ..core.constants import AVANAN_URL_SAAS_NAME, DELETE_AVURL_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan URL exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan URL exception!"


class DeleteAVURLException(DeleteSectoolException):
    """Delete a single Avanan URL (``avanan_url``) sectool exception by type and string.

    Delegates parameter extraction and the API call to
    :class:`~core.delete_sectool_exc.DeleteSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=DELETE_AVURL_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    DeleteAVURLException().run()


if __name__ == "__main__":
    main()
