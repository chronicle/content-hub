"""Update Avanan URL Exception action – modifies an existing Avanan URL sectool exception."""
from ..core.update_sectool_exc import UpdateSectoolException
from ..core.constants import AVANAN_URL_SAAS_NAME, UPDATE_AVURL_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully updated Avanan URL exception!"
ERROR_MESSAGE: str = "Failed updating Avanan URL exception!"


class UpdateAVURLException(UpdateSectoolException):
    """Update an existing Avanan URL (``avanan_url``) sectool exception.

    Delegates parameter extraction and the API call to
    :class:`~core.update_sectool_exc.UpdateSectoolException`.
    """

    def __init__(self) -> None:
        """Initialise with the Avanan URL sectool name and action messages."""
        super().__init__(
            name=UPDATE_AVURL_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=AVANAN_URL_SAAS_NAME
        )


def main() -> None:
    UpdateAVURLException().run()


if __name__ == "__main__":
    main()
