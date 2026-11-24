from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from sentinel_one_v2.core.constants import (
    CREATE_DEVICE_CONTROL_RULE_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2


class CreateDeviceControlRule(Action):

    def __init__(self) -> None:
        super().__init__(CREATE_DEVICE_CONTROL_RULE_SCRIPT_NAME)
        self.output_message: str = (
            "Successfully created a Device Control Rule in SentinelOne."
        )

    def _extract_action_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Api Root",
            is_mandatory=True,
        )
        self.params.api_token = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Token",
            is_mandatory=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=False,
            input_type=bool,
        )

        self.params.rule_json = extract_action_param(
            self.soar_action,
            param_name="Rule JSON",
            is_mandatory=True,
            print_value=True,
        )
        self.params.scope_json = extract_action_param(
            self.soar_action,
            param_name="Scope JSON",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.rule_json = validator.validate_json(
            param_name="Rule JSON",
            json_string=self.params.rule_json,
        )
        self.params.scope_json = validator.validate_json(
            param_name="Scope JSON",
            json_string=self.params.scope_json,
        )

    def _init_api_clients(self) -> SentinelOneV2ManagerV2:
        return SentinelOneV2ManagerFactory().get_manager(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
            logger=self.logger,
        )

    def _perform_action(self, _) -> None:
        rule_details: SingleJson = self.api_client.create_device_control_rule(
            rule_json=self.params.rule_json,
            scope_json=self.params.scope_json,
        )
        self.json_results: SingleJson = rule_details


def main() -> NoReturn:
    CreateDeviceControlRule().run()


if __name__ == "__main__":
    main()
