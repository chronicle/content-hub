from __future__ import annotations
import base64
import copy
import datetime
import json
from typing import List
from urllib.parse import urljoin
import requests
from . import datamodels

from .RSAExceptions import (
    RSAError,
    RSAEmptyAPIConfigurationException,
    EndpointServerNotFoundException,
    IncorrectHashTypeException,
    IsolationFailException,
    UpdateFailException,
    RSAAuthenticationException,
)

from .RSAParser import RSAParser
from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time
from .UtilsManager import filter_old_alerts
from .constants import (
    PROVIDER_NAME,
    DEFAULT_SIZE_OF_QUERY,
    QUERY_REQUEST_PARAMETERS,
    GET_PCAP_FOR_SESSION_ID_PARAMETERS,
    GET_METADATA_FOR_SESSION_ID_IN_RANGE_PARAMETERS,
    GET_METADATA_FOR_SESSION_ID_PARAMETERS,
    REQUEST_HEADERS,
    UI_SESSION_HEADERS,
    GET_SESSION_ID_QUERY_FORMAT,
    GET_SESSION_ID_BASIC_QUERY,
    SOURCE_IP_FIELD,
    DESTINATION_IP_FIELD,
    SOURCE_USER_FIELD,
    DESTINATION_USER_FIELD,
    SOURCE_DOMAIN_FIELD,
    DESTINATION_DOMAIN_FIELD,
    OBTAIN_TOKEN_URL,
    QUERY_URL,
    PCAP_URL,
    PING_QUERY,
    REQUIRED_SERVICE_ID_URL,
    GET_HOSTS_URL,
    SHA256_LENGTH,
    MD5_LENGTH,
    GET_FILES_URL,
    ISOLATE_ENDPOINT_URL,
    UPDATE_INCIDENT_URL,
    STATUS_MAPPING,
    DEFAULT_HOURS_BACKWARDS,
    ADD_NOTE_URL,
    GET_INCIDENTS,
    GET_INCIDENT_ALERTS,
    DEFAULT_USERNAME_STRING,
    DEFAULT_PASSWORD_STRING,
)


