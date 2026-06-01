"""Update Avanan DLP Exception action – modifies an existing Avanan DLP sectool exception."""
from ..core.update_sectool_exc import UpdateSectoolException
from ..core.constants import AVANAN_DLP_SAAS_NAME, UPDATE_AVDLP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Avanan DLP exception!"
ERROR_MESSAGE: str = "Failed updating Avanan DLP exception!"


class UpdateAVDLPException(UpdateSectoolException):
    """Update an existing Avanan DLP (``avanan_dlp``) sectool exception.

    Delegates parameter extraction and the API call to
    :class:`~core.update_sectool_exc.UpdateSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan DLP sectool name and action messages."""
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
