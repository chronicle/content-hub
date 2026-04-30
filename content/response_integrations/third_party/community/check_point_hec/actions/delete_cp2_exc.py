from ..core.delete_sectool_exc import DeleteSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, DELETE_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed deleting Anti-Malware exception!"


class DeleteCP2Exception(DeleteSectoolException):

    def __init__(self) -> None:
        super().__init__(
            name=DELETE_CP2_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    DeleteCP2Exception().run()


if __name__ == "__main__":
    main()
