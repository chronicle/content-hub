from __future__ import annotations
import sys
from typing import List

from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.PhishrodManager import PhishrodManager
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import (
    extract_connector_param); from TIPCommon.smp_io import (
    read_ids,
    write_ids); from TIPCommon.filters import (
    filter_old_alerts,
    pass_whitelist_filter); from TIPCommon.smp_time import (
    is_approaching_timeout); from TIPCommon.utils import (
    is_overflowed)
from ..core.constants import (
    INCIDENTS_CONNECTOR_NAME,
    TIMEOUT_THRESHOLD,
    STORED_IDS_LIMIT,
    SEVERITIES,
)
from ..core.datamodels import Incident
from ..core.exceptions import PhishrodValidationException

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


@output_handler
def main(is_test_run: bool) -> None:
    all_incidents: List[Incident] = []
    processed_incidents: List[AlertInfo] = []
    existing_ids = []
    connector_starting_time = unix_now()
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = INCIDENTS_CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            "***** This is an 'IDE Play Button' 'Run Connector once' test run ******"
        )

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    device_product_field_name = extract_connector_param(
        siemplify, param_name="DeviceProductField", print_value=True, is_mandatory=True
    )
    environment_field_name = extract_connector_param(
        siemplify, param_name="Environment Field Name", print_value=True
    )
    environment_regex_pattern = extract_connector_param(
        siemplify, param_name="Environment Regex Pattern", print_value=True
    )
    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        print_value=True,
        is_mandatory=True,
    )
    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True, print_value=True
    )
    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )
    client_id = extract_connector_param(
        siemplify, param_name="Client ID", is_mandatory=True
    )
    username = extract_connector_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_connector_param(
        siemplify, param_name="Password", is_mandatory=True
    )
    alert_severity = extract_connector_param(
        siemplify, param_name="Alert Severity", is_mandatory=True, print_value=True
    )
    whitelist_as_a_blacklist = extract_connector_param(
        siemplify,
        param_name="Use dynamic list as a blacklist",
        default_value=False,
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")
    whitelist = (
        siemplify.whitelist
        if isinstance(siemplify.whitelist, list)
        else [siemplify.whitelist]
    )

    environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        siemplify, environment_field_name, environment_regex_pattern
    )

    try:
        alert_severity = SEVERITIES.get(alert_severity.upper())
        if alert_severity is None:
            raise PhishrodValidationException(
                f"Alert severity {alert_severity} is invalid. Valid values are:"
                f" Informational, Low, Medium, High, Critical"
            )

        # Read already existing alerts ids
        siemplify.LOGGER.info("Reading already existing alerts ids...")
        existing_ids = read_ids(siemplify)

        # Read new alert
        manager = PhishrodManager(
            api_root=api_root,
            api_key=api_key,
            client_id=client_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        incidents = manager.get_incidents()

        new_incidents = filter_old_alerts(
            siemplify, incidents, existing_ids, "incident_number"
        )

        siemplify.LOGGER.info(
            f"Number of alerts to process after filtering already processed ones: {len(new_incidents)} out of"
            f" {len(incidents)} received from the API"
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            new_incidents = new_incidents[:1]

        for incident in new_incidents:
            if is_approaching_timeout(
                connector_starting_time, python_process_timeout, TIMEOUT_THRESHOLD
            ):
                siemplify.LOGGER.info(
                    "Timeout is approaching. Connector will gracefully exit"
                )
                break

            if pass_whitelist_filter(
                siemplify=siemplify,
                whitelist_as_a_blacklist=whitelist_as_a_blacklist,
                model=incident,
                model_key="email_subject",
                whitelist=whitelist,
            ):
                try:
                    all_incidents.append(incident)
                    siemplify.LOGGER.info(
                        f"Started processing alert with id: {incident.incident_number}"
                    )

                    alert_info = incident.create_alert_info(
                        alert_severity, environment_common, device_product_field_name
                    )

                    if is_overflowed(siemplify, alert_info, is_test_run):
                        siemplify.LOGGER.info(
                            f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}"
                            f"-{alert_info.device_product} found as overflow alert. Skipping..."
                        )
                        # If is overflowed we should skip
                        continue

                    processed_incidents.append(alert_info)
                    siemplify.LOGGER.info(
                        f"Alert with id {incident.incident_number} was created."
                    )

                except Exception as processing_exception:
                    siemplify.LOGGER.error(
                        f"Failed to process alert with id {incident.incident_number}"
                    )
                    siemplify.LOGGER.exception(processing_exception)

                    if is_test_run:
                        raise

    except Exception as critical_error:
        siemplify.LOGGER.error(
            f"Got exception on main handler. Error: {critical_error}"
        )
        siemplify.LOGGER.exception(critical_error)

        if is_test_run:
            raise

    if not is_test_run and all_incidents:
        siemplify.LOGGER.info("Saving existing ids.")
        write_ids(
            siemplify,
            existing_ids + [detection.incident_number for detection in all_incidents],
            stored_ids_limit=STORED_IDS_LIMIT,
        )

    siemplify.LOGGER.info(
        f"Alerts processed: {len(processed_incidents)} out of {len(all_incidents)}"
    )
    siemplify.LOGGER.info(f"Created total of {len(processed_incidents)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_incidents)


if __name__ == "__main__":
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
