from ..core.update_sectool_exc import UpdateSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, UPDATE_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed updating Anti-Malware exception!"


class UpdateCP2Exception(UpdateSectoolException):

    def __init__(self) -> None:
        super().__init__(
            name=UPDATE_CP2_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    UpdateCP2Exception().run()


if __name__ == "__main__":
    main()