class RSAManager:
    def __init__(
        self,
        broker_api_root=None,
        broker_username=None,
        broker_password=None,
        concentrator_api_root=None,
        concentrator_username=None,
        concentrator_password=None,
        ui_api_root=None,
        ui_username=None,
        ui_password=None,
        size=DEFAULT_SIZE_OF_QUERY,
        verify_ssl=False,
        siemplify=None,
    ):

        self.parser = RSAParser()
        self.size = size
        self.siemplify = siemplify
        self.verify_ssl = verify_ssl

        is_broker_configured = bool(
            broker_api_root and broker_username and broker_password
        )
        is_concentrator_configured = bool(
            concentrator_api_root and concentrator_username and concentrator_password
        )
        is_ui_configured = bool(ui_api_root and ui_username and ui_password)

        if (
            not is_broker_configured
            and not is_concentrator_configured
            and not is_ui_configured
        ):
            raise RSAEmptyAPIConfigurationException(
                "Error: At least one of the API configuration sets should be fully configured."
            )

        self.broker_api_root = None
        self.ui_api_root = None
        self.broker_api_username = None
        self.broker_api_password = None
        if is_broker_configured:
            self.broker_api_root = (
                broker_api_root if broker_api_root[-1] == "/" else broker_api_root + "/"
            )
            self.broker_api_username = broker_username
            self.broker_api_password = broker_password
        elif is_concentrator_configured:
            self.broker_api_root = (
                concentrator_api_root
                if concentrator_api_root[-1] == "/"
                else concentrator_api_root + "/"
            )
            self.broker_api_username = concentrator_username
            self.broker_api_password = concentrator_password

        if is_ui_configured:
            self.ui_api_root = (
                ui_api_root if ui_api_root[-1] == "/" else ui_api_root + "/"
            )
            # UI Address Session.
            self.ui_session = requests.session()
            self.ui_session.verify = verify_ssl
            self.ui_session.headers = copy.deepcopy(UI_SESSION_HEADERS)
            self.ui_session.headers["NetWitness-Token"] = self.obtain_token(
                ui_username, ui_password
            )
            self.ui_session.headers.update({"Content-Type": "application/json"})

        # Concentrator/Broker Session.
        if self.broker_api_root:
            self.session = requests.session()
            self.session.verify = verify_ssl
            self.session.auth = (self.broker_api_username, self.broker_api_password)
            self.session.headers = copy.deepcopy(REQUEST_HEADERS)

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise RSAError(f"{error_msg}: {error} - {error.response.content}")

            raise RSAError(
                f"{error_msg}: {response.json().get('name')} {json.dumps(response.json())}"
            )

    def _get_full_url(self, endpoint, **kwargs):
        """
        Get full url from url identifier.
        :param endpoint: {str} The endpoint url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.ui_api_root, endpoint.format(**kwargs))

    def test_connectivity(self):
        """
        Test integration connectivity.
        :return: {bool}
        """
        # Get result.
        if self.broker_api_root:
            request_url = f"{self.broker_api_root}{PING_QUERY}"
            result = self.session.get(request_url)
            # Verify result.
            self.validate_response(result)
        if self.ui_api_root:
            return True
        return False

    def obtain_token(self, username, password):
        """
        Obtain NetWitness authentication security token.
        :param username: {string} NetWitness username.
        :param password: {string} NetWitness password.
        :return: {string} token
        """
        request_url = f"{self.ui_api_root}{OBTAIN_TOKEN_URL}"
        response = self.ui_session.post(
            request_url, data={"username": username, "password": password}
        )
        self.validate_response(response)
        try:
            if response.json().get("accessToken"):
                return response.json().get("accessToken")
            else:
                raise RSAError("Failed to obtain security token.")
        except ValueError:
            # Response is not json. Server is down?
            raise RSAError(f"Failed to obtain security token: {response.content}")

    def get_session_ids_for_query(
        self, hours_backwards=DEFAULT_HOURS_BACKWARDS, custom_query=""
    ):
        """
        Get session id for query.
        :param hours_backwards: {int} Number of hours backwards for fetching
        :param custom_query: {string}
        :return list of session ids: [string, string]
        """
        # form request URL.
        request_url = urljoin(self.broker_api_root, QUERY_URL)
        # Organize request params.
        get_session_id_request_params = QUERY_REQUEST_PARAMETERS
        hours_timestamp = int(
            convert_datetime_to_unix_time(
                utc_now() - datetime.timedelta(hours=hours_backwards)
            )
            / 1000
        )
        # Set query.
        if custom_query:
            get_session_id_request_params["query"] = GET_SESSION_ID_QUERY_FORMAT.format(
                hours_timestamp, custom_query
            )
        else:
            get_session_id_request_params["query"] = GET_SESSION_ID_BASIC_QUERY
        # Set response size.
        # We will use Max Events To Return * 2. The reason behind it is that in order to sort results from API, we need
        # to use Group By clause and that clause creates a duplicate in the response.
        get_session_id_request_params["size"] = self.size * 2
        # Get result.
        result = self.session.get(request_url, params=get_session_id_request_params)
        # verify result
        self.validate_response(result)

        return self.parser.get_session_ids_list(result.json())

    def get_pcap_of_session_id(self, session_id):
        """
        Gets PCAP information for session id.
        :param session_id: {string}
        :return: PCAP file base64 array {string}
        """
        # Form request url.
        request_url = urljoin(self.broker_api_root, PCAP_URL)
        # Form request parameters.
        get_pcap_for_session_id_params = GET_PCAP_FOR_SESSION_ID_PARAMETERS
        get_pcap_for_session_id_params["sessions"] = session_id
        # Get request.
        result = self.session.get(request_url, params=get_pcap_for_session_id_params)

        # Validate response.
        self.validate_response(result)
        # Return result content(PCAP file byte array).
        return base64.b64encode(result.content).decode("utf-8")

    def get_metadata_from_session_id(self, session_id):
        """
        Get meta keys for a session id.
        :param session_id: {string}
        :return: event meta keys for session id{dict}
        """
        # Form request URL.
        request_url = urljoin(self.broker_api_root, QUERY_URL)
        # Form request parameters.
        get_metadata_ids_from_session_id_params = GET_METADATA_FOR_SESSION_ID_PARAMETERS
        get_metadata_ids_from_session_id_params["id1"] = session_id
        get_metadata_ids_from_session_id_params["id2"] = session_id
        get_metadata_ids_from_session_id_params["size"] = self.size
        # Get response
        result = self.session.get(
            request_url, params=get_metadata_ids_from_session_id_params
        )
        # Validate response.
        self.validate_response(result)
        # Extract ids.
        id1 = result.json()["params"]["field1"]
        id2 = result.json()["params"]["field2"]
        return self.get_metadata_from_meta_id_range(id1, id2)

    def get_metadata_from_meta_id_range(self, first_id, second_id):
        """
        Get meta keys for a range of ids.
        :param first_id: first id in the range of ids {string}
        :param second_id: the last id in the range of ids {string}
        :return: key value pairs of metadata {dict}
        """
        request_url = urljoin(self.broker_api_root, QUERY_URL)
        # Form request parameters.
        get_metadata_ids_from_session_id_params = (
            GET_METADATA_FOR_SESSION_ID_IN_RANGE_PARAMETERS
        )
        get_metadata_ids_from_session_id_params["id1"] = first_id
        get_metadata_ids_from_session_id_params["id2"] = second_id
        get_metadata_ids_from_session_id_params["size"] = self.size
        # Get response
        result = self.session.get(
            request_url, params=get_metadata_ids_from_session_id_params
        )
        # Validate response.
        self.validate_response(result)
        event_dict = {}
        for meta in result.json()["results"]["fields"]:
            event_dict[meta["type"]] = meta["value"]
        return self.parser.build_event_object(event_dict)

    def get_events_for_field(
        self, field, field_value, is_quoted=False, hours=DEFAULT_HOURS_BACKWARDS
    ):
        """
        Gets event by specific field and it's value.
        :param field: the field as it displayed in RSA {string}
        :param field_value: field value to search for {string}
        :param is_quoted: {bool} # There are two types of queries, some demand quoted value the rest do not.
        :param hours: Number of hours backwards for fetching
        :return: list of Event {[Event]}
        """
        # form the query.
        if is_quoted:
            query = f"{field}='{field_value}'"
        else:
            query = f"{field}={field_value}"

        # Get session ids for the query.
        session_ids = self.get_session_ids_for_query(
            hours_backwards=hours, custom_query=query
        )
        # Get events for the session ids.
        events = []
        for session_id in session_ids:
            events.append(self.get_metadata_from_session_id(session_id))
        return events

    def get_events_for_ip(self, ip_address, hours):
        """
        Get events for ip address.
        :param ip_address: {string}
        :param hours: Number of hours backwards for fetching
        :return: list of Event {[Event]}
        """

        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_IP_FIELD, ip_address, is_quoted=False, hours=hours
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_IP_FIELD, ip_address, is_quoted=False, hours=hours
        )

        return events_when_source + events_when_destination

    def get_events_for_user(self, user, hours):
        """
        Get events for user.
        :param user: {string}
        :param hours: Number of hours backwards for fetching
        :return: list of Event {[Event]}
        """
        user = user.replace("\\", "\\\\")
        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_USER_FIELD, user, is_quoted=True, hours=hours
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_USER_FIELD, user, is_quoted=True, hours=hours
        )

        return events_when_source + events_when_destination

    def get_events_for_domain(self, domain, hours):
        """
        Get events for domain.
        :param domain: {string}
        :param hours: Number of hours backwards for fetching
        :return: list of Event {[Event]}
        """

        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_DOMAIN_FIELD, domain, is_quoted=True, hours=hours
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_DOMAIN_FIELD, domain, is_quoted=True, hours=hours
        )

        return events_when_source + events_when_destination

    def get_session_ids_for_field(
        self, field, field_value, is_quoted=False, hours=DEFAULT_HOURS_BACKWARDS
    ):
        """
        Get session ids for specific meta field.
        :param field: field as it is presented in RSA {string}
        :param field_value: field to search for {string}
        :param is_quoted: {bool} # There are two types of queries, some demand quoted value the rest do not.
        :param hours: Number of hours backwards for fetching
        :return: list of dicts where which dict contains session id and its details {list[dict]}
        """
        # form the query.
        if is_quoted:
            query = f"{field}='{field_value}'"
        else:
            query = f"{field}={field_value}"

        # Get session ids for the query.
        session_ids = self.get_session_ids_for_query(
            hours_backwards=hours, custom_query=query
        )

        # Return session ids.
        return session_ids

    def get_pcap_for_ip(self, ip_address, hours):
        """
        Get PCAP file byte array for ip address.
        :param ip_address: {string}
        :param hours: Number of hours backwards for fetching
        :return: PCAP file base64 array {string}
        """
        # Get session ids when ip is a source ip.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_IP_FIELD, ip_address, is_quoted=False, hours=hours
        )
        # Get session ids when ip is a destination ip.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_IP_FIELD, ip_address, is_quoted=False, hours=hours
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        return self.get_pcap_of_session_id(",".join(result_session_ids_list))

    def get_pcap_for_user(self, user, hours):
        """
        Get PCAP file byte array for user.
        :param user: {string}
        :param hours: Number of hours backwards for fetching
        :return: PCAP file base64 array {string}
        """
        # Get session ids when ip is a source user.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_USER_FIELD, user, is_quoted=True, hours=hours
        )
        # Get session ids when ip is a destination user.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_USER_FIELD, user, is_quoted=True, hours=hours
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        return self.get_pcap_of_session_id(",".join(result_session_ids_list))

    def get_pcap_for_domain(self, domain, hours):
        """
         Get PCAP file byte array for host.
        :param domain: {string}
        :param hours: Number of hours backwards for fetching
        :return: PCAP file base64 array {string}
        """
        # Get events when ip is a source ip.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_DOMAIN_FIELD, domain, is_quoted=True, hours=hours
        )
        # Get events when ip is a destination ip.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_DOMAIN_FIELD, domain, is_quoted=True, hours=hours
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        return self.get_pcap_of_session_id(",".join(result_session_ids_list))

    def paginate(self, url, params={}):
        """
        Provide pagination process.
        :param url: {string} Request URL.
        :param params: {dict} Request Parameters.
        :return: {list} list of result objects.
        """
        result_incidents_list = []
        if params:
            response = self.ui_session.get(url, params=params)
        else:
            response = self.ui_session.get(url)
        self.validate_response(response)
        result_incidents_list.extend(response.json().get("items"))
        page_count = response.json().get("pageNumber") + 1
        total_page_amount = response.json().get("totalPages")

        while page_count < total_page_amount:
            params["pageNumber"] = page_count
            if params:
                response = self.ui_session.get(url, params=params)
            else:
                response = self.ui_session.get(url)
            self.validate_response(response)
            result_incidents_list.extend(response.json().get("items"))
            page_count += 1

        return result_incidents_list

    def find_required_service_id(self):
        """
        Returns the service id needed for requests
        :return: Service object
        """
        request_url = f"{self.ui_api_root}{REQUIRED_SERVICE_ID_URL}"
        result = self.ui_session.get(request_url)
        self.validate_response(result)
        data = result.json()
        if not data:
            raise EndpointServerNotFoundException("Endpoint server wasn't found.")

        return self.parser.build_service_object(raw_data=data)

    def search_for_host(self, service_id, value):
        """
        Search for IP endpoint
        :param service_id: Running service id
        :param value: Entity identifier
        :return: Host object
        """
        request_url = f"{self.ui_api_root}{GET_HOSTS_URL}"
        params = {"serviceId": service_id, "pageNumber": 0}
        payload = {
            "criteria": {
                "criteriaList": [
                    {
                        "criteriaList": [],
                        "expressionList": [
                            {
                                "propertyName": "hostName",
                                "restrictionType": "EQUAL",
                                "propertyValues": [{"value": value, "relative": False}],
                            }
                        ],
                        "predicateType": "AND",
                    }
                ],
                "expressionList": [],
                "predicateType": "AND",
            },
            "sort": {"keys": ["riskScore"], "descending": True},
        }
        response = self.ui_session.get(request_url, params=params, json=payload)
        self.validate_response(response)
        results = response.json()
        return self.parser.build_host_object(raw_data=results)

    def search_for_ip(self, service_id, value):
        """
        Search for IP endpoint
        :param service_id: Running service id
        :param value: Entity identifier
        :return: Host object
        """
        request_url = f"{self.ui_api_root}{GET_HOSTS_URL}"
        params = {"serviceId": service_id, "pageNumber": 0}
        payload = {
            "criteria": {
                "criteriaList": [
                    {
                        "criteriaList": [],
                        "expressionList": [
                            {
                                "propertyName": "networkInterfaces.ipv4",
                                "restrictionType": "EQUAL",
                                "propertyValues": [{"value": value, "relative": False}],
                            }
                        ],
                        "predicateType": "AND",
                    }
                ],
                "expressionList": [],
                "predicateType": "AND",
            },
            "sort": {"keys": ["riskScore"], "descending": True},
        }
        response = self.ui_session.get(request_url, params=params, json=payload)
        self.validate_response(response)
        results = response.json()
        return self.parser.build_host_object(raw_data=results)

    def search_for_filename(self, service_id, value):
        """
        Search for IP endpoint
        :param service_id: Running service id
        :param value: Entity identifier
        :return: Host object
        """
        request_url = f"{self.ui_api_root}{GET_FILES_URL}"
        params = {"serviceId": service_id, "pageNumber": 0}
        payload = {
            "criteria": {
                "criteriaList": [
                    {
                        "criteriaList": [],
                        "expressionList": [
                            {
                                "propertyName": "firstFileName",
                                "restrictionType": "EQUAL",
                                "propertyValues": [{"value": value, "relative": False}],
                            }
                        ],
                        "predicateType": "AND",
                    }
                ],
                "expressionList": [],
                "predicateType": "AND",
            },
            "sort": {"keys": ["firstFileName"], "descending": True},
        }
        response = self.ui_session.get(request_url, params=params, json=payload)
        self.validate_response(response)
        results = response.json()
        return self.parser.build_file_object(raw_data=results)

    def search_for_filehash(self, service_id, value):
        """
        Search for IP endpoint
        :param service_id: Running service id
        :param value: Entity identifier
        :return: Host object
        """
        request_url = f"{self.ui_api_root}{GET_FILES_URL}"
        params = {"serviceId": service_id, "pageNumber": 0}
        if len(value) == SHA256_LENGTH:
            property_name = "checksumSha256"
        elif len(value) == MD5_LENGTH:
            property_name = "checksumMd5"
        else:
            raise IncorrectHashTypeException(
                "Not supported hash type. Provide either MD5 or SHA-256."
            )

        payload = {
            "criteria": {
                "criteriaList": [
                    {
                        "criteriaList": [],
                        "expressionList": [
                            {
                                "propertyName": property_name,
                                "restrictionType": "EQUAL",
                                "propertyValues": [{"value": value, "relative": False}],
                            }
                        ],
                        "predicateType": "AND",
                    }
                ],
                "expressionList": [],
                "predicateType": "AND",
            },
            "sort": {"keys": ["firstFileName"], "descending": True},
        }
        response = self.ui_session.get(request_url, params=params, json=payload)
        self.validate_response(response)
        results = response.json()
        return self.parser.build_file_object(raw_data=results)

    def isolate_endpoint(self, agent_id, service_id, comment):
        """
        Execute the isolation request
        :param agent_id: Id of endpoint to isolate
        :param service_id: Running service id
        :param comment: Comment describing isolation reason
        :return: True if successful, exception otherwise
        """
        request_url = (
            f"{self.ui_api_root}{ISOLATE_ENDPOINT_URL.format(agent_id=agent_id)}"
        )
        params = {"serviceId": service_id}
        payload = {"allowDnsOnlyBySystem": False, "exclusions": [], "comment": comment}
        response = self.ui_session.post(request_url, params=params, json=payload)
        try:
            self.validate_response(response)
        except Exception:
            raise IsolationFailException("Unable to request isolation for endpoint.")

    def unisolate_endpoint(self, agent_id, service_id, comment):
        """
        Execute the unisolation request
        :param agent_id: Id of endpoint to isolate
        :param service_id: Running service id
        :param comment: Comment describing isolation reason
        :return: True if successful, exception otherwise
        """
        request_url = (
            f"{self.ui_api_root}{ISOLATE_ENDPOINT_URL.format(agent_id=agent_id)}"
        )
        params = {"serviceId": service_id}
        payload = {"allowDnsOnlyBySystem": False, "exclusions": [], "comment": comment}
        response = self.ui_session.delete(request_url, params=params, json=payload)
        try:
            self.validate_response(response)
        except Exception:
            raise IsolationFailException("Unable to request unisolation for endpoint.")

    def update_incident(self, incident_id, status, assignee):
        """
        Update the incident
        :param incident_id: Id of incident
        :param status: Status to set
        :param assignee: Assignee to set
        :return: True, exception otherwise
        """
        status = STATUS_MAPPING.get(status)
        request_url = (
            f"{self.ui_api_root}{UPDATE_INCIDENT_URL.format(incident_id=incident_id)}"
        )
        payload = {}
        if status:
            payload["status"] = status
        if assignee:
            payload["assignee"] = assignee

        response = self.ui_session.patch(request_url, json=payload)
        try:
            self.validate_response(response, error_msg="Unable to update incident")
        except Exception as e:
            if response.status_code == 400:
                raise UpdateFailException(
                    self.parser.build_error_object(response.json()).message
                )
            raise Exception(e)
        return self.parser.build_incident_object(response.json())

    def add_note_to_incident(self, incident_id, note, author):
        """
        Update the incident
        :param incident_id: Id of incident
        :param note: Note to add
        :param author: Author of note
        :return: True, exception otherwise
        """
        request_url = (
            f"{self.ui_api_root}{ADD_NOTE_URL.format(incident_id=incident_id)}"
        )
        payload = {"author": author, "notes": note}
        response = self.ui_session.post(request_url, json=payload)
        try:
            self.validate_response(response, error_msg="Unable to add note to incident")
        except Exception as e:
            if response.status_code == 400:
                raise UpdateFailException(
                    self.parser.build_error_object(response.json()).message
                )
            raise Exception(e)

    def get_incidents(
        self, start_time: str, limit: int, existing_ids: List[str]
    ) -> List[datamodels.Incident]:
        """
        Get oldest incidents by date range. Incidents are returned from the API in descending order, so we take the last page
        if more pages are available.
        :param limit: {int} Specify the maximum number of incidents to return. You can specify between 1 and 100
        :param start_time: {str} Start time for your request. Enter time using time standard defined in ISO 8601 (e.g.
        1018-01-01T14:00:00.000Z).
        :param existing_ids; {list} List of incident ids that were already processed
        :return: {[datamodels.Incident]}  list of found Incident items found within time range.
        """
        request_url = self._get_full_url(GET_INCIDENTS)
        results = []

        response = self.ui_session.get(
            request_url, params={"since": start_time, "pageSize": limit}
        )
        self.validate_response(
            response, error_msg=f"Failed to get incidents from {PROVIDER_NAME}"
        )
        more_results = response.json().get("hasNext", False)

        if more_results:
            page_number = response.json().get("totalPages", 1)

            # If more pages are available, take the last page as it contains the oldest incidents
            while more_results:
                if limit is not None and len(results) >= limit:
                    break
                response = self.ui_session.get(
                    request_url,
                    params={
                        "since": start_time,
                        "pageNumber": page_number - 1,
                        "pageSize": limit,
                    },
                )
                self.validate_response(
                    response, error_msg=f"Failed to get incidents from {PROVIDER_NAME}"
                )

                incidents = self.parser.build_incident_object_list(
                    list(reversed(response.json().get("items", [])))
                )
                results.extend(
                    filter_old_alerts(
                        self.siemplify.LOGGER,
                        incidents,
                        existing_ids,
                        "id",
                        "event_count",
                    )
                )

                more_results = response.json().get("hasPrevious", False)
                page_number -= 1
        else:
            incidents = self.parser.build_incident_object_list(
                response.json().get("items", [])
            )
            results.extend(
                filter_old_alerts(
                    self.siemplify.LOGGER, incidents, existing_ids, "id", "event_count"
                )
            )

        return results[:limit] if limit is not None else results

    def get_incident_alerts(self, incident_id: str) -> List[datamodels.IncidentAlert]:
        """
        Get an Incident's Alerts. All the alerts that are associated with an incident can be retrieved using the incident's id
        :param incident_id: {str} The incident id.
        :return: {[datamodels.IncidentAlert]} List of associated alerts of the incident.
        """
        request_url = self._get_full_url(GET_INCIDENT_ALERTS, incident_id=incident_id)
        results = []
        more_results = True
        page_number = 0

        while more_results:  # Paginate through incident alerts
            response = self.ui_session.get(
                request_url, params={"pageNumber": page_number}
            )
            self.validate_response(
                response, error_msg=f"Failed to fetch for incident {incident_id} alerts"
            )
            results.extend(self.parser.build_alert_object_list(response.json()))
            more_results = response.json().get("hasNext")
            page_number += 1

        return results

    def get_event_additional_data(self, event_source_id):
        """
        Get additional information about the event
        :param event_source_id: {str} ID of the event
        :return: {} List of EventAdditionalData objects
        """
        if self.broker_api_root:
            url = urljoin(self.broker_api_root, QUERY_URL)
            metadata_response = self.session.get(
                url,
                params={
                    "id1": event_source_id,
                    "id2": event_source_id,
                    "msg": "session",
                    "size": 100,
                },
            )
            self.validate_response(metadata_response)
            metadata = self.parser.build_event_metadata_object(metadata_response.json())

            response = self.session.get(
                url,
                params={
                    "id1": metadata.field_1,
                    "id2": metadata.field_2,
                    "msg": "query",
                    "query": "select *",
                    "size": 100,
                },
            )
            self.validate_response(response)

            return self.parser.build_event_additional_data_list(response.json())

    def get_event_details(self, event_source, event_source_id, custom_credentials):
        """
        Get additional information about the event
        :param event_source: {str} source of the event
        :param event_source_id: {str} ID of the event source
        :param custom_credentials: {dict} Custom data source credentials
        :return: {} List of EventAdditionalData objects
        """
        root_url = self.broker_api_root if self.broker_api_root else ""
        event_source = event_source[:-3] + "1" + event_source[-2:]
        username = (
            custom_credentials.get(DEFAULT_USERNAME_STRING, "")
            if custom_credentials
            else self.broker_api_username
        )
        password = (
            custom_credentials.get(DEFAULT_PASSWORD_STRING, "")
            if custom_credentials
            else self.broker_api_password
        )
        creds = next(
            (
                item
                for item in custom_credentials.get("dataSources", [])
                if item.get("api_root") == event_source
            ),
            None,
        )
        event_source = "https://" + event_source + "/"

        if creds:
            username = creds.get(
                "username", custom_credentials.get(DEFAULT_USERNAME_STRING)
            )
            password = creds.get(
                "password", custom_credentials.get(DEFAULT_PASSWORD_STRING)
            )
            root_url = event_source

        root_url = event_source
        url = urljoin(root_url, QUERY_URL)
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            auth=(username, password),
            verify=self.verify_ssl,
            params={
                "msg": "query",
                "size": 1000,
                "query": f"select * where sessionid={event_source_id}",
            },
        )
        if response.status_code == 401:
            raise RSAAuthenticationException(
                f"Invalid credentials provided for data source: {event_source}. "
                f"Please check the spelling."
            )
        self.validate_response(response)
        return self.parser.build_event_additional_data_list(response.json())
