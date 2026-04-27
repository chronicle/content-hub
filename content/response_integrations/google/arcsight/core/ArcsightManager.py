from __future__ import annotations
import requests
import base64
import copy
from urllib.parse import urljoin, quote
import netaddr
from simplejson.scanner import JSONDecodeError
from .ArcsightParser import ArcsightParser
from .exceptions import ArcsightApiError, UnableToParseException


# =====================================
#               CONSTS                #
# =====================================
# Define json return type
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
# Arcsight manager API root (8443 as the REST API default port)

API_ENDPOINTS = {
    # Main actions
    "login": "www/core-service/rest/LoginService/login",
    "get_login_url": "www/core-service/rest/LoginService/login?login={username}&password={password}",
    "logout": "www/core-service/rest/LoginService/logout",
    "list_by_name": "www/manager-service/rest/ActiveListService/getResourceByName",
    "find_by_uuid": "www/manager-service/rest/ResourceService/findByUUID",
    "search": "www/manager-service/rest/ManagerSearchService/search1",
    "query_by_name": "/www/manager-service/rest/QueryViewerService/getResourceByName",
    "query_results": "www/manager-service/rest/QueryViewerService/getMatrixData",
    "query_resources_ids": "www/manager-service/rest/QueryViewerService/findAllIds",
    "query_resources_by_ids": "www/manager-service/rest/QueryViewerService/getResourcesByIds",
    "active_list_resources_ids": "www/manager-service/rest/ActiveListService/findAllIds",
    "active_list_resources_by_ids": "www/manager-service/rest/ActiveListService/getResourcesByIds",
    "case_resources_ids": "www/manager-service/rest/CaseService/findAllIds",
    "case_resources_by_ids": "www/manager-service/rest/CaseService/getResourcesByIds",
    "report_resources_ids": "www/manager-service/rest/ReportService/findAllIds",
    "report_resources_by_ids": "www/manager-service/rest/ReportService/getResourcesByIds",
    "reports": "www/manager-service/rest/ReportService/getResourcesByNameSafely",
    "reports_by_id": "www/manager-service/rest/ReportService/getResourceById",
    "reports_generation": "www/manager-service/rest/ArchiveReportService/initDefaultArchiveReportDownloadWithOverwrite",
    "reports_download": "www/manager-service/fileservlet",
    "list_entries_by_uuid": "www/manager-service/rest/ActiveListService/getEntries",
    "add_entries_to_active_list": "www/manager-service/rest/ActiveListService/addEntries",
    "get_security_events": "www/manager-service/rest/SecurityEventService/getSecurityEvents",
    "get_case_by_id": "www/manager-service/rest/CaseService/getResourceById",
    "get_case_by_name": "www/manager-service/rest/CaseService/getResourceByName",
    "update_case": "www/manager-service/rest/CaseService/update",
}


MAX_DEPTH = 5
PAGE_SIZE = 50
REPORT_FORMAT = "Report Format"
VALID_STAGES = ["INITIAL", "QUEUED", "FINAL", "CLOSED", "FOLLOW_UP"]
# Certificate file temp path
CA_CERTIFICATE_FILE_PATH = "cacert.pem"

# API MAIN ERROR HTML CHARACTER AS A DELIMITER
HTML_START_DELIMITER = "<h1>"
HTML_END_DELIMITER = "</h1>"
ERROR_DELIMITER = ":"


