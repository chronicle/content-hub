from ..core.delete_sectool_excs import DeleteSectoolExceptions
from ..core.constants import AVANAN_DLP_SAAS_NAME, DELETE_AVDLP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan DLP exception!"


class DeleteAVDLPExceptions(DeleteSectoolExceptions):

    def __init__(self) -> None:
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
