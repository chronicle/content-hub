from __future__ import annotations
from typing import TYPE_CHECKING
import re
from sentinel_one_v2.core.datamodelsV2 import Alert

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory
from sentinel_one_v2.core.constants import (
    ANALYST_VERDICT_MAPPING,
    INCIDENT_STATUS_MAPPING,
    INTEGRATION_NAME,
    PRODUCT_NAME,
    SELECT_ONE,
    UPDATE_ALERT_SCRIPT_NAME,
)
from sentinel_one_v2.core.exceptions import SentinelOneV2ValidationError

if TYPE_CHECKING:
    from typing import NoReturn
    from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2


class UpdateAlert(Action):
    """
    Update an alert's status or verdict in SentinelOne.
    """

    def __init__(self) -> None:
        super().__init__(UPDATE_ALERT_SCRIPT_NAME)

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

        self.params.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.incident_status = extract_action_param(
            self.soar_action,
            param_name="Status",
            is_mandatory=False,
            print_value=True,
            default_value=SELECT_ONE,
        )
        self.params.analyst_verdict = extract_action_param(
            self.soar_action,
            param_name="Verdict",
            is_mandatory=False,
            print_value=True,
            default_value=SELECT_ONE,
        )

    def _validate_params(self) -> None:
        if (
            self.params.incident_status == SELECT_ONE
            and self.params.analyst_verdict == SELECT_ONE
        ):
            raise SentinelOneV2ValidationError(
                "At least one of the “Status” or “Verdict” parameters "
                "should have a value."
            )

        validator = ParameterValidator(self.soar_action)
        if self.params.incident_status != SELECT_ONE:
            validator.validate_ddl(
                param_name="Status",
                value=self.params.incident_status,
                ddl_values=list(INCIDENT_STATUS_MAPPING.keys()),
            )

        if self.params.analyst_verdict != SELECT_ONE:
            validator.validate_ddl(
                param_name="Verdict",
                value=self.params.analyst_verdict,
                ddl_values=list(ANALYST_VERDICT_MAPPING.keys()),
            )
        if not re.match(r"^\d+$", self.params.alert_id):
            raise SentinelOneV2ValidationError(
                'parameter "Alert ID" is not Valid'
            )

    def _init_api_clients(self) -> SentinelOneV2ManagerV2:
        return SentinelOneV2ManagerFactory().get_manager(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
        )

    def _perform_action(self, _) -> None:
        self.logger.info(f"Started processing alert: {self.params.alert_id}")
        alert: Alert = self.api_client.get_cloud_detection_alert_or_raise(
            self.params.alert_id
        )

        status_updated: bool = False
        verdict_updated: bool = False

        if self.params.incident_status != SELECT_ONE:
            status_updated = self._update_status(alert)

        if self.params.analyst_verdict != SELECT_ONE:
            verdict_updated = self._update_verdict(alert)

        if status_updated or verdict_updated:
            self.logger.info("Fetching updated alert details.")
            updated_alert: Alert = (
                self.api_client.get_cloud_detection_alert_or_raise(
                    self.params.alert_id
                )
            )
            self.json_results = updated_alert.to_json()
            self.output_message = (
                f"Successfully updated alert {self.params.alert_id} in "
                f"{PRODUCT_NAME}."
            )
            self.result_value = True
        else:
            self.result_value = False

    def _update_status(self, alert: Alert) -> bool:
        if alert.incident_status.lower() != self.params.incident_status.lower():
            self.logger.info(
                f"Updating incident status for alert {self.params.alert_id} to "
                f"{self.params.incident_status}"
            )
            mapped_status: str = INCIDENT_STATUS_MAPPING[self.params.incident_status]
            self.api_client.update_cloud_detection_alert_incident_status(
                alert_ids=[self.params.alert_id], status=mapped_status
            )
            return True

        self.logger.info(
            f"Incident status for alert {self.params.alert_id} is already set "
            f"to '{self.params.incident_status}'."
        )
        return False

    def _update_verdict(self, alert: Alert) -> bool:
        if alert.verdict.lower() != self.params.analyst_verdict.lower():
            self.logger.info(
                f"Updating analyst verdict for alert {self.params.alert_id} to "
                f"{self.params.analyst_verdict}"
            )
            mapped_verdict = ANALYST_VERDICT_MAPPING[self.params.analyst_verdict]
            self.api_client.update_cloud_detection_alert_verdict(
                alert_ids=[self.params.alert_id], analyst_verdict=mapped_verdict
            )
            return True

        self.logger.info(
            f"Analyst verdict for alert {self.params.alert_id} is already set "
            f"to '{self.params.analyst_verdict}'."
        )
        return False


def main() -> NoReturn:
    UpdateAlert().run()


if __name__ == "__main__":
    main()
