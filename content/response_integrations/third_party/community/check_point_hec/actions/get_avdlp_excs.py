from ..core.get_sectool_excs import GetSectoolExceptions
from ..core.constants import AVANAN_DLP_SAAS_NAME, GET_AVDLP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Avanan DLP exceptions!"
ERROR_MESSAGE: str = "Failed getting Avanan DLP exceptions!"


class GetAVDLPExceptions(GetSectoolExceptions):

    def __init__(self) -> None:
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
