"""Create Anti-Malware Exception action – adds a Check Point Anti-Malware (CP2) exception."""
from ..core.create_sectool_exc import CreateSectoolException
from ..core.constants import ANTI_MALWARE_SAAS_NAME, CREATE_CP2_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully created Anti-Malware exception!"
ERROR_MESSAGE: str = "Failed creating Anti-Malware exception!"


class CreateCP2Exception(CreateSectoolException):
    """Create a new exception for the Check Point Anti-Malware (``checkpoint2``) sectool.

    Extends :class:`~core.create_sectool_exc.CreateSectoolException` with extra
    validation for the ``allow_file_type`` exception type: the supplied file
    extension must belong to a fixed allow-list, and the *exception payload
    condition* defaults to ``with_or_without_link`` when not explicitly set.
    """

    def __init__(self) -> None:
        """Initialise with the Anti-Malware sectool name and action messages."""
        super().__init__(
            name=CREATE_CP2_EXC_SCRIPT_NAME,
            output_message=SUCCESS_MESSAGE,
            error_output=ERROR_MESSAGE,
            sectool_name=ANTI_MALWARE_SAAS_NAME
        )

    def _extract_action_parameters(self):
        """Extract parameters and apply file-type validation for ``allow_file_type`` exceptions."""
        super()._extract_action_parameters()
        valid_file_types = ['.aac', '.aif', '.au','.avi','.avif', '.bcpio','.bin','.bmp',
                            '.cdf','cpio','.csh', '.css','.csv','.doc', '.dvi','.eml',
                            '.etx', '.gif','.hdf','.heif', '.html','.ico','.ief', '.jpg','.js',]

        if self.params.exception_type == 'allow_file_type':
            if self.params.exception_string not in valid_file_types:
                raise ValueError(f"Incorrect file type, pick one of {valid_file_types}")
            elif not self.params.exception_payload_condition:
                self.params.exception_payload_condition = "with_or_without_link"

def main() -> None:
    CreateCP2Exception().run()


if __name__ == "__main__":
    main()
