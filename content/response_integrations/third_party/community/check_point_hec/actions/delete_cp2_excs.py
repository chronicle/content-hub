from ..core.delete_sectool_excs import DeleteSectoolExceptions
from ..core.constants import ANTI_MALWARE_SAAS_NAME, DELETE_CP2_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anti-Malware exceptions!"
ERROR_MESSAGE: str = "Failed deleting Anti-Malware exceptions!"


class DeleteCP2Exceptions(DeleteSectoolExceptions):

    def __init__(self) -> None:
        super().__init__(
            name=DELETE_CP2_EXCS_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )


def main() -> None:
    DeleteCP2Exceptions().run()


if __name__ == "__main__":
    main()
