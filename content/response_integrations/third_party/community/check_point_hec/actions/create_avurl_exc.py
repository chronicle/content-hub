"""Create Avanan URL Exception action – adds an Avanan URL sectool exception."""
from ..core.create_sectool_exc import CreateSectoolException
from ..core.constants import AVANAN_URL_SAAS_NAME, CREATE_AVURL_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Avanan URL exception!"
ERROR_MESSAGE: str = "Failed creating Avanan URL exception!"


class CreateAVURLException(CreateSectoolException):
    """Create a new exception for the Avanan URL (``avanan_url``) sectool.

    Delegates all parameter extraction and API interaction to
    :class:`~core.create_sectool_exc.CreateSectoolException`, pre-configured
    with the URL sectool name.
    """

    def __init__(self) -> None:
        """Initialize with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=CREATE_AVURL_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    CreateAVURLException().run()


if __name__ == "__main__":
    main()
