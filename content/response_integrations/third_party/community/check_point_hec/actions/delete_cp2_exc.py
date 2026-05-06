"""Delete Anti-Malware Exception action – removes a single CP2 sectool exception."""
from ..core.delete_sectool_exc import DeleteSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, DELETE_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed deleting Anti-Malware exception!"


class DeleteCP2Exception(DeleteSectoolException):
    """Delete a single Check Point Anti-Malware (``checkpoint2``) sectool exception.

    Delegates parameter extraction and the API call to
    :class:`~core.delete_sectool_exc.DeleteSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Anti-Malware sectool name and action messages."""
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
