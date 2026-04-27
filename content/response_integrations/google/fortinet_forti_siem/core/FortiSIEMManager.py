from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import ENDPOINTS, DEFAULT_MAX_LIMIT, INCIDENT_FIELDS
from .UtilsManager import validate_response, filter_old_alerts, xml_to_json
from .FortiSIEMParser import FortiSIEMParser
from soar_sdk.SiemplifyUtils import unix_now
from soar_sdk.SiemplifyDataModel import EntityTypes


class FortiSIEMManager:
    def __init__(self, api_root, username, password, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} FortiSIEM API root
        :param username: {str} FortiSIEM username
        :param password: {str} FortiSIEM password
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = FortiSIEMParser()
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = verify_ssl

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def get_incidents(
        self,
        existing_ids,
        limit,
        start_timestamp,
        statuses,
        events_limit=None,
        track_new_events=True,
        track_new_events_threshold=None,
    ):
        """
        Get incidents
        :param existing_ids: {dict} existing ids json
        :param limit: {int} limit for results
        :param start_timestamp: {int} timestamp for oldest incident to fetch
        :param statuses: {list} list of incident statuses to fetch
        :param events_limit: {int} limit for incidents events
        :param track_new_events: {bool} specifies if incidents new events should be tracked
        :param track_new_events_threshold: {int} specifies how long incidents new events should be tracked
        :return: {list} list of Alert objects
        """
        url = self._get_full_url("get_incidents")

        payload = {
            "filters": {"status": statuses},
            "start": 0,
            "size": max(limit, DEFAULT_MAX_LIMIT),
            "orderBy": "incidentLastSeen",
            "timeFrom": start_timestamp,
            "timeTo": unix_now(),
            "descending": "false",
            "fields": INCIDENT_FIELDS,
        }

        response = self.session.post(url, json=payload)
        validate_response(response)

        return filter_old_alerts(
            self.siemplify_logger,
            self.parser.build_alert_objects(response.json()),
            existing_ids,
            "incident_id",
            events_limit,
            track_new_events,
            track_new_events_threshold,
        )

    def get_incident_events(self, incident_id):
        """
        Get incident events
        :param incident_id: {str} incident id
        :return: {list} list of Event objects
        """
        url = self._get_full_url("get_incident_events")
        params = {"incidentId": incident_id}

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_event_objects(response.json())

    def build_custom_query_payload(
        self,
        fields_to_return,
        sort_field,
        sort_order,
        start_time_seconds,
        end_time_seconds,
        conditions,
    ):
        """
        Function that build the query payload in XML
        :param fields_to_return: {str} Fields to return
        :param sort_field: {str} Field based on which sorting will be done
        :param sort_order: {str} Sorting order DESC, ASC
        :param start_time_seconds: {str} Start Time in second
        :param end_time_seconds: {str} End Time in second
        :param conditions: {str} Conditions to use in the payload
        :return: {str} XML payload
        """
        select_query = "<AttrList />"
        order_query = ""

        if fields_to_return:
            select_query = f"<AttrList>{fields_to_return}</AttrList>"

        if sort_field is not None:
            order_query = f"<OrderByClause><AttrList>{sort_field} {sort_order}</AttrList></OrderByClause>"

        query = f"""<?xml version="1.0" encoding="UTF-8"?><Reports><Report baseline="" rsSync=""><Name>SiemplifyAPIGetEvents</Name><Description>Siemplify API get events</Description><Include/><Exclude/><SelectClause>{select_query}</SelectClause>{order_query}<PatternClause><SubPattern name=""><SingleEvtConstr>{conditions}</SingleEvtConstr></SubPattern></PatternClause><ReportInterval><Low>{start_time_seconds}</Low><High>{end_time_seconds}</High></ReportInterval></Report></Reports>"""
        self.siemplify_logger.info(f"Raw payload used in the request: {query}")
        return query

    def build_query_payload(
        self,
        sort_field,
        sort_order,
        fields_to_return,
        start_time_seconds,
        end_time_seconds,
        event_types,
        ph_event_categories,
        minimum_severity_to_fetch,
        event_ids,
    ):
        """
        Function that build the query payload in XML
        :param fields_to_return: {str} Fields to return
        :param sort_field: {str} Field based on which sorting will be done
        :param sort_order: {str} Sorting order DESC, ASC
        :param start_time_seconds: {str} Start Time in second
        :param end_time_seconds: {str} End Time in second
        :param event_types: {str} CSV of Event Types
        :param ph_event_categories: {str} CSV of PH Event Categories
        :param minimum_severity_to_fetch: {str} Minimum secerity to fetch
        :param event_ids: {str} CSV of Event IDs
        :return: {str} XML payload
        """

        conditions = ""
        event_type_query = ""
        ph_event_category_query = ""
        severity_query = ""
        event_id_query = ""
        select_query = "<AttrList />"
        order_query = ""

        if fields_to_return:
            select_query = f"<AttrList>{fields_to_return}</AttrList>"

        if sort_field is not None:
            order_query = f"<OrderByClause><AttrList>{sort_field} {sort_order}</AttrList></OrderByClause>"

        if event_types:
            for event_type in event_types:
                event_type_query += f' OR eventType = "{event_type}"'
            event_type_query = event_type_query.strip(" OR")
            conditions += f"({event_type_query})"
        if ph_event_categories:
            for ph_event_category in ph_event_categories:
                ph_event_category_query += f" OR phEventCategory = {ph_event_category}"
            ph_event_category_query = ph_event_category_query.strip(" OR")
            conditions += f" AND ({ph_event_category_query})"
        if minimum_severity_to_fetch:
            severity_query += f" OR eventSeverity >= {minimum_severity_to_fetch}"
            severity_query = severity_query.strip(" OR")
            conditions += f" AND ({severity_query})"
        if event_ids:
            for event_id in event_ids:
                event_id_query += f" OR eventId = {event_id}"
            event_id_query = event_id_query.strip(" OR")
            conditions += f" AND ({event_id_query})"

        conditions = conditions.strip(" AND")
        query = f"""<?xml version="1.0" encoding="UTF-8"?><Reports><Report baseline="" rsSync=""><Name>SiemplifyAPIGetEvents</Name><Description>Siemplify API get events</Description><Include/><Exclude/><SelectClause>{select_query}</SelectClause>{order_query}<PatternClause><SubPattern name=""><SingleEvtConstr>{conditions}</SingleEvtConstr></SubPattern></PatternClause><ReportInterval><Low>{start_time_seconds}</Low><High>{end_time_seconds}</High></ReportInterval></Report></Reports>"""
        self.siemplify_logger.info(f"Raw payload used in the request: {query}")
        return query, conditions

    def get_device_info(self, entity, organization):
        """
        Get device info by entity identifier
        :param entity: {SiemplifyEntity} SiemplifyEntity object
        :param organization: {str} organization name
        :return: {DeviceInfo} DeviceInfo object
        """
        url = self._get_full_url("get_device_info")
        params = {"loadDepend": "false"}

        if entity.entity_type == EntityTypes.ADDRESS:
            params["ip"] = entity.identifier
        elif entity.entity_type == EntityTypes.HOSTNAME:
            params["name"] = entity.identifier

        if organization:
            params["organization"] = organization

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_device_info_object(xml_to_json(response.content))

    def start_event_query(self, xml_payload):
        """
        Start events query
        :param xml_payload: {str} xml payload
        :return: {str} executed query id
        """
        url = self._get_full_url("start_event_query")
        response = self.session.post(url, data=xml_payload)
        validate_response(response)
        return response.text

    def get_event_query_progress(self, query_id):
        """
        Get event query progress
        :param query_id: {str} started query id
        :return: {int} query status
        """
        url = self._get_full_url("get_event_query_progress", query_id=query_id)
        response = self.session.get(url)
        validate_response(response)
        return response.text

    def get_event_query_results(self, query_id, limit):
        """
        Get event query results
        :param query_id: {str} completed query id
        :param limit: {int} limit for results
        :return: {list} Event objects
        """
        url = self._get_full_url(
            "get_event_query_results", query_id=query_id, limit=limit
        )
        response = self.session.get(url)
        validate_response(response)
        return self.parser.build_query_result_objects(xml_to_json(response.text))
