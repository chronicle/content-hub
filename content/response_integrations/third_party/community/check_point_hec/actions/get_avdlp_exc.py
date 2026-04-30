from ..core.get_sectool_exc import GetSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, GET_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed deleting Avanan DLP exception!"


class GetAVDLPException(GetSectoolException):

    def __init__(self) -> None:
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
