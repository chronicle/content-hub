# Imports
from __future__ import annotations
import sys

import arrow

from ..core.AlienVaultManagerLoader import AlienVaultManagerLoader
from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import (
    dict_to_flat,
    read_ids_by_timestamp,
    write_ids_with_timestamp,
    siemplify_fetch_timestamp,
    siemplify_save_timestamp,
    NUM_OF_MILLI_IN_SEC,
    is_overflowed,
)

# Consts
DEFAULT_PRODUCT = DEFAULT_VENDOR = "AlienVault USM Anywhere"
ALARM_ID_FILE = "AlarmIDs.json"
ALARM_DB_KEY = "AlarmIDs"
ALERTS_LIMIT = 20
IDS_HOURS_LIMIT = 72
DAYS_BACKWARDS_LIMIT = 3
PADDING_PERIOD_DEFAULT = 0


class AlienVaultAnyConnector:
    def __init__(self, connector_scope, alienvault_manager, environment):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.alienvault_manager = alienvault_manager
        self.environment = environment

    @staticmethod
    def validate_timestamp(last_run_timestamp: float, offset: int) -> float:
        """
        Validate timestamp in range
        :param last_run_timestamp: {long} last run timestamp in milliseconds
        :param offset: {int} max days backward to fetch from
        :return: {long} if first run, return current time minus offset time, else return timestamp from file
        """
        # Check if first run
        last_run_datetime = arrow.get(last_run_timestamp / NUM_OF_MILLI_IN_SEC)
        if last_run_datetime.shift(days=offset) < arrow.utcnow():
            return arrow.utcnow().shift(days=-offset).int_timestamp * NUM_OF_MILLI_IN_SEC
        else:
            return last_run_timestamp

    def validate_timestamp_to_save(self, all_cases):
        """
        Validate timestamp to save. Timestamps from the future will be ignored.
        :param: {[CaseInfo()]} - All processed cases
        :return: {int} Latest valid timestamp for the connector to save. None if no valid timestamp were found.
        """
        # Check that alerts does not contain future timestamp
        for case in sorted(all_cases, key=lambda case: case.end_time, reverse=True):
            if case.end_time > unix_now():
                self.logger.info(
                    f"Alert {case.ticket_id} - found to be with future timestamp - "
                    f"{case.end_time} - Skipping.."
                )
                continue
            return case.end_time

    def build_alarm_case_info(self, alarm):
        """
        Build a CaseInfo from alarm
        :param alarm: {AlienVaultAlarmModel} AlienVault alarm after parsing
        :return: {CaseInfo} The new case
        """

        self.logger.info(f"Building CaseInfo for alarm {alarm.uuid}")

        case_info = CaseInfo()
        case_info.name = alarm.name
        case_info.ticket_id = alarm.uuid
        case_info.rule_generator = case_info.name
        case_info.display_id = case_info.ticket_id
        case_info.device_vendor = DEFAULT_VENDOR
        case_info.device_product = DEFAULT_PRODUCT
        case_info.priority = alarm.priority
        case_info.start_time = alarm.timestamp
        case_info.end_time = alarm.timestamp
        case_info.environment = self.environment

        # Set events
        case_info.events = []
        case_info.extensions["original_priority"] = alarm.original_priority
        case_info.extensions["Is Suppressed"] = alarm.is_suppressed

        for event in alarm.events:
            # TODO: Consult with product/Itay whether we need to extract the actual data or leave it this way
            #  almost all the fields are prefixed with message_
            #  events are a dict with "message" key and the event actual data is inside the message key.
            try:
                case_info.events.append(dict_to_flat(event))
            except Exception as e:
                self.logger.error(
                    f"Unable to process event {event.get('uuid')} of alarm {alarm}: {e}"
                )

        self.logger.info(f"Found {len(case_info.events)} events")

        return case_info


