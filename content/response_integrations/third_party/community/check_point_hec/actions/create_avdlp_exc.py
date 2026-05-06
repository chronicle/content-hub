"""Create Avanan DLP Exception action – adds an Avanan DLP sectool exception."""
from ..core.create_sectool_exc import CreateSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, CREATE_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed creating Avanan DLP exception!"


class CreateAVDLPException(CreateSectoolException):
    """Create a new exception for the Avanan DLP (``avanan_dlp``) sectool.

    Delegates all parameter extraction and API interaction to
    :class:`~core.create_sectool_exc.CreateSectoolException`, pre-configured
    with the DLP sectool name.
    """

    def __init__(self) -> None:
        """Initialize with the Avanan DLP sectool name and action messages."""
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
