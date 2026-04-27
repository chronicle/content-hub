from __future__ import annotations

import sys
from datetime import datetime

import arrow

from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import (
    convert_string_to_datetime,
    convert_datetime_to_unix_time,
    output_handler,
)

from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_io import write_ids
from TIPCommon.smp_time import (
    siemplify_fetch_timestamp,
    siemplify_save_timestamp,
    validate_timestamp,
)
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_overflowed

from ..core.constants import (
    CONNECTOR_NAME,
    PRODUCT_NAME,
    VENDOR,
    DEFAULT_DAYS_BACKWARDS,
    MAX_INCIDENTS_PER_CYCLE,
    CASE_RULE_GENERATOR,
    NO_RESULTS,
    SN_DEFAULT_DOMAIN,
    DEFAULT_EVENT_NAME,
    LINK_KEY,
    PRIORITY_MAPPING,
    LOW_PRIORITY,
    EXCLUDE_INCIDENT_FIELDS,
    FIELD_SYS_UPDATED_ON,
    PARAM_UPDATED_TIME
)
from ..core.datamodels import Incident
from ..core.exceptions import (
    AssignmentGroupNotFoundError,
    ServiceNowRecordNotFoundException,
)
from ..core.ServiceNowManager import ServiceNowManager, DEFAULT_TABLE
from ..core.UtilsManager import FetchResult, fetch_and_filter_incidents, load_processed_ids


