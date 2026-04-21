from ..core.create_sectool_exc import CreateSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, CREATE_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed creating Avanan DLP exception!"


class CreateAVDLPException(CreateSectoolException):

    def __init__(self) -> None:
        super().__init__(
            name=CREATE_AVDLP_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_DLP_SAAS_NAME
        )


def main() -> None:
    CreateAVDLPException().run()


if __name__ == "__main__":
    main()
