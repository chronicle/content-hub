from ..core.update_sectool_exc import UpdateSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, UPDATE_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed updating Avanan DLP exception!"


class UpdateAVDLPException(UpdateSectoolException):

    def __init__(self) -> None:
        super().__init__(
            name=UPDATE_AVDLP_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    UpdateAVDLPException().run()


if __name__ == "__main__":
    main()