class ServiceNowConnector:

    def __init__(
        self,
        connector_scope: SiemplifyConnectorExecution,
        connector_name: str,
        sn_manager: ServiceNowManager,
        max_incidents_per_cycle: int,
        server_time_zone: str,
        whitelist: list[str],
        whitelist_as_blacklist: bool,
        is_test_run: bool = False,
    ) -> None:
        self.connector_scope = connector_scope
        self.connector_scope.script_name = connector_name
        self.logger = connector_scope.LOGGER
        self.sn_manager = sn_manager
        self.max_incidents_per_cycle = max_incidents_per_cycle
        self.server_time_zone = server_time_zone
        self.whitelist = self.get_whitelist_params(whitelist_pairs=whitelist)
        self.whitelist_as_blacklist = whitelist_as_blacklist
        self.is_test_run = is_test_run

    def get_whitelist_params(self, whitelist_pairs):
        """
        Extract whitelist fields
        :param whitelist_pairs: {list} list of comma separated key values
        :return: {dict} of all extracted fields
        """
        result = {}
        for whitelist in whitelist_pairs:
            for field in whitelist.split(","):
                if "=" not in field:
                    result[field] = ""
                    continue
                key, value = field.split("=", 1)
                result[key.strip()] = value.strip()

        return result

    def get_whitelist_queries(self):
        """
        Get whitelist queries
        :return: {list} of whitelist queries or None
        """
        operator = "!=" if self.whitelist_as_blacklist else "="

        return self.prepare_whitelist_params_as_query(
            whitelist_params=self.whitelist, operator=operator
        )

    def prepare_whitelist_params_as_query(self, whitelist_params, operator="="):
        """
        Get whitelist params as query params.
        :param whitelist_params {dict}
        :param operator {str} '=' or '!=' ...
        :return: {list} of query strings
        """
        queries = []
        for key, value in whitelist_params.items():
            if key:
                queries.append(f"{key}{operator}{value}")

        return queries

    def get_incidents(
        self,
        last_run: datetime,
        table_name: str | None,
        assignment_group: str | None,
        existing_ids: list[str]
    ) -> FetchResult:
        """Get tickets since last success time.
        Args:
            last_run(datetime): last run timestamp
            table_name(str): table name
            assignment_group(str): assignment group name
            existing_ids(list[str]): list of already processed IDs
        Returns:
            FetchResult: A dataclass containing incidents, latest timestamp, and IDs
            to persist.
        """
        sn_last_time_format: str = self.sn_manager.convert_datetime_to_sn_format(
            last_run
        )
        incidents: list[Incident] = []
        latest_timestamp: str | None = None
        ids_to_persist: list[str] = []
        sys_id: str | None = None
        if assignment_group:
            sys_id: str = self.get_sys_id_from_group_name(assignment_group)

        try:
            filter_params: SingleJson = {
                "table_name": table_name,
                "custom_queries": self.get_whitelist_queries(),
                "sys_id": sys_id,
                PARAM_UPDATED_TIME: sn_last_time_format,
            }

            fetch_result: FetchResult = fetch_and_filter_incidents(
                self.sn_manager,
                filter_params,
                existing_ids,
                FIELD_SYS_UPDATED_ON,
                self.max_incidents_per_cycle
            )
            incidents: list[Incident] = fetch_result.incidents
            latest_timestamp: str | None = fetch_result.latest_timestamp
            ids_to_persist: list[str] = fetch_result.ids_to_persist

            for incident in incidents:
                for key, value in incident.raw_data.items():
                    if isinstance(value, dict) and LINK_KEY in value:
                        link_url = value.get(LINK_KEY)
                        if any(
                            field in key or field in link_url
                            for field in EXCLUDE_INCIDENT_FIELDS
                        ):
                            continue

                        try:
                            incident.raw_data[key]["context"] = (
                                self.sn_manager.get_additional_context_for_field(
                                    link=value.get(LINK_KEY)
                                )
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to fetch more context for incident {incident.number} "
                                f'field "{key}". Error: {e}.'
                            )

        except Exception as e:
            if NO_RESULTS not in str(e):
                self.logger.error("Failed to fetch incidents")
                self.logger.exception(e)

        self.logger.info(
            f"Found {len(incidents)} incidents since {str(sn_last_time_format)}."
        )

        return FetchResult(
            incidents=incidents,
            latest_timestamp=latest_timestamp,
            ids_to_persist=ids_to_persist
        )

    def get_sys_id_from_group_name(self, assignment_group: str) -> str:
        """Get the sys_id of an assignment group, using cache if available.

        Args:
            assignment_group (str): The name of the assignment group.

        Raises:
            AssignmentGroupNotFoundException: If the assignment group is not found.

        Returns:
            str: The sys_id of the assignment group.
        """
        sys_id = self.connector_scope.get_connector_context_property(
            identifier=self.connector_scope.context.connector_info.identifier,
            property_key=assignment_group,
            )
        if sys_id is None:
            try:
                sys_id = self.sn_manager.get_sys_id_from_group_name(assignment_group)
                if not self.is_test_run:
                    self.connector_scope.set_connector_context_property(
                        identifier=(
                            self.connector_scope.context.connector_info.identifier
                        ),
                        property_key=assignment_group,
                        property_value=sys_id,
                    )
            except ServiceNowRecordNotFoundException as e:
                raise AssignmentGroupNotFoundError(
                    f"Error executing {CONNECTOR_NAME}. Reason: \"{assignment_group}\" "
                    "Assignment Group wasn't found in ServiceNow. Please check the "
                    "spelling."
                ) from e

        return sys_id

    def update_incident_user_info(self, incident):
        """
        Update incident user info
        :param incident: {Incident} Incident instance
        """
        if incident.opener_id and incident.caller_id:
            user_info = self.sn_manager.get_user_info(
                incident.opener_id, incident.caller_id
            )
            user_info = user_info[0] if user_info else None
            if user_info:
                incident.update_incident_with_user_info(user_info)

    def is_valid_incident_time(self, last_run_time, incident_dict):
        """
        Compare incident time to connector last run time to make sure incidents are not taken more than once.
        Base on the ServiceNow Api, incident fetch without time zone
        :param last_run_time: {datetime} last execution time from file
        :param incident_dict: {Incident object}
        :return: {Boolean}
        """
        # compare full dates
        incident_time = convert_string_to_datetime(
            incident_dict.get("opened_at"), timezone_str=self.server_time_zone
        )
        # Checking if incident is already taken, if yes - incident is not valid.
        if incident_time <= last_run_time:
            return False
        return True

    def create_event(self, incident, event_name):
        """
        Create events from incident data
        :param incident: {dict} All incident data
        :param event_name: {string} name of the event
        :return: event {dict} one event from the incident data
        """
        event_details = dict_to_flat(incident)
        event_details["event_name"] = event_name
        try:
            time_field: str = FIELD_SYS_UPDATED_ON
            event_time: int = (
                convert_datetime_to_unix_time(
                    convert_string_to_datetime(
                        incident.get(time_field),
                        timezone_str=self.server_time_zone,
                    )
                )
                if incident.get(time_field)
                else 1
            )
        except ValueError as e:
            self.logger.error(
                f"Failed to parse datetime from incident field '{time_field}'. "
                f"Error: {e}"
            )
            event_time = 1
        except Exception as e:
            self.logger.error(f"Failed to get incident creation time. {e}")
            event_time = 1

        event_details["StartTime"] = event_details["EndTime"] = event_time
        return event_details

    @staticmethod
    def map_priority(sn_priority):
        """
        Mapping ServiceNow priority to siemplify priority
        :param sn_priority: {string} '1, 2 or 3' (1=high, 2=medium, 3=low)
        :return: {int} (40=low, 60=medium, 80=high)
        """
        return PRIORITY_MAPPING.get(sn_priority, LOW_PRIORITY)

    def create_case_info(
        self,
        incident: SingleJson,
        event: SingleJson,
        connector_environment: str,
        rule_generator_field: str,
        use_sys_domain_environment: bool,
    ) -> CaseInfo:
        """Create a CaseInfo object from a ServiceNow incident.

        Args:
            incident (SingleJson): An incident data dictionary.
            event (SingleJson): An event created from the incident data.
            connector_environment (str): The default connector environment.
            rule_generator_field (str): The field name for the rule generator.
            use_sys_domain_environment (bool): If True, use the incident's
                sys_domain as the environment.

        Returns:
            CaseInfo: A CaseInfo object populated with incident data.
        """
        case_info = CaseInfo()
        incident_number: str
        try:
            incident_number = incident["number"]
            case_info.name = incident["number"]
        except Exception as e:
            incident_number = incident["sys_id"]
            case_info.name = incident_number
            self.logger.error(
                f"Found incident, cannot get its number. Get its SysID{str(e)}"
            )
            self.logger.exception(e)

        self.logger.info(f"Creating Case for incident {incident_number}")
        try:
            if rule_generator_field:
                case_info.rule_generator = incident.get(
                    rule_generator_field, CASE_RULE_GENERATOR
                )
            else:
                case_info.rule_generator = CASE_RULE_GENERATOR

            try:
                time_field: str = FIELD_SYS_UPDATED_ON
                case_info.start_time: int = (
                    convert_datetime_to_unix_time(
                        convert_string_to_datetime(
                            incident.get(time_field),
                            timezone_str=self.server_time_zone,
                        )
                    )
                    if incident.get(time_field)
                    else 1
                )
            except ValueError as e:
                self.logger.error(
                    f"Failed to parse datetime from incident field '{time_field}'. "
                    f"Error: {e}"
                )
                case_info.start_time = 1
            except Exception as e:
                self.logger.error(f"Failed to get incident creation time. {e}")
                case_info.start_time = 1

            case_info.end_time = case_info.start_time

            case_info.identifier = incident_number
            case_info.ticket_id = case_info.identifier
            case_info.priority = self.map_priority(incident.get("urgency"))
            case_info.device_vendor = VENDOR
            case_info.device_product = PRODUCT_NAME
            case_info.display_id = case_info.identifier

            case_info.environment = connector_environment
            if use_sys_domain_environment:
                try:
                    domain_id: str = incident["sys_domain"]["value"]
                    if domain_id != SN_DEFAULT_DOMAIN:
                        case_info.environment = (
                            self.sn_manager.get_full_domain_name_by_id(domain_id)
                        )
                except (KeyError, TypeError) as e:
                    self.logger.error("Failed to get incident domain.")
                    self.logger.exception(e)

            case_info.events = [event]

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {str(e)}. Skipping Incident.")

        return case_info


