from __future__ import annotations

import functools
import urllib.parse

from requests import HTTPError
from scc_enterprise.core import SCCEnterpriseDatamodels
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.base.connector import Connector
from TIPCommon.data_models import CaseDataStatus
from TIPCommon.data_models import CASE_DATA_STATUS_VAL_NAME_MAP
from TIPCommon.exceptions import (
    BadGatewayError,
    ConnectorSetupError,
    DeadlineExceededError,
    ResourceExhaustedError,
    UnavailableError,
)
from TIPCommon.rest.soar_api import get_case_overview_details
from TIPCommon.smp_io import read_ids, read_content, write_ids, write_content
from TIPCommon.utils import is_empty_string_or_none
from scc_enterprise.core import GoogleSecurityCommandCenterConstants as constants
from scc_enterprise.core import GoogleSecurityCommandCenterDatamodels as datamodels
from scc_enterprise.core.GoogleSecurityCommandCenterExceptions import GoogleSecurityCommandCenterException
from scc_enterprise.core.GoogleSecurityCommandCenterManager import GoogleSecurityCommandCenterManager
from scc_enterprise.core.SCCEnterpriseConsts import URGENT_POSTURE_CONNECTOR_NAME, FINDINGS_CONTEXT_KEY
from scc_enterprise.core.SCCEnterpriseUtils import soar_supports_scce_phase_2, load_findings_context


