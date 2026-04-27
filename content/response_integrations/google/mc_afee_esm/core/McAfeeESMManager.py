from __future__ import annotations
import time

import requests

from copy import deepcopy
from urllib.parse import urljoin
from typing import List, Dict, Union, Any

from .McAfeeESMSession import McAfeeESMSession
from .McAfeeESMExceptions import McAfeeESMException, BadRequestException
from .McAfeeESMParser import McAfeeESMParser
from .datamodels import *
from TIPCommon import filter_old_alerts
from .constants import (
    HEADERS,
    ENDPOINTS,
    SUPPORTED_PRODUCT_VERSIONS,
    DEFAULT_PAGE_SIZE,
    FIRST_PAGE_INDEX,
    MAX_EVENTS_LIMIT,
    CUSTOM_TIME_FILTER,
    QUERY_TIME_EXPRESSION,
    GET_EVENTS_MAIN_QUERY,
    QUERY_TEMPLATE_FOR_CONNECTOR,
    TIME_FILTER_TEMPLATE,
    SEVERITY_FILTER_TEMPLATE,
    SIGIDS_FILTER_TEMPLATE,
    COMPLETE_STATUS,
    TIME_TO_SLEEP_FUNCTION_IN_SECONDS,
    QUERY_RESULTS_LIMIT,
    GET_EVENTS_API_TIMEOUT,
)


