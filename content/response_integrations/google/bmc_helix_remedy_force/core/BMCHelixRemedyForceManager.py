from __future__ import annotations
import requests

from urllib.parse import urljoin
from pypika import Query, Field, Criterion, Order
from bs4 import BeautifulSoup

from .BMCHelixRemedyForceParser import BMCHelixRemedyForceParser
from .BMCHelixRemedyForceExceptions import (
    BMCHelixRemedyForceException,
    RecordTypeNotFound,
    RecordIDNotFound,
    RecordNotCreated,
)
from .constants import *
from TIPCommon import filter_old_alerts
from .UtilsManager import prepare_timestamp_statement, validate_integer_param


class BMCHelixRemedyForceManager:
    def __init__(
        self,
        api_root=None,
        username=None,
        password=None,
        verify_ssl=False,
        siemplify=None,
        client_id=None,
        client_secret=None,
        refresh_token=None,
        login_api_root=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: BMC Helix RemedyForce API root.
        :param username: BMC Helix RemedyForce Username.
        :param password: BMC Helix RemedyForce Password.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the BMC Helix RemedyForce server is valid.
        :param siemplify: Siemplify instance.
        :param client_id: {str} BMC Helix RemedyForce client ID of the connected app.
        :param client_secret: {str} BMC Helix Remedyforce client secret of the connected app.
        :param refresh_token: {str} Refresh token for the OAuth authorization.
        :param login_api_root: {str} API root that is used to authenticate in BMC Helix Remedyforce.
        """

        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.login_api_root = (
            login_api_root if login_api_root[-1:] == "/" else login_api_root + "/"
        )
        self.username = username
        self.password = password
        self.siemplify = siemplify
        self.parser = BMCHelixRemedyForceParser()

        self.session = requests.session()
        self.session.verify = verify_ssl
        if client_id and client_secret and refresh_token:
            self.session_id = self.get_access_token(
                client_id, client_secret, refresh_token
            )
        elif username and password:
            self.session_id = self.get_session_id(
                password=self.password, username=self.username
            )
        else:
            raise BMCHelixRemedyForceException(
                "Please provide necessary parameters for either Basic or "
                "Oauth authentication"
            )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.session_id}",
                "Content-Type": "application/json",
            }
        )

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def get_access_token(self, client_id, client_secret, refresh_token):
        """
        Obtain the access token
        :param client_id: {str} The client id to authenticate with
        :param client_secret: {str} The secret of the given client id
        :param refresh_token: {str} The current refresh token
        :return: {str} The new access token
        """
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        response = self.session.post(
            urljoin(self.login_api_root, ENDPOINTS["login"]), data=data
        )
        self.validate_access_token_response(response, "Unable to obtain access token")
        return response.json()["access_token"]

    @staticmethod
    def obtain_refresh_token(
        client_id, client_secret, redirect_uri, code, login_api_root
    ):
        """
        Obtain a refresh token
        :param client_id: {str} The client id to authenticate with
        :param client_secret: {str} The secret of the given client id
        :param redirect_uri: {str} The redirect uri that matched the given client
        :param code: {str} The generated code from the authorizing step
        :param login_api_root: {str} API root that is used to authenticate in BMC Helix Remedyforce.
        :return: {str} The new refresh token
        """
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        response = requests.post(urljoin(login_api_root, ENDPOINTS["login"]), data=data)
        BMCHelixRemedyForceManager.validate_access_token_response(
            response, error_msg="Unable to obtain refresh token"
        )
        return response.json()

    @staticmethod
    def validate_access_token_response(response, error_msg="An error occurred"):
        """
        Validate the access token response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:
            response.raise_for_status()

            if response.status_code != 200:
                raise BMCHelixRemedyForceException(f"{error_msg}: {response.content}")
        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise BMCHelixRemedyForceException(
                    f"{error_msg}: {error} - {error.response.content}"
                )

            raise BMCHelixRemedyForceException(
                f"{error_msg}: {response.json().get('error')} {response.json().get('error_description')}"
            )

    @staticmethod
    def validate_response(response, error_msg="An error occurred", action_type=None):
        try:
            if (
                response.status_code == 404
                and "The requested resource does not exist" in response.text
            ):
                raise RecordTypeNotFound("Record Type Not Found")

            if response.status_code == 404:
                raise RecordIDNotFound("Record ID Not Found")

            if response.status_code == 400:
                error_message = (
                    response.json()[0].get("message")
                    if response.json()[0].get("message")
                    else response.text
                )
                raise RecordNotCreated(error_message)

            response.raise_for_status()

        except requests.HTTPError as error:
            raise BMCHelixRemedyForceException(
                f"{error_msg}: {error} {error.response.content}"
            )

    def get_session_id(self, password, username):
        """
        :param username: BMC Helix RemedyForce Username.
        :param password: BMC Helix RemedyForce Password.
        :return: {string} Session ID
        """
        request_url = urljoin(self.login_api_root, ENDPOINTS["get_session_id"])

        self.session.headers.update({"Content-Type": "text/xml", "SOAPAction": "Login"})

        SESSION_ID_XML = """<?xml version="1.0" encoding="utf-8" ?>
            <env:Envelope xmlns:xsd=" http://www.w3.org/2001/XMLSchema "
                xmlns:xsi=" http://www.w3.org/2001/XMLSchema-instance "
                xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
                <env:Body>
                    <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                        <n1:username>{username}</n1:username>
                        <n1:password>{password}</n1:password>
                    </n1:login>
                </env:Body>
            </env:Envelope>

            """

        res = self.session.post(
            request_url,
            data=SESSION_ID_XML.format(username=username, password=password),
        )
        self.validate_response(res)

        soup = BeautifulSoup(res.content, "lxml")
        session_id = soup.findAll("sessionid")
        session_id = session_id[0]

        return session_id.text

    def test_connectivity(self):
        """
        Test integration to the BMC Helix RemedyForce.
        :return: {bool} True if successful, exception otherwise
        """
        request_url = self._get_full_url("test_connectivity")

        result = self.session.get(request_url)
        self.validate_response(result)

    def create_record(self, record_type, record_payload):
        """
        Function that creates records
        :param record_type {str} Record Type
        :param record_payload {str} Record Payload
        :return: {JSON} Raw response in JSON
        """
        request_url = self._get_full_url("create_record", record_type=record_type)

        result = self.session.post(request_url, data=record_payload)
        self.validate_response(result)

        return result.json()

    def update_record(self, record_type, fields_to_update, record_id):
        """
        Function that creates records
        :param record_id {} Record ID
        :param record_type {str} Record Type
        :param fields_to_update {str} Fields To Update

        """
        request_url = self._get_full_url(
            "manage_record", record_type=record_type, record_id=record_id
        )

        result = self.session.patch(request_url, data=fields_to_update)
        self.validate_response(result)

    def delete_record(self, record_type, record_id):
        """
        Function that deletes records
        :param record_id {} Record ID
        :param record_type {str} Record Type
        """
        request_url = self._get_full_url(
            "manage_record", record_type=record_type, record_id=record_id
        )

        result = self.session.delete(request_url)
        self.validate_response(result)

    def get_record_details(self, record_type, record_id, fields_to_return):
        """
        Function that gets details about the record
        :param record_id {} Record ID
        :param record_type {str} Record Type
        :param fields_to_return {list} List Of Fields to Return
        :return: {RecordObject} Record Object
        """
        request_url = self._get_full_url(
            "manage_record", record_type=record_type, record_id=record_id
        )

        result = self.session.get(request_url)
        self.validate_response(result)

        return self.parser.build_siemplify_record_object(
            result.json(), fields_to_return=fields_to_return
        )

    def get_record_types(self, filter_logic, filter_value, limit):
        """
        Function that gets details about the record
        :param record_id {} Record ID
        :param record_type {str} Record Type
        """
        request_url = self._get_full_url("get_objects")

        result = self.session.get(request_url)
        self.validate_response(result)

        return self.parser.build_siemplify_record_types_object(
            raw_data=result.json(),
            filter_logic=filter_logic,
            filter_value=filter_value,
            limit=limit,
        )

    def execute_custom_query(self, query):
        """
        Function that executes SQQL Query
        :param query {} Query To Execute
        :return: {RecordObject} Record Object
        """
        request_url = self._get_full_url("execute_query")

        params = {"q": query}

        result = self.session.get(request_url, params=params)
        self.validate_response(result)

        return self.parser.build_siemplify_query_object(result.json())

    def get_incidents(
        self,
        existing_ids,
        limit,
        start_time,
        lowest_priority,
        ingest_empty_priority,
        types,
    ):
        """
        Get incidents
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_time: {datetime} The start datetime from where to fetch
        :param lowest_priority: {int} Lowest priority to use for fetching incidents
        :param ingest_empty_priority: {bool} If True, will fetch incidents that don't have priority
        :param types: {list} List of incident types to fetch
        :return: {list} The list of filtered Incident objects
        """
        request_url = self._get_full_url("get_incidents")
        query = self._build_request_query(
            start_time=start_time,
            lowest_priority=lowest_priority,
            ingest_empty_priority=ingest_empty_priority,
            types=types,
            limit=limit,
        )
        params = {"q": query}
        response = self.session.get(request_url, params=params)
        self.validate_response(response)
        incidents = self.parser.build_incident_objects(raw_data=response.json())

        filtered_incidents = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=incidents,
            existing_ids=existing_ids,
            id_key="id",
        )
        return sorted(filtered_incidents, key=lambda incident: incident.created_date)[
            :limit
        ]

    def _build_request_query(
        self,
        start_time,
        lowest_priority,
        ingest_empty_priority,
        types,
        limit=LIMIT_PER_REQUEST,
    ):
        """
        Prepare the query string
        :param start_time: {str} Start time for results
        :param lowest_priority: {int} Lowest priority to use for fetching incidents
        :param ingest_empty_priority: {bool} If True, will fetch incidents that don't have priority
        :param types: {list} List of incident types to fetch
        :param limit: {int} Number of results to return
        :return: {str} Request query
        """
        validate_integer_param(lowest_priority, "Lowest Priority")
        validate_integer_param(limit, "Max Incidents To Fetch")
        # validate_date_param(start_time)

        BMCServiceDesk__Incident__c = Query.Table("BMCServiceDesk__Incident__c")
        query = (
            Query.from_(BMCServiceDesk__Incident__c)
            .select("FIELDS(ALL)")
            .where(BMCServiceDesk__Incident__c.CreatedDate >= Field(start_time))
        )

        if lowest_priority:
            if not ingest_empty_priority:
                query = query.where(
                    BMCServiceDesk__Incident__c.BMCServiceDesk__Priority_ID__c
                    <= "%s" % lowest_priority
                    & BMCServiceDesk__Incident__c.BMCServiceDesk__Priority_ID__c
                    != BMCServiceDesk__Incident__c.null
                )
            else:
                query = query.where(
                    BMCServiceDesk__Incident__c.BMCServiceDesk__Priority_ID__c
                    <= f"{lowest_priority}"
                )

        query = query.where(
            (BMCServiceDesk__Incident__c.BMCServiceDesk__Status_ID__c == "OPENED")
            | (BMCServiceDesk__Incident__c.BMCServiceDesk__Status_ID__c == "ASSIGNED")
        )
        if types:
            query = query.where(
                Criterion.any(
                    [
                        BMCServiceDesk__Incident__c.BMCServiceDesk__Type__c == _type
                        for _type in types
                    ]
                )
            )

        query = query.orderby(BMCServiceDesk__Incident__c.CreatedDate, order=Order.asc)
        query = query.limit(limit)

        return query.get_sql(quote_char="")

    def build_query(
        self,
        record_type,
        where_filter,
        time_frame,
        start_time,
        end_time,
        fields_to_return,
        sort_field,
        sort_order,
        limit,
    ):
        """
        Function that prepares the SOQL Query for BMC
        :param record_type {str} Record Type to Query
        :param where_filter {str} WHERE statement in the query
        :param time_frame {str} Timeframe
        :param start_time {str} Start Time
        :param fields_to_return {str} Fields To Return
        :param end_time {str} End Time
        :param sort_field {str} Field on which the sorting should be done
        :param sort_order {str} Sort Order ASC/DESC
        :param limit {str} Max Results to Return - LIMIT in Query
        :return: {str} Query
        """

        _table = Query.Table(record_type)
        basic_query = Query.from_(_table)

        if fields_to_return:
            for field in fields_to_return:
                basic_query = basic_query.select(Field(field))
        else:
            basic_query = basic_query.select("FIELDS(ALL)")

        if where_filter:
            basic_query = basic_query.where(Field(where_filter))
        if time_frame != TIME_FRAME_CUSTOM:
            start_time, end_time = prepare_timestamp_statement(time_frame)
            if time_frame in [
                TIME_FRAME_LAST_HOUR,
                TIME_FRAME_LAST_6HOURS,
                TIME_FRAME_LAST_24HOURS,
            ]:
                basic_query = basic_query.where(_table.CreatedDate >= Field(start_time))

            else:
                basic_query = basic_query.where(_table.CreatedDate >= Field(start_time))
                basic_query = basic_query.where(_table.CreatedDate >= Field(end_time))

        else:
            basic_query = basic_query.where(_table.CreatedDate >= Field(start_time))
            if end_time:
                basic_query = basic_query.where(_table.CreatedDate <= Field(end_time))

        basic_query = basic_query.orderby(_table.CreatedDate, order=Order.asc)

        if limit:
            # basic_query = basic_query + f" LIMIT {limit}"
            basic_query = basic_query.limit(limit)

        return basic_query.get_sql(quote_char="")
