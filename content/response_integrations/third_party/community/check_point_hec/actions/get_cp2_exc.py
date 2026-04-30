from ..core.get_sectool_exc import GetSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, GET_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed getting Anti-Malware exception!"


class GetCP2Exception(GetSectoolException):

    def __init__(self) -> None:
        super().__init__(
            name=GET_CP2_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    GetCP2Exception().run()


if __name__ == "__main__":
    main()
