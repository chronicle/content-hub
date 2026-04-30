from ..core.get_sectool_excs import GetSectoolExceptions
from ..core.constants import AVANAN_URL_SAAS_NAME, GET_AVURL_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Avanan URL exceptions!"
ERROR_MESSAGE: str = "Failed getting Avanan URL exceptions!"


class GetAVURLExceptions(GetSectoolExceptions):

    def __init__(self) -> None:
        super().__init__(
            name=GET_AVURL_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    GetAVURLExceptions().run()


if __name__ == "__main__":
    main()