class UrgentPostureFindingConnector(Connector):
    def __init__(self) -> None:
        super().__init__(URGENT_POSTURE_CONNECTOR_NAME)
        if not soar_supports_scce_phase_2(self.siemplify):
            raise GoogleSecurityCommandCenterException(
                f"This Connector is not supported by SOAR SDK in current version. "
                f"Please Upgrade your SOAR platform to latest version to execute "
                f"this connector."
            )

        self.manager: GoogleSecurityCommandCenterManager | None = None
        self.subscription = None
        self.tc_findings_map = {}
        self.ack_ids = []
        self._case_context_mapping = {}

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.fallback_owner = self.param_validator.validate_email(
            "Fallback Owner", self.params.fallback_owner
        )

        if not is_empty_string_or_none(self.params.workload_identity_email):
            self.params.workload_identity_email = self.param_validator.validate_email(
                "Workload Identity Email", self.params.workload_identity_email
            )

        if not is_empty_string_or_none(self.params.user_service_account):
            self.param_validator.validate_json(
                "User Service Account", self.params.user_service_account
            )

    def init_managers(self) -> None:
        self.manager = GoogleSecurityCommandCenterManager(
            api_root=self.params.api_root,
            service_account_string=self.params.user_service_account,
            workload_identity_email=self.params.workload_identity_email,
            pubsub_project_id=self.params.pub_sub_project_id,
            quota_project_id=self.params.quota_project_id,
            organization_id=self.params.organization_id,
            location_id=self.params.location_id,
            verify_ssl=self.params.verify_ssl,
            chronicle_soar=self.siemplify,
        )
        if is_empty_string_or_none(self.params.user_service_account):
            try:
                self.manager.test_connectivity()
            except GoogleSecurityCommandCenterException as e:
                raise GoogleSecurityCommandCenterException(
                    'Error executing "Urgent Posture Findings Connector". '
                    "Reason: Authentication with Workload Identity to Google"
                    "Security Command Center server resulted in failure. "
                    f"Error: {e}."
                ) from e

        identifier = urllib.parse.quote_plus(
            self.siemplify.context.connector_info.identifier.split("_")[1]
        )
        notifications_config_name = (
            constants.CONNECTOR_NOTIFICATIONS_CONFIG_FORMAT.format(
                identifier=identifier
            )
        )
        toxic_notifications_config_name = (
            constants.CONNECTOR_TOXIC_NOTIFICATIONS_CONFIG_FORMAT.format(
                identifier=identifier
            )
        )
        topic_name = constants.CONNECTOR_TOPIC_NAME_FORMAT.format(identifier=identifier)
        subscription_name = constants.CONNECTOR_SUB_NAME_FORMAT.format(
            identifier=identifier
        )

        # Using the script timout threshold as the ack_deadline for each
        # message pulled by the pubsub subscription
        self.subscription = self.manager.get_pubsub_subscription(
            notifications_config_name=notifications_config_name,
            toxic_notifications_config_name=toxic_notifications_config_name,
            pubsub_topic_name=topic_name,
            subscription_name=subscription_name,
            toxic_query_filter=constants.TOXIC_COMBINATION_FILTER,
            ack_deadline=self.params.python_process_timeout,
        )

        try:
            self.context.tc_source_name = self.context.tc_source_name or next(
                (
                    source.name
                    for source in self.manager.list_sources()
                    if constants.TOXIC_COMBINATION_SOURCE_NAME in source.display_name
                ),
                None,
            )
        except GoogleSecurityCommandCenterException as e:
            self.logger.error(f"Connector wasn't able to list sources. Error: {str(e)}")

    def get_alerts(self) -> list[datamodels.PostureFindingAlert]:
        """Fetch new notifications from Pub/Sub topic."""
        posture_alerts = self.manager.get_posture_alerts(
            self.subscription, max_alerts_to_fetch=constants.MAX_ALERTS_TO_FETCH
        )
        tc_finding_ids = set()

        for posture_alert in posture_alerts:
            if not posture_alert.from_tc_config:
                continue

            if posture_alert.finding_class != constants.TOXIC_COMBINATION_CLASS:
                tc_finding_ids.update(posture_alert.tc_group_ids)
                continue

            if self.context.tc_source_name is None:
                self.context.tc_source_name = posture_alert.source_name

        self.fetch_tc_findings(tc_finding_ids)
        return posture_alerts

    def fetch_tc_findings(self, tc_finding_ids: set[str]) -> None:
        """Fetch TC findings and set them into Connector.tc_findings_map.

        Args:
            tc_finding_ids (str): List of tc finding IDs to fetch
        """
        if self.context.tc_source_name is None or not tc_finding_ids:
            return

        findings_names = [
            (
                f"{self.context.tc_source_name}/locations/{self.params.location_id}/"
                f"findings/{finding_id}"
            )
            for finding_id in tc_finding_ids
        ]
        for index in range(0, len(findings_names), constants.LIST_FINDINGS_BATCH):
            findings_batch_filter = " OR ".join(
                f'name="{finding_name}"'
                for finding_name in findings_names[
                    index : index + constants.LIST_FINDINGS_BATCH
                ]
            )
            self.tc_findings_map.update(
                {
                    finding.name.split("/")[-1]: finding
                    for finding in self.manager.list_findings_by_filter(
                        filter_string=findings_batch_filter,
                        limit=constants.LIST_FINDINGS_BATCH,
                    )
                }
            )

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.tc_source_name = (
            read_content(
                self.siemplify, constants.TC_SOURCE_CONTEXT, constants.TC_SOURCE_CONTEXT
            )
            or None
        )
        self.context.existing_ids = set(read_ids(self.siemplify))

    def write_context_data(self, alerts: list[datamodels.PostureFindingAlert]) -> None:
        self.logger.info("Saving existing ids.")
        write_content(
            self.siemplify,
            self.context.tc_source_name,
            constants.TC_SOURCE_CONTEXT,
            constants.TC_SOURCE_CONTEXT,
        )
        write_ids(
            self.siemplify,
            list(self.context.existing_ids),
            stored_ids_limit=constants.STORED_IDS_LIMIT,
        )

    def store_alert_in_cache(self, alert: datamodels.PostureFindingAlert):
        self.context.existing_ids.add(alert.display_id)
        self.ack_ids.append(alert.ack_id)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def max_alerts_processed(self, processed_alerts) -> bool:
        """Check if connector already reached max alerts to be processed."""
        return len(processed_alerts) >= constants.MAX_ALERTS_TO_PROCESS

    def create_alert_info(self, alert: datamodels.PostureFindingAlert) -> AlertInfo:
        """Create SOAR alert infro from Pub/Sub notification."""

        source_grouping_identifier_builder = datamodels.SourceGroupingIdentifierBuilder(
            group_by_project=self.params.group_by_gcp_project,
            group_by_aws_account=self.params.group_by_aws_account,
            group_by_azure_subscription=self.params.group_by_azure_subscription,
            group_by_severity=self.params.group_by_severity,
            group_by_asset_type=self.params.group_by_asset_type,
        )
        finding_owner_builder = datamodels.FindingOwnerBuilder(
            fallback_owner=self.params.fallback_owner,
            owner_tag_name=self.params.owner_tag_name,
        )

        return alert.get_posture_alert_info(
            logger=self.logger,
            alert_info=AlertInfo(),
            environment_common=self.env_common,
            device_product_field=self.params.device_product_field,
            fallback_severity="SEVERITY_UNSPECIFIED",
            source_grouping_identifier_builder=source_grouping_identifier_builder,
            finding_owner_builder=finding_owner_builder,
        )

    def _get_case_findings_context(
        self, case_id: str
    ) -> set[SCCEnterpriseDatamodels.FindingContext]:
        """Fetch finding's context for a given case."""
        if case_id not in self._case_context_mapping:
            findings_context_str = self.siemplify.get_context_property(
                context_type=1, identifier=case_id, property_key=FINDINGS_CONTEXT_KEY
            )
            _, self._case_context_mapping[case_id] = load_findings_context(
                findings_context_str
            )

        return self._case_context_mapping[case_id]

    def _set_alert_identifiers_to_case_context(self, case_id: str) -> None:
        """Update alert identifiers for a given case in case context."""
        current_findings_context = self._get_case_findings_context(case_id)
        try:
            soar_case = get_case_overview_details(
                chronicle_soar=self.siemplify, case_id=case_id
            )
        except HTTPError as e:
            self.logger.error(
              f"Error fetching case data for case {case_id}, error is: {e}"
            )
            return

        def _is_from_same_alert(fc, soar_alert_) -> bool:
            return fc.name_without_location.upper() in soar_alert_.identifier

        for soar_alert in soar_case.alerts:
            alert_fc = next(
                filter(
                    functools.partial(_is_from_same_alert, soar_alert_=soar_alert),
                    current_findings_context,
                ),
                None,
            )
            if alert_fc is None:
                continue

            alert_fc.alert_identifier = soar_alert.identifier

    def _get_current_alert_identifier(
        self, alert: datamodels.PostureFindingAlert
    ) -> str | None:
        """Get an alert identifier from Findings-Context of alert."""
        if alert.external_systems.case_id == constants.URGENT_POSTURE_DEFAULT_CASE_ID:
            return None

        current_findings_context = self._get_case_findings_context(
            case_id=alert.external_systems.case_id
        )
        current_alert_fc = next(
            filter(
                lambda fc: fc.name_without_location == alert.name_without_location,
                current_findings_context,
            ),
            None,
        )
        if not current_alert_fc:
            return None

        if current_alert_fc.alert_identifier is None:
            self._set_alert_identifiers_to_case_context(
                case_id=alert.external_systems.case_id
            )

        return current_alert_fc.alert_identifier

    def filter_alerts(
        self, alerts: list[datamodels.PostureFindingAlert]
    ) -> list[datamodels.PostureFindingAlert]:
        filtered_alerts = set()

        def _add_alert(_alert: datamodels.PostureFindingAlert):
            if _alert in filtered_alerts:
                existing_alert = next(filter(lambda a: a == _alert, filtered_alerts))
                self.ack_ids.append(existing_alert.ack_id)
                filtered_alerts.remove(existing_alert)

            filtered_alerts.add(_alert)

        for alert in alerts:
            # If finding is a related finding to a Toxic Combination
            if alert.is_toxic_related_finding:
                alert_related_tcs = [
                    self.tc_findings_map[tc_group_id]
                    for tc_group_id in alert.tc_group_ids
                    if tc_group_id in self.tc_findings_map
                ]
                # If TC findings can't be fetched OR all TCs are muted (inactive)
                if not alert_related_tcs or all(
                    tc.is_muted or not tc.is_active for tc in alert_related_tcs
                ):
                    self.logger.info(
                        f"The alert {alert.display_id} skipped because all "
                        f"underlying Toxic Combinations are muted or newly created."
                    )
                    self.ack_ids.append(alert.ack_id)
                    continue

            soar_case_id = alert.external_systems.case_id
            has_open_case = (
                soar_case_id != constants.URGENT_POSTURE_DEFAULT_CASE_ID
                and self.siemplify.platform_url in alert.external_systems.case_uri
                and (
                    alert.external_systems.status
                    != CASE_DATA_STATUS_VAL_NAME_MAP[CaseDataStatus.CLOSED]
                    or (
                        alert.last_update_time
                        - alert.external_systems.external_system_update_time
                        < 10 * constants.MINUTE_IN_MS
                    )
                )
            )

            if has_open_case:
                current_alert_identifier = self._get_current_alert_identifier(alert)
                if current_alert_identifier is None:
                    self.logger.error(
                        f"Failed to fetch current alert identifier for finding "
                        f"{alert.ticket_id} from case {soar_case_id}."
                    )
                    continue

                previous_case_id = (
                    constants.URGENT_POSTURE_DEFAULT_CASE_ID
                    if current_alert_identifier.endswith(
                        constants.URGENT_POSTURE_DEFAULT_CASE_ID.upper()
                    )
                    else current_alert_identifier.split("_")[-1]
                )
                alert.set_display_id(previous_case_id)
                self.logger.info(
                    f"Changing alert identifier to {alert.display_id} from case "
                    f"{soar_case_id} for update flow."
                )

            _add_alert(alert)

        return list(filtered_alerts)

    def build_external_systems_filter(self) -> datamodels.SCCCombinedFilter:
        """Build external systems filter for ingestion flow."""
        return datamodels.SCCCombinedFilter(
            filter_value=[
                datamodels.SCCFilter(
                    filter_name="externalSystems.chronicle_soar.externalUid",
                    filter_value=[""],
                    operator=":",
                    inverted=True,
                ),
                datamodels.SCCFilter(
                    filter_name="externalSystems.chronicle_soar.status",
                    filter_value=["Opened"],
                    inverted=True,
                ),
                datamodels.SCCFilter(
                    filter_name="externalSystems.chronicle_soar.caseUri",
                    filter_value=[self.siemplify.platform_url],
                    operator=":",
                    inverted=True,
                ),
                datamodels.SCCFilter(
                    filter_name="findingClass",
                    filter_value=constants.TOXIC_COMBINATION_CLASS,
                    inverted=True,
                ),
            ]
        )

    def finalize(self) -> None:
        if not self.is_test_run and self.manager is not None:
            self.logger.info(
                f"Acknowledging {len(self.ack_ids)} posture findings messages "
                f"from pubsub"
            )
            self.manager.ack_pubsub_findings(self.subscription.name, self.ack_ids)

    @output_handler
    def start(self) -> None:
        """
        Executes the connector logic.

        Execution steps:

            1. Extracting connector script parameters from the SDK connector object
            2. Validate parameters values
            3. Loading the connector context data via the SDK connector object
            4. Initializing the integrations manager(s)
            5. Fetching & parsing alerts from the product via integration manager
            6. Filtering the alerts
            7. Processing the filtered alerts into siemplify alerts
            8. Saving connector context data via the SDK connector object
            9. Sending newly created siemplify alerts to the platform

        Raises:
            ConnectorSetupError: if any of the pre-processing phases fail
        """
        self.logger.info(
            f"---------------- Starting connector {self.script_name} "
            "execution ----------------"
        )
        if self.is_test_run:
            self.logger.info(
                '****** This is an "IDE Play Button"\\"Run Connector once" '
                "test run ******"
            )

        self.logger.info("------------------- Main - Param Init -------------------")
        self.extract_params()
        self.logger.info("------------------- Main - Started -------------------")
        processed_alerts = []

        try:
            try:
                self.validate_params_wrapper()
                self.read_context_wrapper()
                self.logger.info("Initializing managers...")
                self.init_managers()
            except (
                BadGatewayError,
                DeadlineExceededError,
                ResourceExhaustedError,
                UnavailableError,
            ):
                raise
            except Exception as e:
                raise ConnectorSetupError(e) from e

            self.logger.info(
                "Fetching data from manager and starting case ingestion..."
            )
            fetched_alerts = self.get_alerts()
            self.logger.info(f"Fetched {len(fetched_alerts)} alerts from the manager")

            filtered_alerts = self.filter_alerts(fetched_alerts)
            self.logger.info(
                f"Successfully filtered alerts. "
                f"Filtered alerts count: {len(filtered_alerts)}"
            )

            self.logger.info("Starting to process alerts...")
            processed_alerts, all_alerts = self.process_alerts(filtered_alerts)
            if not self.is_test_run:
                self.write_context_wrapper(all_alerts)

        except (
            BadGatewayError,
            DeadlineExceededError,
            ResourceExhaustedError,
            UnavailableError,
        ) as e:
            self.logger.error(
                f"Pub/Sub or SCC services are temporarily unavailable, "
                f"received error: {e}. The connector will gracefully exit "
                f"and retry on next iteration."
            )

        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        try:
            self.finalize()
        except Exception as e:
            self.logger.error(f"{self.error_msg}")
            self.logger.error(f"Error: {e}")
            self.logger.exception(e)

            if self.is_test_run:
                raise

        self.logger.info("------------------- Main - Finished -------------------")
        self.logger.info(
            f"Sending {len(processed_alerts)} alerts back to SOAR platform. This "
            "package can contain both new alerts and updates to existing ones."
        )
        self.siemplify.return_package(processed_alerts)
        self.logger.info(
            f"---------------- Finished connector {self.script_name} "
            f"execution ----------------"
        )


if __name__ == "__main__":
    connector = UrgentPostureFindingConnector()
    connector.start()