def main(is_test_run=False):
    """
    Main execution
    """
    siemplify = SiemplifyConnectorExecution()
    all_cases = []
    cases = []

    try:
        # Parameters.
        siemplify.LOGGER.info(
            "==================== Main - Param Init ===================="
        )
        (
            version,
            api_root,
            username,
            password,
            verify_ssl,
            max_alert_per_cycle,
            offset,
            padding_period,
            suppressed,
            use_suppressed_filter,
            priorities,
            intent,
            strategy,
            method,
        ) = init_params(siemplify)

        if is_test_run:
            siemplify.LOGGER.info(
                '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
            )
        else:
            siemplify.LOGGER.info(
                "========== Starting AlienVault USM Anywhere Connector =========="
            )

        siemplify.LOGGER.info(f"Connecting to {api_root}")

        alienvault_manager = AlienVaultManagerLoader.load_manager(
            version=version,
            api_root=api_root,
            username=username,
            password=password,
            use_ssl=verify_ssl,
            chronicle_soar=siemplify,
        )
        siemplify.LOGGER.info("Successfully connected to AlienVault Anywhere.")

        av_connector = AlienVaultAnyConnector(
            siemplify, alienvault_manager, siemplify.context.connector_info.environment
        )

        last_success_datetime: float = siemplify_fetch_timestamp(siemplify)
        last_time: float = av_connector.validate_timestamp(
            last_success_datetime, offset
        )

        padding_time: float = (
            arrow.utcnow().shift(hours=-padding_period).int_timestamp * NUM_OF_MILLI_IN_SEC
        )
        if padding_period and last_time > padding_time:
            last_time = padding_time
            siemplify.LOGGER.info(
                f"Last success time is greater than alerts padding period. Unix: {last_time} will be"
                f" used as last success time"
            )

        # fetch last fetched incident index
        existing_ids = read_ids_by_timestamp(
            siemplify,
            convert_to_milliseconds=True,
            offset_in_hours=max(offset * 2 * 24, IDS_HOURS_LIMIT),
            ids_file_name=ALARM_ID_FILE,
            db_key=ALARM_DB_KEY,
        )
        siemplify.LOGGER.info(f"Fetching alarms from {last_time}")

        # Getting alarms
        alarms = alienvault_manager.get_alarms(
            from_time=last_time,
            limit=max_alert_per_cycle,
            alarms_json_ids=existing_ids.keys(),
            show_suppressed=suppressed,
            intent=intent,
            strategy=strategy,
            priorities=priorities,
            method=method,
            use_suppressed_filter=use_suppressed_filter,
        )
        siemplify.LOGGER.info(f"Successfully fetched {len(alarms)} alarms.")

        # Test on one alarm only
        if is_test_run:
            alarms = alarms[:1]

        for alarm in alarms:
            try:
                siemplify.LOGGER.info(
                    f"Processing alarm {alarm.uuid}: {alarm.name}, "
                    f"timestamp_occured: {alarm.timestamp}"
                )

                # Build the case
                case = av_connector.build_alarm_case_info(alarm)
                all_cases.append(case)
                existing_ids.update({alarm.uuid: unix_now()})

                if is_overflowed(siemplify, case, is_test_run):
                    siemplify.LOGGER.warn(
                        f"{case.name}-{case.ticket_id}-"
                        f"{case.environment}-{case.device_product} "
                        f"found as overflow alert, skipping this alert."
                    )
                    # If is overflowed we should skip
                    continue

                cases.append(case)
                siemplify.LOGGER.info(f"Case {alarm.uuid} was created.")

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Error processing alarm {alarm.uuid}: {e}"
                )
                siemplify.LOGGER.exception(e)
                if is_test_run:
                    raise

        new_timestamp = last_time

        # Set the new timestamp
        if all_cases:
            new_valid_timestamp = av_connector.validate_timestamp_to_save(all_cases)
            if new_valid_timestamp:
                new_timestamp = new_valid_timestamp

        siemplify.LOGGER.info(f"Completed. Found {len(cases)} cases.")

        if not is_test_run:
            # update last execution time
            siemplify.LOGGER.info(f"Saving timestamp of {new_timestamp}")
            siemplify_save_timestamp(siemplify, new_timestamp=new_timestamp)
            # Write ids to file
            write_ids_with_timestamp(
                siemplify,
                existing_ids,
                ids_file_name=ALARM_ID_FILE,
                db_key=ALARM_DB_KEY,
            )

        alienvault_manager.session.close()

        # Return data
        siemplify.return_package(cases)

    except Exception as e:
        siemplify.LOGGER.error(str(e))
        siemplify.LOGGER.exception(e)
        if is_test_run:
            raise


def init_params(siemplify):
    """
    initialize params
    :param siemplify: {SiemplifyConnectorExecution}
    :return: params
    """
    # TODO: change this parameter to List type - check connector type (currently not develop on Server side)
    version = siemplify.parameters.get("Product Version")
    api_root = siemplify.parameters.get("Api Root")
    username = siemplify.parameters.get("ClientID")
    password = siemplify.parameters.get("Secret")
    verify_ssl = str(siemplify.parameters.get("Verify SSL", "False")).lower() == "true"
    max_alert_per_cycle = (
        int(siemplify.parameters.get("Max Alerts Per Cycle"))
        if siemplify.parameters.get("Max Alerts Per Cycle")
        else ALERTS_LIMIT
    )
    offset = (
        int(siemplify.parameters.get("Max Days Backwards"))
        if siemplify.parameters.get("Max Days Backwards")
        else DAYS_BACKWARDS_LIMIT
    )
    padding_period = (
        int(siemplify.parameters.get("Padding Period"))
        if siemplify.parameters.get("Padding Period")
        else PADDING_PERIOD_DEFAULT
    )

    suppressed = (
        str(siemplify.parameters.get("Show Suppressed", "False")).lower() == "true"
    )
    use_suppressed_filter = (
        str(siemplify.parameters.get("Use Suppressed Filter", "False")).lower()
        == "true"
    )
    priorities = (
        siemplify.parameters.get("Priority").split(",")
        if siemplify.parameters.get("Priority")
        else []
    )
    intent = siemplify.parameters.get("Rule Intent")
    strategy = siemplify.parameters.get("Rule Strategy")
    method = siemplify.parameters.get("Rule Method")

    return (
        version,
        api_root,
        username,
        password,
        verify_ssl,
        max_alert_per_cycle,
        offset,
        padding_period,
        suppressed,
        use_suppressed_filter,
        priorities,
        intent,
        strategy,
        method,
    )


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