class McAfeeESMManager:
    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        product_version: str,
        verify_ssl: bool = False,
        siemplify_logger: object = None,
        siemplify_scope: object = None,
        is_connector: bool = False,
        use_aes_encryption: bool = False,
    ) -> None:
        """Base class constructor.

        Args:
            api_root (str): API root of the McAfee ESM instance. Should be like
            https://1.1.1.1/rs/
            username (str): Username for McAfee ESM instance.
            password (str): Password for McAfee ESM instance.
            product_version (str): Product version. Possible values: 11.1-11.5.
            verify_ssl (bool): Sets session verification. Defaults to False.
            siemplify_logger (object): Logger instance, which will be used within the
            manager.
            siemplify_scope (object): Siemplify object, which is currently used.
            is_connector (bool): Whether the siemplify connector is used.
            Defaults to False.
            use_aes_encryption (bool): If enabled, integration will authenticate using
            AES Encryption and will not do Base64 inside the code. Note: you need to
            provide Login and Password already as Base64 encoded strings.
            Defaults to False.

        Raises:
            McAfeeESMException: If unsupported product version provided.
        """
        self.username = username
        self.password = password
        self.api_root = api_root if api_root[-1] == "/" else api_root + "/"
        if product_version not in SUPPORTED_PRODUCT_VERSIONS:
            raise McAfeeESMException(
                "Unsupported product version provided. Possible values: 11.1, 11.2, 11.3, 11.4, 11.5"
            )
        # Set Session.
        self.session = McAfeeESMSession(
            username=self.username,
            password=self.password,
            api_root=self.api_root,
            is_connector=is_connector,
            siemplify_scope=siemplify_scope,
            siemplify_logger=siemplify_logger,
            use_aes_encryption=use_aes_encryption,
        )
        self.session.headers = deepcopy(HEADERS)
        self.session.set_token()
        self.session.verify = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.siemplify_scope = siemplify_scope
        self.parser = McAfeeESMParser()

    def _get_full_url(self, url_id: str, **kwargs: str) -> str:
        """
        Get full url from url identifier.
        Args:
            url_id: The id of url
            **kwargs: Variables passed for string formatting

        Returns:
            (str): The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self) -> None:
        """
        Test Connectivity
        Returns:
            True, if successful, exception otherwise
        """
        url = self._get_full_url("ping")
        response = self.session.post(url)
        self.validate_response(response)

    def validate_response(self, response: requests.Response) -> None:
        """
        Validate HTTP response
        Args:
            response: HTTP response

        Returns:
            True, if successful, exception otherwise
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            if response.status_code == 400:
                raise BadRequestException(response.content)
            raise McAfeeESMException(
                f"Status code:{response.status_code}, Content:{response.content}, Error: {err}"
            )
        except Exception as err:
            raise Exception(f"Error occurred - Error: {err}")

    def get_alarms(
        self, existing_ids: List, start_timestamp: str, end_timestamp: str, limit: int
    ) -> List:
        """Get triggered alarms

        Args:
            existing_ids: List of alarm ids that are already ingested
            start_timestamp: Start time to fetch alarms from
            end_timestamp: End time to fetch alarms until
            limit: Limit for results

        Returns:
            List of Alarm objects
        """
        url = self._get_full_url("get_alarms")
        params = {
            "triggeredTimeRange": "CUSTOM",
            "customStart": start_timestamp,
            "customEnd": end_timestamp,
        }
        alarms = self.paginate_results(
            method="POST",
            url=url,
            limit=limit,
            parser_method="build_alarm_object",
            params=params,
        )

        filtered_alarms = filter_old_alerts(
            self.siemplify_scope, alarms, existing_ids, "alarm_id"
        )
        return sorted(filtered_alarms, key=lambda alarm: alarm.triggered_date)

    def get_alarm_details(self, alarm_id: str) -> List:
        """Get details on source events of triggered alarms by alarm id

        Args:
            alarm_id: Id of the alarm

        Returns:
            List
        """
        url = self._get_full_url("get_alarm_details")
        params = {"id": alarm_id}
        response = self.session.post(url, params=params)
        self.validate_response(response)

        events = self.parser.export_events_data_from_alarms_data(response.json())
        return sorted(events, key=lambda event: event.get("lastTime"))[
            -MAX_EVENTS_LIMIT:
        ]

    def get_event_details(
        self, event_id: str, time_format: str = None, time_zone: int = None
    ) -> SourceEvent:
        """Get details of source event by id

        Args:
            event_id: Id of the event
            time_format: Time format for timestamp
            time_zone: Time zone for timestamp

        Returns:
            datamodels.SourceEvent
        """
        url = self._get_full_url("get_event_details")
        payload = {"id": event_id}
        response = self.session.post(url, json=payload, timeout=GET_EVENTS_API_TIMEOUT)
        self.validate_response(response)

        return self.parser.build_source_event_object(
            response.json(), time_format, time_zone, self.siemplify_logger
        )

    def get_correlation_alert_details(self, event_id: str) -> SourceEvent:
        """Get details of correlation event by id

        Args:
            event_id: Id of the event

        Returns:
            datamodels.CorrelationAlert
        """
        url = self._get_full_url("get_event_details")
        payload = {"id": event_id}
        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return self.parser.build_correlation_alert_object(response.json())

    def check_correlated_events(self, source_event_ids: List) -> List:
        """Check whether given source events have correlated events

        Args:
            source_event_ids: List of source event ids

        Returns:
            List
        """
        url = self._get_full_url("check_correlations")
        payload = {"list": source_event_ids}
        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return self.parser.extract_correlated_ids(response.json())

    def get_correlated_events(self, source_event_id: str) -> List:
        """Get correlated events by source event id

        Args:
            source_event_id: Source event id that has correlations

        Returns:
            List
        """
        url = self._get_full_url("get_correlated_events")
        params = {"queryType": "EVENT"}
        payload = {
            "eventId": {"value": source_event_id},
            "fields": [{"name": "IPSIDAlertID"}],
        }
        response = self.session.post(url, json=payload, params=params)
        self.validate_response(response)

        return self.parser.extract_event_ids(response.json())

    def paginate_results(
        self,
        method: str,
        url: str,
        limit: int,
        parser_method: str,
        params: Union[Dict, str] = None,
        body: Union[Dict, str] = None,
    ) -> List:
        """
        Load data using pagination
        Args:
            method: The method of the request (GET, POST, PUT, DELETE, PATCH)
            url: Url for loading data
            limit: Max number of items to return
            parser_method: Parser method to convert response json to model
            params: Parameters to send
            body: Body to send

        Returns:
            List of models
        """
        data = []
        params = params or {}
        page_size = max(DEFAULT_PAGE_SIZE, limit)
        params["pageSize"] = page_size
        params["pageNumber"] = FIRST_PAGE_INDEX

        while True:
            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response)
            alerts = self.parser.build_results(
                raw_json=response.json(), method=parser_method, pure_data=True
            )
            data.extend(alerts)
            params["pageNumber"] += 1
            if len(alerts) < page_size:
                break

        return data

    def build_events_query(
        self,
        search_component: Dict,
        entity_identifier: str,
        ips_id: str,
        hours_back: int,
        results_limit: int,
    ) -> Dict:
        """Function that builds events query

        Args:
            search_component: The part of the query with entity info
            entity_identifier: Entity to search for
            ips_id: ips sensor id
            hours_back: The amount of hours to search back
            results_limit: Max results to return

        Returns:
            Query dict
        """
        # Predefine query (taken from the ESM Dashboards Events section in GUI)
        query = deepcopy(GET_EVENTS_MAIN_QUERY)

        # Set the iPS ID
        query["query"]["filters"]["exp"][1]["opr"][-1] = ips_id
        # Set time back.
        query["query"]["filters"]["exp"][0]["opr"][-1] = QUERY_TIME_EXPRESSION.format(
            hours_back=hours_back
        )

        for statement in search_component:
            statement["opr"][-1] = statement["opr"][-1].format(entity_identifier)

        query["query"]["filters"]["exp"][-1]["exp"] = search_component

        # Set the query results limit
        query["limit"] = results_limit

        return query

    def run_events_query(self, query: Dict) -> str:
        """Run the query in ESM

        Args:
            query: Query to run

        Returns:
            Query result URL
        """
        url = self._get_full_url("create_events_query")
        response = self.session.post(url, json=query)
        self.validate_response(response)

        return response.json().get("location")[1:]  # Remove the first '/'

    def check_events_query_status(self, location: str) -> str:
        """Check the query status in ESM

        Args:
            location: Query URI

        Returns:
            Query result URL
        """
        url = urljoin(self.api_root, location)
        response = self.session.get(url)
        self.validate_response(response)

        response_json = response.json()
        if response_json.get("status") == COMPLETE_STATUS:
            return response_json.get("location")[1:]  # Remove the first '/'

    def get_events_query_results(self, location: str, limit: int) -> EventsQueryResult:
        """Get the results of events query

        Args:
            location: Query URI
            limit: Results limit

        Returns:
            EventsQueryResult object
        """
        url = urljoin(self.api_root, location)
        params = {"offset": 0, "page_size": limit, "reverse": False}
        response = self.session.get(url, params=params)
        self.validate_response(response)

        return self.parser.build_events_query_result_object(response.json())

    def execute_query(self, query_type: str, query: Dict) -> str:
        """Executes the given query in ESM

        Args:
            query_type: Type of query to execute
            query: Query to execute

        Returns:
            Result ID of the executed query
        """
        url = self._get_full_url("execute_query")
        params = {"reverse": False, "type": query_type}
        response = self.session.post(url, json=query, params=params)
        self.validate_response(response)

        return response.json().get("resultID")

    def check_query_status(self, result_id: str) -> QueryResult:
        """Check the execution status of the query

        Args:
            result_id: Id of the executed query

        Returns:
            QueryResult object
        """
        url = self._get_full_url("get_query_status")
        payload = {"resultID": result_id}
        response = self.session.post(url, json=payload)
        self.validate_response(response)

        return self.parser.build_query_result_object(response.json())

    def get_query_results(self, result_id: str, limit: int) -> QueryResult:
        """Get the results of the query

        Args:
            result_id: ID of the executed query
            limit: Number of results to return

        Returns:
            QueryResult object
        """
        url = self._get_full_url("get_query_results")
        params = {"startPos": 0, "numRows": limit, "reverse": False}
        payload = {"resultID": result_id}
        response = self.session.post(url, params=params, json=payload)
        self.validate_response(response)

        return self.parser.build_query_result_object(response.json())

    def build_query(
        self,
        fields_to_return: List,
        time_filter: str,
        start_time: str,
        end_time: str,
        filter_field_name: str,
        filter_operator: str,
        filter_values: List,
        sort_field: str,
        sort_order: str,
        limit: int,
        entity_identifier: str = None,
        entity_key: str = None,
    ) -> Dict:
        """Function that builds the query to execute

        Args:
            fields_to_return: List of fields to return
            time_filter: Time frame
            start_time: Start time for results
            end_time: End time for results
            filter_field_name: Field name used for filtering
            filter_operator: Operator used for filtering
            filter_values: List of values used for filtering
            sort_field: Field to use for sorting
            sort_order: Sort order
            limit: Number of results to return
            entity_identifier: Used for creating entity query
            entity_key: Field name for creating entity query

        Returns:
            Query dict
        """
        query_dict = {
            "config": {
                "fields": [{"name": field} for field in fields_to_return],
                "limit": limit,
            }
        }

        # Add field filters
        query_dict["config"].update(
            self._build_filter_query(
                filter_field_name=filter_field_name,
                filter_operator=filter_operator,
                filter_values=filter_values,
                entity_identifier=entity_identifier,
                entity_key=entity_key,
            )
        )

        # Add time filter
        query_dict["config"].update(
            self._build_time_query(
                time_filter=time_filter, start_time=start_time, end_time=end_time
            )
        )

        # Apply sorting, if any
        if sort_field:
            query_dict["config"].update(
                self._build_sort_query(sort_field=sort_field, sort_order=sort_order)
            )

        return query_dict

    @staticmethod
    def _build_time_query(time_filter: str, start_time: str, end_time: str) -> Dict:
        """Function that builds time filter

        Args:
            time_filter: Time frame
            start_time: Start time for results
            end_time: End time for results

        Returns:
            Time filter dict
        """
        if time_filter == CUSTOM_TIME_FILTER:
            return {
                "timeRange": time_filter,
                "customStart": start_time,
                "customEnd": end_time,
            }
        else:
            return {"timeRange": time_filter}

    @staticmethod
    def _build_filter_query(
        filter_field_name: str,
        filter_operator: str,
        filter_values: List,
        entity_identifier: str = None,
        entity_key: str = None,
    ) -> Dict:
        """Function that builds filter

        Args:
            filter_field_name: Field name used for filtering
            filter_operator: Operator used for filtering
            filter_values: List of values used for filtering
            entity_identifier: Used for creating entity query
            entity_key: Field name for creating entity query

        Returns:
            Filter dict
        """
        filters_list = [
            {
                "operator": filter_operator,
                "field": {"name": filter_field_name},
                "type": "EsmFieldFilter",
                "values": [
                    {"type": "EsmBasicValue", "value": value} for value in filter_values
                ],
            }
        ]

        if entity_identifier:
            filters_list.append(
                {
                    "operator": "EQUALS",
                    "field": {"name": entity_key},
                    "type": "EsmFieldFilter",
                    "values": [{"type": "EsmBasicValue", "value": entity_identifier}],
                }
            )

        return {"filters": filters_list}

    @staticmethod
    def _build_sort_query(sort_field: str, sort_order: str) -> Dict:
        """Function that builds sort query

        Args:
            sort_field: Field to use for sorting
            sort_order: Sort order

        Returns:
            Sort dict
        """
        return {"order": [{"direction": sort_order, "field": {"name": sort_field}}]}

    def get_watchlist(self, watchlist_name) -> Watchlist:
        """Get watchlist by name

        Args:
            watchlist_name: Name of the watchlist to find

        Returns:
            datamodels.Watchlist
        """
        url = self._get_full_url("get_watchlist")
        params = {
            "hidden": False,
            "dynamic": False,
            "writeOnly": False,
            "indexedOnly": False,
        }
        response = self.session.post(url, params=params)
        self.validate_response(response)

        results = self.parser.build_results(
            raw_json=response.json(), method="build_watchlist_object", pure_data=True
        )

        watchlist = next(
            (item for item in results if item.name.lower() == watchlist_name.lower()),
            None,
        )

        if not watchlist:
            raise Exception(f'Watchlist with name "{watchlist_name}" doesn\'t exist.')

        return watchlist

    def add_values_to_watchlist(self, watchlist_id: str, values_to_add: List) -> None:
        """Add values to watchlist

        Args:
            watchlist_id: ID of the watchlist to add values
            values_to_add: List of values to add
        """
        url = self._get_full_url("add_watchlist_values")
        payload = {"watchlist": watchlist_id, "values": values_to_add}
        response = self.session.post(url, json=payload)
        self.validate_response(response)

    def remove_values_from_watchlist(
        self, watchlist_id: str, values_to_remove: List
    ) -> None:
        """Remove values from watchlist

        Args:
            watchlist_id: ID of the watchlist
            values_to_remove: List of values to remove
        """
        url = self._get_full_url("remove_watchlist_values")
        payload = {"watchlist": watchlist_id, "values": values_to_remove}
        response = self.session.post(url, json=payload)
        self.validate_response(response)

    def create_advanced_query(self, query: str):
        """
        Manager method for creating query on McAfeeESM
        Args:
            query: str
        Return:
            query_id: str
        """
        url = self._get_full_url("create_advanced_query")
        response = self.session.post(url=url, json=query)
        self.validate_response(response)

        # if query was built and run before:
        response_data = response.json()
        if "totalRows" in response_data.keys():
            objects = []
            fields = [i["field"] for i in response_data["fields"]]
            values = response_data["data"]
            for value in values:
                object_item = {}
                for index, field in enumerate(fields):
                    object_item[field.replace(".", "_")] = value[index]
                objects.append(
                    self.parser.build_advanced_query_result_object(object_item)
                )
            return objects
        return response.json()["location"].split("/")[-1]

    def execute_advanced_query(self, query_id: str) -> List[Any]:
        """
        Manager method for created query on McAfeeESM
        Args:
            query_id: str
        Return:
            list of AdvancedQueryResult objects
        """
        url = self._get_full_url("get_advanced_query_results", **{"query_id": query_id})
        response = self.session.get(url)
        self.validate_response(response)
        results = response.json()
        objects = []
        if results:
            fields = [i["field"] for i in results["fields"]]
            values = results["data"]
            for value in values:
                object_item = {}
                for index, field in enumerate(fields):
                    object_item[field.replace(".", "_")] = value[index]
                objects.append(
                    self.parser.build_advanced_query_result_object(object_item)
                )
        return objects

    def get_query_status(self, query_id: str) -> str:
        """
        Manager method for checking query completion status on McAfeeESM
        Args:
            query_id: str
        Return:
            query status: str
        """
        url = self._get_full_url("query_status", **{"query_id": query_id})
        response = self.session.get(url)
        self.validate_response(response)
        return response.json().get("status")

    def get_event_ids_for_connector(
        self,
        start_time: str,
        end_time: str,
        ips_id: str,
        avg_severity: str,
        sig_ids: str,
    ) -> List:
        """Execute a query and fetch the results

        Args:
            start_time: Start time for the query
            end_time: End time for the query
            ips_id: IPSID that will be used to fetch data
            avg_severity: The lowes average severity to filter with
            sig_ids: Signature ids that will be used for filtering

        Returns:
            List of results
        """
        url = self._get_full_url("create_events_query")
        query = deepcopy(QUERY_TEMPLATE_FOR_CONNECTOR)

        # Set the iPS ID
        query["query"]["filters"]["exp"][1]["opr"][1] = ips_id
        # Set time filter
        query["query"]["filters"]["exp"][0]["opr"][1] = TIME_FILTER_TEMPLATE.format(
            start_time=start_time, end_time=end_time
        )
        # Set severity filter
        if avg_severity:
            SEVERITY_FILTER_TEMPLATE["opr"][1] = avg_severity
            query["query"]["filters"]["exp"].append(SEVERITY_FILTER_TEMPLATE)
        # Set sig ids filter
        if sig_ids:
            SIGIDS_FILTER_TEMPLATE["opr"][1] = sig_ids
            query["query"]["filters"]["exp"].append(SIGIDS_FILTER_TEMPLATE)

        response = self.session.post(url, json=query)
        self.validate_response(response)

        query_location = response.json().get("location")[1:]  # Remove the first '/'
        # Check query status
        result_check_url = urljoin(self.api_root, query_location)
        progress = self.session.get(result_check_url)
        self.validate_response(progress)

        while progress.json().get("status") != COMPLETE_STATUS:
            progress = self.session.get(result_check_url)
            self.validate_response(progress)
            time.sleep(TIME_TO_SLEEP_FUNCTION_IN_SECONDS)

        # Fetch query results
        query_results_location = progress.json().get("location")[
            1:
        ]  # Remove the first '/'
        query_results_url = urljoin(self.api_root, query_results_location)
        results_params = {
            "offset": 0,
            "page_size": QUERY_RESULTS_LIMIT,
            "reverse": False,
        }
        results_response = self.session.get(query_results_url, params=results_params)
        self.validate_response(results_response)

        query_result_obj = self.parser.build_events_query_result_object(
            results_response.json()
        )
        return [
            self.parser.build_query_event_object(item_json)
            for item_json in query_result_obj.to_json_list()
        ]
