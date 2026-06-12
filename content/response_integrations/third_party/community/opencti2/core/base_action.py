from abc import ABC

from core.opencti_client.client import OpenCTIClient
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param


class BaseAction(Action, ABC):
    """Base action class."""

    INTEGRATION_IDENTIFIER: str = "OpenCTI2"

    def __init__(self, script_name: str) -> None:
        script_name = self.build_script_name(script_name)

        super().__init__(script_name)

        self.output_message = f"Action '{script_name}' successfully executed"
        self.error_output_message = f"Error executing action '{script_name}'"

    @classmethod
    def build_script_name(cls, action_name: str) -> str:
        """Build a platform-compatible script name for an action."""
        return f"{cls.INTEGRATION_IDENTIFIER} - {action_name}"

    def _init_api_clients(self) -> OpenCTIClient:
        """Initialize and return the OpenCTI API client."""
        octi_url: str = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="URL",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )  # type: ignore[assignment]
        octi_token: str = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="API Token",
            input_type=str,
            is_mandatory=True,
            print_value=False,
        )  # type: ignore[assignment]
        verify_ssl: bool = extract_configuration_param(
            self.soar_action,
            provider_name=self.INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            input_type=bool,  # type: ignore[arg-type]
            is_mandatory=False,
            default_value=True,
            print_value=True,
        )

        return OpenCTIClient(
            base_url=octi_url,
            api_token=octi_token,
            ssl_verify=verify_ssl,
        )

    @property
    def api_client(self) -> OpenCTIClient:
        """Override api_client typing."""
        return super().api_client  # type: ignore[return-value]
