from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from sentinel_one_v2.core.constants import (
    DELETE_DEVICE_CONTROL_RULE_SCRIPT_NAME,
    INTEGRATION_NAME,
    SCOPE_TYPE_DDL_VALUES,
    SCOPE_TYPE_MAPPER,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2


class DeleteDeviceControlRule(Action):

    def __init__(self) -> None:
        super().__init__(DELETE_DEVICE_CONTROL_RULE_SCRIPT_NAME)

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
        self.params.rule_id = extract_action_param(
            self.soar_action,
            param_name="Rule ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.scope_type = extract_action_param(
            self.soar_action,
            param_name="Scope Type",
            print_value=True,
        )
        self.params.scope_id = extract_action_param(
            self.soar_action,
            param_name="Scope ID",
            is_mandatory=True,
            print_value=True,
        )


    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Scope Type",
            value=self.params.scope_type,
            ddl_values=SCOPE_TYPE_DDL_VALUES,
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
        rule_details: SingleJson = self.api_client.get_device_control_rule_name(
            rule_id=self.params.rule_id,
            scope_type=SCOPE_TYPE_MAPPER.get(self.params.scope_type),
            scope_id=self.params.scope_id,
        )
        if not rule_details:
            self.output_message: str = (
                f"Rule with ID {self.params.rule_id} wasn't found in SentinelOne."
            )
            return

        rule_name: str = rule_details[0]["ruleName"]
        self.api_client.delete_device_control_rule(
            rule_id=self.params.rule_id,
            rule_name=rule_name,
        )
        self.output_message: str = (
            f"Successfully deleted a Device Control Rule with ID {self.params.rule_id} "
            "in SentinelOne."
        )


def main() -> NoReturn:
    DeleteDeviceControlRule().run()


if __name__ == "__main__":
    main()