@output_handler
def main(is_test: bool = False) -> None:
    connector_scope = SiemplifyConnectorExecution()
    output_variables = {}
    log_items = []

    connector_scope.LOGGER.info("======= Starting ServiceNow Connector. =======")

    try:

        default_incident_table = extract_connector_param(
            connector_scope,
            param_name="Incident Table",
            print_value=True,
            default_value=DEFAULT_TABLE,
        )

        # Configurations.
        api_root = extract_connector_param(
            connector_scope, param_name="Api Root", print_value=True
        )
        username = extract_connector_param(
            connector_scope, param_name="Username", print_value=False
        )
        password = extract_connector_param(
            connector_scope, param_name="Password", print_value=False
        )
        verify_ssl = extract_connector_param(
            connector_scope,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )
        use_sys_domain_environment = extract_connector_param(
            connector_scope,
            param_name="Use sys_domain Environment",
            input_type=bool,
            default_value=True,
        )
        client_id = extract_connector_param(
            connector_scope, param_name="Client ID", print_value=False
        )
        client_secret = extract_connector_param(
            connector_scope, param_name="Client Secret", print_value=False
        )
        refresh_token = extract_connector_param(
            connector_scope, param_name="Refresh Token", print_value=False
        )
        assignment_group = extract_connector_param(
            connector_scope,
            param_name="Assignment Group",
            print_value=True,
        )
        use_oauth = extract_connector_param(
            connector_scope,
            param_name="Use Oauth Authentication",
            default_value=False,
            input_type=bool,
        )

        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=connector_scope.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )

        days_backwards = extract_connector_param(
            connector_scope,
            param_name="Days Backwards",
            print_value=True,
            input_type=int,
            default_value=DEFAULT_DAYS_BACKWARDS,
        )
        max_incidents_per_cycle = extract_connector_param(
            connector_scope,
            param_name="Max Incidents Per Cycle",
            print_value=True,
            input_type=int,
            default_value=MAX_INCIDENTS_PER_CYCLE,
        )
        server_time_zone = extract_connector_param(
            connector_scope,
            param_name="Server Time Zone",
            print_value=True,
            default_value="UTC",
        )
        rule_generator_field = extract_connector_param(
            connector_scope, param_name="Rule Generator", print_value=True
        )
        table_name = extract_connector_param(
            connector_scope, param_name="Table Name", print_value=True
        )
        event_name = extract_connector_param(
            connector_scope,
            param_name="Event Name",
            print_value=True,
            default_value=DEFAULT_EVENT_NAME,
        )
        get_user_info = extract_connector_param(
            connector_scope,
            param_name="Get User Information",
            input_type=bool,
            print_value=True,
        )
        disable_overflow: bool = extract_connector_param(
            connector_scope,
            param_name="Disable Overflow",
            input_type=bool,
            print_value=True,
            default_value=False,
        )
        whitelist_as_blacklist = extract_connector_param(
            connector_scope,
            param_name="Use whitelist as a blacklist",
            input_type=bool,
            print_value=True,
        )
        environments_whitelist = extract_connector_param(
            connector_scope, param_name="Environments Whitelist", print_value=True
        )
        if environments_whitelist:
            environments_whitelist = environments_whitelist.split(",")
        else:
            environments_whitelist = []

        connector_environment = connector_scope.context.connector_info.environment

        servicenow_connector = ServiceNowConnector(
            connector_scope,
            CONNECTOR_NAME,
            service_now_manager,
            max_incidents_per_cycle,
            server_time_zone,
            connector_scope.whitelist,
            whitelist_as_blacklist,
            is_test,
        )

        last_run_time = siemplify_fetch_timestamp(connector_scope, datetime_format=True)
        last_calculated_run_time = validate_timestamp(
            last_run_time, days_backwards, offset_is_in_days=True
        )
        aware_time = arrow.get(last_calculated_run_time).to(server_time_zone).datetime
        connector_scope.LOGGER.info(
            f"Calculating connector last run time. Last run time is: {last_calculated_run_time}"
        )

        connector_scope.LOGGER.info("Collecting Incidents.")
        existing_ids: list[str] = load_processed_ids(connector_scope)
        loaded_ids = list(existing_ids)
        fetch_result = servicenow_connector.get_incidents(
            last_run=aware_time,
            table_name=table_name,
            assignment_group=assignment_group,
            existing_ids=existing_ids
        )
        incidents: list[Incident] = fetch_result.incidents
        latest_fetched_timestamp: str | None = fetch_result.latest_timestamp
        ids_to_persist_batch: list[str] = fetch_result.ids_to_persist

        if is_test:
            incidents = incidents[:1]

        all_cases = []
        cases_to_ingest = []
        for incident in incidents:
            try:
                if get_user_info:
                    servicenow_connector.update_incident_user_info(incident)

                # Create security event
                event = servicenow_connector.create_event(
                    incident.to_json(), event_name
                )

                # Create case info
                case = servicenow_connector.create_case_info(
                    incident.to_json(),
                    event,
                    connector_environment,
                    rule_generator_field,
                    use_sys_domain_environment,
                )

                is_overflow: bool = not disable_overflow and is_overflowed(
                    connector_scope,
                    case,
                    is_test,
                )
                if is_overflow:
                    # Skipping this alert (and dot ingest it to siemplify)
                    connector_scope.LOGGER.info(
                        f"{str(case.rule_generator)}-{str(case.ticket_id)}-{case.environment}-{str(case.device_product)} found as overflow alert. Skipping"
                    )

                else:
                    # Validate that the environment is in the whitelist
                    if (
                        case.environment
                        and (case.environment not in environments_whitelist)
                        and environments_whitelist
                    ):
                        connector_scope.LOGGER.warn(
                            f"Environment is not in whitelist - {str(case.environment)}"
                        )
                    else:
                        # Ingest the case to siemplify
                        cases_to_ingest.append(case)
                all_cases.append(case)
                existing_ids.append(incident.sys_id)

            except Exception as e:
                connector_scope.LOGGER.error("Failed to create CaseInfo")
                connector_scope.LOGGER.error(f"Error Message: {str(e)}")
                connector_scope.LOGGER.exception(e)
                if is_test:
                    raise

        connector_scope.LOGGER.info("Completed processing incidents.")
        if not is_test and (incidents or latest_fetched_timestamp):
            latest_timestamp = latest_fetched_timestamp
            ids_to_persist = list(ids_to_persist_batch)

            sn_last_time_format = (
                servicenow_connector.sn_manager.convert_datetime_to_sn_format(
                    aware_time
                )
            )
            if latest_timestamp == sn_last_time_format:
                ids_to_persist.extend(loaded_ids)
                ids_to_persist = list(set(ids_to_persist))

            write_ids(connector_scope, ids_to_persist)
        connector_scope.LOGGER.info(
            "Ingest case to Siemplify only if the domain incident is in the whitelist "
            "or if the Incident is in the Default domain."
        )

        if all_cases:
            all_cases = sorted(all_cases, key=lambda case: case.end_time)
            new_last_run_time = all_cases[-1].end_time
        else:
            if latest_fetched_timestamp:
                try:
                    dt = convert_string_to_datetime(
                        latest_fetched_timestamp, timezone_str=server_time_zone
                    )
                    new_last_run_time = convert_datetime_to_unix_time(dt)
                except ValueError:
                    new_last_run_time = convert_datetime_to_unix_time(aware_time)
            else:
                new_last_run_time = convert_datetime_to_unix_time(aware_time)

        connector_scope.LOGGER.info(f"Create {len(cases_to_ingest)} cases.")
        if is_test:
            connector_scope.LOGGER.info(
                "======= ServiceNow Connector Test Finish. ======="
            )
        else:
            siemplify_save_timestamp(connector_scope, new_timestamp=new_last_run_time)

            connector_scope.LOGGER.info("======= ServiceNow Connector Finish. =======")

        connector_scope.return_package(cases_to_ingest, output_variables, log_items)

    except Exception as e:  # pylint: disable=broad-except
        if not is_test:
            connector_scope.LOGGER.error(str(e))
            connector_scope.LOGGER.exception(e)
        else:
            connector_scope.LOGGER.exception(e)
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "True":
        print("Main execution started")
        main()
    else:
        print("Test execution started")
        main(is_test=True)
