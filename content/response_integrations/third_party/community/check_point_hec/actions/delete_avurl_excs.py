from ..core.delete_sectool_excs import DeleteSectoolExceptions
from ..core.constants import AVANAN_URL_SAAS_NAME, DELETE_AVURL_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan URL exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan URL exception!"


class DeleteAVURLExceptions(DeleteSectoolExceptions):

    def __init__(self) -> None:
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