class ArcsightManager:
    """
    Responsible for all arcsight Web Service API functionality
    """

    def __init__(
        self,
        server_ip,
        username,
        password,
        verify_ssl=False,
        ca_certificate_file=None,
        logger=None,
    ):
        self.host_api = server_ip
        self.username = username
        self.password = password
        self.quoted_password = quote(password)
        self.session = requests.Session()
        self.session.headers = HEADERS
        self.session.verify = self.__get_verification(
            verify_ssl=verify_ssl, certificate=ca_certificate_file
        )
        # Will be defined in login()
        self.token = None
        self.logger = logger
        self.parser = ArcsightParser()

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {unicode} The full url
        """
        api_root = self.host_api

        return urljoin(api_root, API_ENDPOINTS[url_id].format(**kwargs))

    def __get_verification(self, verify_ssl, certificate=None):
        if certificate:
            try:
                file_content = base64.b64decode(certificate)
                with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                    f.write(file_content.decode())
            except Exception as e:
                raise ArcsightApiError(e)

        return CA_CERTIFICATE_FILE_PATH if (verify_ssl and certificate) else verify_ssl

    def _obtain_token(self):
        """
        Get username token for the REST API use
        :return: {str} valid token
        """
        # Perform login and get token, No certificate validation
        token = self._obtain_token_first_method(self._get_full_url("login"))
        return token

    def _obtain_token_first_method(self, url):
        """
        Perform login and get token with first available method
        :param url: {str} The request url
        :return: {str} The valid token
        """
        response = self.session.post(
            url,
            json={
                "log.login": {"log.login": self.username, "log.password": self.password}
            },
        )

        self.validate_response(
            response,
            "Unable to obtain token with given credentials. "
            "Please verify the credentials and the connection to "
            "the server.",
            display_http_error=False,
        )

        return self.parser.get_token(response.json())

    def _obtain_token_second_method(self):
        """
        Perform login and get token with second available method
        :return: {str} The valid token
        """
        login_url = self._get_full_url(
            "get_login_url", username=self.username, password=self.quoted_password
        )

        response = self.session.get(login_url)

        self.validate_response(
            response,
            "Unable to obtain token with given credentials. "
            "Please verify the credentials and the connection to "
            "the server.",
            display_http_error=False,
        )

        return self.parser.get_token(response.json())

    def login(self):
        """
        Login to arcsight
        """
        self.token = self.token or self._obtain_token()

    def logout(self):
        """
        Logout from arcsight (close open session)
        :return bool: True if log out successful else raise exception
        """
        if not self.token:
            return True
        response = self.session.get(
            self._get_full_url("logout"), params={"authToken": self.token}
        )
        self.validate_response(response, "Unable to logout")
        self.token = None
        return True

    def get_activelist_uuid(self, activelist_name):
        """
        Retrieve activelist uuid by it's name
        :param activelist_name: {str} The relevant activelist name
        :return: {str} activelist uuid
        """
        payload = {
            "act.getResourceByName": {
                "act.authToken": self.token,
                "act.name": activelist_name,
            }
        }
        response = self.session.post(self._get_full_url("list_by_name"), json=payload)
        self.validate_response(response, "Unable to get activelist uuid")

        return self.parser.get_uuid(response.json())

    def get_reports_info_by_name(self, report_name):
        """
        Retrieve reports info by it's name
        :param report_name: {str} The relevant report name
        :return: {list} reports info
        """
        payload = {
            "rep.getResourcesByNameSafely": {
                "rep.authToken": self.token,
                "rep.name": report_name,
            }
        }
        try:
            response = self.session.post(self._get_full_url("reports"), json=payload)
            self.validate_response(response, "Unable to get reports")

            if not response.json()["rep.getResourcesByNameSafelyResponse"]:
                raise ArcsightApiError(f"No reports were found for {report_name}")

            # The result might be single dict or a list of dicts
            if isinstance(
                response.json()["rep.getResourcesByNameSafelyResponse"]["rep.return"],
                list,
            ):
                return response.json()["rep.getResourcesByNameSafelyResponse"][
                    "rep.return"
                ]

            else:
                return [
                    response.json()["rep.getResourcesByNameSafelyResponse"][
                        "rep.return"
                    ]
                ]

        except JSONDecodeError:
            raise ArcsightApiError(f"{response} Cant find report {report_name}")

    def get_report_info_by_id(self, report_id):
        """
        Retrieve report info by it's id
        :param report_id: {str} The relevant report id
        :return: {dict} report info
        """
        payload = {
            "rep.getResourceById": {
                "rep.authToken": self.token,
                "rep.resourceId": report_id,
            }
        }
        try:
            response = self.session.post(
                self._get_full_url("reports_by_id"), json=payload
            )
            self.validate_response(response, "Unable to get report uuid")

            if not response.json()["rep.getResourceByIdResponse"]:
                raise ArcsightApiError(f"No reports were found for {report_id}")

            return response.json()["rep.getResourceByIdResponse"]["rep.return"]
        except JSONDecodeError:
            raise ArcsightApiError(f"{response} Cant find report {report_id}")

    def get_report_info_by_uri(self, report_uri):
        """
        Retrieve report info by it's uri
        :param report_uri: {str} The relevant report uri
        :return: {dict} report info
        """
        # Get the name of the report from the URI
        report_name = report_uri.rsplit("/", 1)[-1]
        payload = {
            "rep.getResourcesByNameSafely": {
                "rep.authToken": self.token,
                "rep.name": report_name,
            }
        }
        response = self.session.post(self._get_full_url("reports"), json=payload)
        self.validate_response(response, "Unable to get reports")
        # In case of missing data, because rep.getResourceByIdResponse
        if not response.json().get("rep.getResourcesByNameSafelyResponse"):
            raise ArcsightApiError(f"No reports were found for {report_uri}")

        return self.parser.build_report_info_object(response.json(), REPORT_FORMAT)

    def search(self, query, limit):
        """
        Perform a free text search
        :param query: {str} The search query
        :param limit: {int} How many items to return in the response
        :return: {list} The search results
        """
        payload = {
            "mss.search1": {
                "mss.authToken": self.token,
                "mss.queryStr": query,
                "mss.pageSize": limit,
            }
        }
        try:
            response = self.session.post(self._get_full_url("search"), json=payload)
            self.validate_response(response, "Unable to search")
            return self.parser.build_search_response_object(response.json())
        except JSONDecodeError:
            raise ArcsightApiError(f"Cant run query: {query}")

    def get_query_uuid(self, query_name):
        """
        Get uuid by query name
        :param query_name: {str} The query name
        :return: {str} The query id
        """
        payload = {
            "qvs.getResourceByName": {
                "qvs.authToken": self.token,
                "qvs.name": query_name,
            }
        }
        response = self.session.post(self._get_full_url("query_by_name"), json=payload)
        self.validate_response(response)

        return self.parser.get_query_uuid(response.json())

    def get_query_result(self, query_id, limit):
        """
        Get results of a query
        :param query_id: {str} The query id
        :param limit: {int} Limit items
        :return: {RawObject} instance
        """
        payload = {
            "qvs.getMatrixData": {"qvs.authToken": self.token, "qvs.id": query_id}
        }

        response = self.session.post(self._get_full_url("query_results"), json=payload)
        self.validate_response(response, f"Unable to get query {query_id} results")

        return self.parser.build_query_raws_object(response.json(), limit)

    def get_report_download_token(self, report_id, dynamic_parameters=None):
        """
        Generate report download token
        :param report_id: {str} The report id
        :param dynamic_parameters: {dict} The dynamic fields for the query to
        generate the report
        :return: {str} The report download token
        """
        fields = (
            [{"key": k, "value": v} for k, v in dynamic_parameters.items()]
            if dynamic_parameters
            else {"key": "dummy_key", "value": "dummay_value"}
        )
        payload = {
            "arc.initDefaultArchiveReportDownloadWithOverwrite": {
                "arc.authToken": self.token,
                "arc.reportId": report_id,
                "arc.reportType": "Manual",
                "arc.fieldValueList": fields,
            }
        }

        response = self.session.post(
            self._get_full_url("reports_generation"), json=payload
        )
        self.validate_response(response)

        return self.parser.get_report_download_token(response.json())

    def download_report(self, download_token):
        """
        Download report
        :param download_token: {str} Download token
        :return: {ReportContent}
        """
        download_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        download_payload = {"file.command": "download", "file.id": download_token}
        response = self.session.post(
            self._get_full_url("reports_download"),
            headers=download_headers,
            data=download_payload,
        )
        self.validate_response(response, f"Unable to download report {download_token}")

        return self.parser.build_report_content(report_content=response.content)

    def get_correlations_from_report(self, download_token):
        """
        Download report and parse the correlation data
        :param download_token: {str} Download token
        :return: {list} List of Correlation objects
        """
        download_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        download_payload = {"file.command": "download", "file.id": download_token}
        response = self.session.post(
            self._get_full_url("reports_download"),
            headers=download_headers,
            data=download_payload,
        )
        self.validate_response(response, f"Unable to download report {download_token}")

        return self.parser.build_correlations_list(
            raw_data=response.content.decode("utf-8")
        )

    def get_resource_by_uuid(self, uuid):
        """
        Get a resource by uuid
        :param uuid: {str} The uuid
        :return: {dict} The resource
        """
        payload = {"res.findByUUID": {"res.authToken": self.token, "res.id": uuid}}
        try:
            response = self.session.post(
                self._get_full_url("find_by_uuid"), json=payload
            )
            self.validate_response(response, "Unable to get resource by uuid")
            return response.json()["res.findByUUIDResponse"]["res.return"]
        except JSONDecodeError:
            raise ArcsightApiError(f"{response} Cant find resource by uuid {uuid}")

    def get_case_by_id(self, case_id):
        """
        Get a case by id
        :param case_id: {str} The id of the case
        :return: {dict} The case data
        """
        payload = {
            "cas.getResourceById": {
                "cas.authToken": self.token,
                "cas.resourceId": case_id,
            }
        }
        try:
            response = self.session.post(
                self._get_full_url("get_case_by_id"), json=payload
            )
            self.validate_response(response, f"Unable to get case {case_id}")
            return response.json()["cas.getResourceByIdResponse"]["cas.return"]
        except JSONDecodeError:
            raise ArcsightApiError(f"{response} Cant find case by id {case_id}")

    def get_case_by_name(self, name):
        """
        Get a case by name
        :param name: {str} The name of the case
        :return: {dict} The case data
        """
        payload = {
            "cas.getResourceByName": {"cas.authToken": self.token, "cas.name": name}
        }
        response = self.session.post(
            self._get_full_url("get_case_by_name"), json=payload
        )
        self.validate_response(response, f"Unable to get case {name}")

        return self.parser.build_case_by_name_object(response.json())

    def update_case_stage(self, case_name, stage):
        """
        Update a case stage
        :param case_name: {str} The name of the case to update
        :param stage: {str} The stage of the case. Valid values:
          - CLOSED
          - QUEUED
          - FINAL
          - FOLLOW_UP
          - INITIAL
        :return: {bool} True if success, exception otherwise.
        """
        case = self.get_case_by_name(case_name)
        case.raw_data["stage"] = stage.upper()

        payload = {
            "cas.update": {"cas.authToken": self.token, "cas.resource": case.raw_data}
        }

        response = self.session.post(self._get_full_url("update_case"), json=payload)
        self.validate_response(response, f"Unable to update case {case_name} stage")

        return True

    def get_activelist_entries_by_uuid(self, uuid, limit=None):
        """
        Retrieve activelist entries by it's uuid
        :param uuid: {str} activelist uuid
        :param limit: {int} how many entries to return
        :return: {EntriesObject}
        """
        # List all ActiveList Entries
        payload = {
            "act.getEntries": {"act.authToken": self.token, "act.resourceId": uuid}
        }

        response = self.session.post(
            self._get_full_url("list_entries_by_uuid"), json=payload
        )
        self.validate_response(response, "Unable to get activelist entries")

        return self.parser.build_activelist_entries_object(response.json(), limit)

    def add_entries_to_activelist_uuid(self, entries, list_uuid=None):
        """
        Add entries to activelist
        :param entries: {dict} {columns: [...], entities: [...]}
        :param list_uuid: {str} activelist uuid
        :return: {bool} Success indicator
        """
        if not entries.get("columns") or not entries.get("entry_list"):
            raise ArcsightApiError("Entries list must contain columns and values")

        payload = self.get_entry_payload(
            list_uuid, entries["columns"], entries["entry_list"]
        )

        response = self.session.post(
            self._get_full_url("add_entries_to_active_list"), json=payload
        )

        self.validate_response(response, "Cannot update active list")

        return True

    def get_query_resources_ids(self, limit=None):
        """
        Get query resources ids
        :param limit {int} Limit for ids
        :return: {list} List of ids
        """
        payload = {"qvs.findAllIds": {"qvs.authToken": self.token}}

        response = self.session.post(
            self._get_full_url("query_resources_ids"), json=payload
        )
        self.validate_response(response, "Unable to Query resources ids")
        return self.parser.get_resources_ids(
            response.json(), key_prefix="qvs", limit=limit
        )

    def get_query_resources_by_ids(self, resources_ids):
        """
        Get query resources by ids
        :param resources_ids {list} List of ids
        :return: {list} List of QueryObject instances
        """
        payload = {
            "qvs.getResourcesByIds": {
                "qvs.authToken": self.token,
                "qvs.ids": resources_ids,
            }
        }

        response = self.session.post(
            self._get_full_url("query_resources_by_ids"), json=payload
        )
        self.validate_response(response, "Unable to get resources details")
        return self.parser.build_queries(response.json())

    def get_active_lists_ids(self, limit=None):
        """
        Get active list resources ids
        :param limit {int} Limit for ids
        :return: {list} List of ids
        """
        payload = {"act.findAllIds": {"act.authToken": self.token}}

        response = self.session.post(
            self._get_full_url("active_list_resources_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Active List resources ids")
        return self.parser.get_resources_ids(
            response.json(), key_prefix="act", limit=limit
        )

    def get_active_lists_resources_by_ids(self, resources_ids):
        """
        Get active list resources by ids
        :param resources_ids {list} List of ids
        :return: {list} List of ActiveListObject instances
        """
        payload = {
            "act.getResourcesByIds": {
                "act.authToken": self.token,
                "act.ids": resources_ids,
            }
        }

        response = self.session.post(
            self._get_full_url("active_list_resources_by_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Active List resources details")
        return self.parser.build_active_lists(response.json())

    def get_case_resources_ids(self, limit=None):
        """
        Get case list resources ids
        :param limit {int} Limit for ids
        :return: {list} List of ids
        """
        payload = {"cas.findAllIds": {"cas.authToken": self.token}}

        response = self.session.post(
            self._get_full_url("case_resources_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Case resources ids")
        return self.parser.get_resources_ids(
            response.json(), key_prefix="cas", limit=limit
        )

    def get_case_resources_by_ids(self, resources_ids):
        """
        Get case resources by ids
        :param resources_ids {list} List of ids
        :return: {list} List of CaseObject instances
        """
        payload = {
            "cas.getResourcesByIds": {
                "cas.authToken": self.token,
                "cas.ids": resources_ids,
            }
        }

        response = self.session.post(
            self._get_full_url("case_resources_by_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Case resources details")
        return self.parser.build_cases(response.json())

    def get_report_resources_ids(self, limit=None):
        """
        Get report resources ids
        :param limit {int} Limit for ids
        :return: {list} List of ids
        """
        payload = {"rep.findAllIds": {"rep.authToken": self.token}}

        response = self.session.post(
            self._get_full_url("report_resources_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Report resources ids")
        return self.parser.get_resources_ids(
            response.json(), key_prefix="rep", limit=limit
        )

    def get_report_resources_by_ids(self, resources_ids):
        """
        Get report resources by ids
        :param resources_ids {list} List of ids
        :return: {list} List of ReportObject instances
        """
        payload = {
            "rep.getResourcesByIds": {
                "rep.authToken": self.token,
                "rep.ids": resources_ids,
            }
        }

        response = self.session.post(
            self._get_full_url("report_resources_by_ids"), json=payload
        )
        self.validate_response(response, "Unable to get Report resources details")
        return self.parser.build_reports(response.json())

    def is_value_in_activelist_column(self, list_id, column_name, value):
        """
        Check if value exist in specific column in activelist on arcsight
        :param list_id: {str} activelist uuid
        :param column_name: {str} The name of the column
        :param value: {str} The name of the value to search for
        :return: {boolean} True if exists, False otherwise.
        """
        try:
            csv_entries = self.get_activelist_entries_by_uuid(list_id)
            columns = csv_entries[0].split(",")
            if column_name in columns:
                index_of_column = columns.index(column_name)
                values_in_column = [
                    entry.split(",")[index_of_column].lower()
                    for entry in csv_entries[1:]
                ]
                if value.lower() in values_in_column:
                    return True
        except Exception:
            raise

        return False

    def get_security_events(self, ids, events_limit):
        """
        Get security events of given ids up to given limit
        :param ids: {[int]} List of ids (ints)
        :param events_limit: {int} The limit
        :return: {[dicts]} list of events (dicts)
        """
        events = []
        # Fetch events tree
        try:
            self._get_security_events_recursive(events, ids, events_limit)
            return events, None

        except ArcsightApiError as e:
            return events, e

    def _get_security_events_recursive(
        self, events, ids, events_limit, current_depth=0
    ):
        """
        Get security events recursivly
        :param events: {[events]} The events found so far
        :param ids: {[int]} List of ids (ints)
        :param current_depth: {int} The current depth of the search
        """
        if not ids:
            return

        if current_depth > MAX_DEPTH:
            return

        if len(events) >= events_limit:
            return

        if len(events) + len(ids) > events_limit:
            ids = ids[: (events_limit - len(events))]

        # Get the events in the current depth
        current_level_events = self._get_security_events_single_level(ids)

        if current_level_events:
            # Extend events with found events
            events.extend(current_level_events)

            # Iterate over newly found events
            for event in current_level_events:
                new_events_ids = []

                # For each event get its base event ids if they are available
                if "baseEventIds" in event.keys():
                    base_events = event["baseEventIds"]

                    if not isinstance(event["baseEventIds"], list):
                        # If only one base event is available - then event['baseEventIds'] is an int
                        base_events = [base_events]

                    # Find ids from baseEventIds that are not already in the found events
                    for base_event_id in base_events:
                        if base_event_id not in [ev["eventId"] for ev in events]:
                            new_events_ids.append(base_event_id)

                    # For each case event id that is not already in the found events,
                    # Get its security events by recursion (while adding 1 to the current depth)
                    if new_events_ids:
                        # New event
                        self._get_security_events_recursive(
                            events, new_events_ids, events_limit, current_depth + 1
                        )

    def _get_security_events_single_level(self, ids):
        """
        Get single level of security events
        :param ids: {[int]} List of ids (ints)
        :return: {[dicts]} List of events
        """

        # CR: Document what -1 stand for
        soap_data = {
            "sev.getSecurityEvents": {
                "sev.authToken": self.token,
                "sev.ids": ids,
                "sev.startMillis": -1,
                "sev.endMillis": -1,
            }
        }

        response = self.session.post(
            self._get_full_url("get_security_events"), json=soap_data
        )

        try:
            response.raise_for_status()

            results = response.json()

            if (
                "sev.getSecurityEventsResponse" in results.keys()
                and "sev.return" in results["sev.getSecurityEventsResponse"]
            ):

                if not isinstance(
                    response.json()["sev.getSecurityEventsResponse"]["sev.return"], list
                ):
                    return [
                        response.json()["sev.getSecurityEventsResponse"]["sev.return"]
                    ]

                return response.json()["sev.getSecurityEventsResponse"]["sev.return"]

            return []

        except Exception as e:
            raise ArcsightApiError(e)

    def remove_invalid_values(self, events):
        for event in events:
            for key, value in event.items():
                try:
                    if str(value) in [
                        "-9223372036854775808",
                        "-2147483648",
                        str(4.9e-324),
                        str(5e-324),
                    ]:
                        event[key] = ""
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Unable to remove invalid value {value}")
                        self.logger.exception(e)

                    else:
                        raise

    def completely_remove_invalid_values(self, events):
        modified_events = []
        for event in events:
            event_to_modify = copy.deepcopy(event)
            for key, value in event.items():
                try:
                    if str(value) in [
                        "-9223372036854775808",
                        "-2147483648",
                        str(4.9e-324),
                        str(5e-324),
                    ]:
                        del event_to_modify[key]
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Unable to remove invalid value {value}")
                        self.logger.exception(e)

                    else:
                        raise
            modified_events.append(event_to_modify)

        return modified_events

    def parse_ip_addresses(self, events):
        for event in events:
            for key, value in event.items():
                if "address" in key.lower():
                    if value:
                        try:
                            ip = str(netaddr.IPAddress(value))
                            event[key] = ip
                        except Exception as e:
                            if self.logger:
                                self.logger.info(
                                    f"Value - '{value}' in key '{key}' wasn't converted to the IP address"
                                )
                            else:
                                raise UnableToParseException(key, value)

    def get_entry_payload(self, list_uuid, columns_names, entry_values):
        """
        Get new entry payload with columns and it's values
        :param list_uuid: {str} List uuid
        :param columns_names: {list} List of columns names
        :param entry_values: {iterable} entries values
        :return: {dict} Entry payload
        """
        return {
            "act.addEntries": {
                "act.authToken": self.token,
                "act.resourceId": list_uuid,
                "act.entryList": {
                    "columns": columns_names,
                    "entryList": [{"entry": entry} for entry in entry_values],
                },
            }
        }

    def validate_response(
        self, response, error_msg="An error occurred", display_http_error=True
    ):
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            if display_http_error:
                raise ArcsightApiError(
                    f"{error_msg}: {error} {self.render_error_body(error.response.content)}"
                )

            raise ArcsightApiError(
                f"{error_msg}: Status Code: {response.status_code}. Response: {self.render_error_body(error.response.content)}"
            )

    def render_error_body(self, html_body):
        """
        Render html body to error main message
        :param html_body: {str} The HTML body of the API error
        :return: {str} Sliced error message
        """
        html_body = html_body if type(html_body) == str else html_body.decode()
        if HTML_START_DELIMITER not in html_body:
            error_text = html_body
        else:
            text_start = html_body.split(HTML_START_DELIMITER)[1]
            error_text = text_start.split(HTML_END_DELIMITER)[0]
            error_text = error_text.split(ERROR_DELIMITER)[-1]
        return error_text
