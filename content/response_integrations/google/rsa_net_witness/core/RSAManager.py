# ==============================================================================
# title           :RSAManager.py
# description     :RSA integration logic.
# author          :victor@siemplify.co
# date            :21-2-18
# python_version  :2.7
# product_version : 11.1.0.0
# ==============================================================================
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
from urllib.parse import urljoin
import os
from xml.etree.ElementTree import Element
import defusedxml.ElementTree as ET
import shutil
import json
import datetime
import copy


# =====================================
#               CONSTS                #
# =====================================
DEFAULT_SIZE_OF_QUERY = "50"
TIME_OFFSET_IN_HOURS = 2

# Payloads.
QUERY_REQUEST_PARAMETERS = {
    "msg": "query",
    "query": "select sessionid where ip.src=10.0.0.138",
    "size": 50,
}
GET_PCAP_FOR_SESSION_ID_PARAMETERS = {
    "render": "pcap",
    "sessions": "12335,35135,351355",
}
GET_RAW_LOGS_FOR_SESSION_ID_PARAMETERS = {
    "render": "logs",
    "sessions": "12335,35135,351355",
}
GET_METADATA_FOR_SESSION_ID_IN_RANGE_PARAMETERS = {
    "id1": "123",
    "id2": "123",
    "msg": "query",
    "query": "select *",
    "size": 50,
}
GET_METADATA_FOR_SESSION_ID_PARAMETERS = {
    "id1": "123",
    "id2": "123",
    "msg": "session",
    "size": 50,
}
GET_INCIDENT_PARAMETERS = {"pageNumber": 0, "pageSize": 100, "since": "", "until": ""}
OBTAIN_TOKEN_PARAMS = {"username": "", "password": ""}

# Headers.
REQUEST_HEADERS = {"Accept": "application/json"}
UI_SESSION_HEADERS = {"NetWitness-Token": ""}

# Queries Formats.
# Get session id.
GET_SESSION_ID_QUERY_FORMAT = "select sessionid where {0}"
GET_SESSION_ID_BASIC_QUERY = "select sessionid"

# RSA fields.
SOURCE_IP_FIELD = "ip.src"
DESTINATION_IP_FIELD = "ip.dst"
SOURCE_USER_FIELD = "user.src"
DESTINATION_USER_FIELD = "user.dst"
SOURCE_DOMAIN_FIELD = "domain.src"
DESTINATION_DOMAIN_FIELD = "domain.dst"

# Rest API URLs
GET_INCIDENTS_URL = "rest/api/incidents"
OBTAIN_TOKEN_URL = "rest/api/auth/userpass"
GET_INCIDENT_FOR_ID_URL = "/rest/api/incidents/{0}/alerts"  # {0} Incident ID

# API URLs
QUERY_URL = "/sdk"
PCAP_URL = "sdk/packets"
UPLOAD_FEED_URL = "/decoder/parsers/upload"
GET_INCIDENT_URL = """/ajax/incidents/3?_dc={current_time}&page=1&start=0&limit=100&sort=[{{"property":"created","direction":"DESC"}}]&filter=[{{"property":"created","value":[880893740159,{current_time}]}},{{"property":"status","value":["NEW","IN_PROGRESS","ASSIGNED","REMEDIATION_REQUESTED"]}}]"""  # {current_time} - Current Time.

GET_ALERTS_FROM_INCIDENT_URL = (
    "/ajax/alerts/3?_dc={0}"
    '&page=1&start=0&limit=100&sort=[{"property":"alert.timestamp",'
    '"direction":"DESC"}]&filter='
    '[{"property":"incidentId","value":"{1}"}]'
)  # {0} - Current Time, {1} - Incident Id.

GET_ALERT_DATA_URL = (
    "/ajax/alerts/events/3/{0}?_"
    "dc={1}&page=1&start=0&limit=100&sort="
    '[{"property":"timestamp",'
    '"direction":"DESC"}]'
)  # {0} - Alert ID, {1} - str(time.time()).replace('.','')


# WatchList files directory.
WATCHLIST_FOLDER_NAME = "watchlist"
WATCHLIST_ZIP_FILE_NAME = "watchlist.zip"
WATCHLIST_XML_FILE_NAME = "watchlist.xml"
WATCHLIST_CSV_FILE_NAME = "watchlist.txt"
WATCHLIST_JSON_FILE_NAME = "watchlist.json"


# XML format
WATCHLIST_METADATA_FORMAT = """<FDF>
    <FlatFileFeed name="Threat Feed Alerter" path="watchlist.txt" separator=",">
        <LanguageKeys>

        </LanguageKeys>
        <Fields>
          <Field index="1" type="index" />
        </Fields>
  </FlatFileFeed>
</FDF>"""

KEY_FORMAT = '<Field index="{0}" type="value" key="{1}" />'


# =====================================
#              CLASSES                #
# =====================================
class RSAError(Exception):
    pass


# ToDo: Adjust the actions and the connectors to the new manager.
class RSA:
    def __init__(
        self,
        concentrator_uri,
        decoder_uri,
        username,
        password,
        ui_uri=None,
        size=DEFAULT_SIZE_OF_QUERY,
        verify_ssl=False,
    ):
        self.concentrator_uri = (
            concentrator_uri if concentrator_uri[-1] == "/" else concentrator_uri + "/"
        )
        self.decoder_uri = decoder_uri if decoder_uri[-1] == "/" else decoder_uri + "/"

        self.size = size

        if ui_uri:
            self.ui_uri = ui_uri if ui_uri[-1] == "/" else ui_uri + "/"

            # UI Address Session.
            self.ui_session = requests.session()
            self.ui_session.verify = verify_ssl
            self.ui_session.headers = copy.deepcopy(UI_SESSION_HEADERS)
            self.ui_session.headers["NetWitness-Token"] = self.obtain_token(
                username, password
            )

        # Concentrator/Decoder Session.
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = (username, password)
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

    @staticmethod
    def list_of_dicts_to_csv(list_of_dicts):
        """
        Gets a list of dictionaries and return a list of strings in CSV format.
        :param list_of_dicts: llst of dictionary objects.
        :return: list of strings in a CSV format {string}]
        """
        csv_result = []
        csv_row = []
        if list_of_dicts:
            headers_list = list(list_of_dicts[0].keys())
            headers_string = ",".join(headers_list).replace(".", " ")
            # Append headers row to result.
            csv_result.append(headers_string)
            for event_dict in list_of_dicts:
                for header in headers_list:
                    # Add value to row.
                    if header in event_dict:
                        csv_row.append(str(event_dict[header]).replace(",", " "))
                    else:
                        csv_row.append("None")
                # Appand new row to result.
                csv_result.append(",".join(csv_row))
                # Reset CSV row parameter.
                csv_row = []
        return csv_result

    @staticmethod
    def validate_file_exists(file_path, default_file_content=""):
        """
        Validates if file exists,if not creates the file and it's dir tree.
        :param file_path:
        :param default_file_content: {string}
        :return:
        """
        # Extract directory from file path.
        file_dir = os.path.dirname(file_path)
        # Verify directory exists.

        if not os.path.isfile(file_path):
            # If directory does
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            open(file_path, "a+").write(default_file_content)

    def test_connectivity(self):
        """
        Test integration connectivity.
        :return: {bool}
        """
        # Get result.
        result = self.session.get(self.concentrator_uri)
        # Verify result.
        self.validate_response(result)
        return True

    def obtain_token(self, username, password):
        """
        Obtain NetWitness authentication security token.
        :param username: {string} NetWitness username.
        :param password: {string} NetWitness password.
        :return: {string} token
        """
        request_url = f"{self.ui_uri}{OBTAIN_TOKEN_URL}"
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

    def get_session_ids_for_query(self, custom_query=""):
        """
        Get session id for query.
        :param custom_query: {string}
        :return list of session ids: [string, string]
        """
        # form request URL.
        request_url = urljoin(self.concentrator_uri, QUERY_URL)
        # Organize request params.
        get_session_id_request_params = QUERY_REQUEST_PARAMETERS
        # Set query.
        if custom_query:
            get_session_id_request_params["query"] = GET_SESSION_ID_QUERY_FORMAT.format(
                custom_query
            )
        else:
            get_session_id_request_params["query"] = GET_SESSION_ID_BASIC_QUERY
        # Set response size.
        get_session_id_request_params["size"] = self.size
        # Get result.
        result = self.session.get(request_url, params=get_session_id_request_params)
        # verify result
        self.validate_response(result)
        # For session ids list.
        session_ids_list = [
            id_dict["value"] for id_dict in result.json()["results"]["fields"]
        ]
        # return results.
        return session_ids_list

    def get_pcap_of_session_id(self, session_id):
        """
        Gets PCAP information for session id.
        :param session_id: {string}
        :return: PCAP file byte array {string}
        """
        # Form request url.
        request_url = urljoin(self.concentrator_uri, PCAP_URL)
        # Form request parameters.
        get_pcap_for_session_id_params = GET_PCAP_FOR_SESSION_ID_PARAMETERS
        get_pcap_for_session_id_params["sessions"] = session_id
        # Get request.
        result = self.session.get(request_url, params=get_pcap_for_session_id_params)

        # Validate response.
        self.validate_response(result)
        # Return result content(PCAP file byte array).
        return result.content

    def get_raw_log_of_session_ids(self, session_id):
        """
        Get raw log for a session id.
        :param session_id: RSA Netwitness session id {string}
        :return: Raw log(meta keys) {dict}
        """
        # Form request URL.
        request_url = urljoin(self.concentrator_uri, PCAP_URL)
        # Form request parameters.
        get_raw_log_for_session_id_params = GET_RAW_LOGS_FOR_SESSION_ID_PARAMETERS
        get_raw_log_for_session_id_params["sessions"] = session_id
        # Get request.
        result = self.session.get(request_url, params=get_raw_log_for_session_id_params)
        # Validate response.
        self.validate_response(result)

        # Form result.
        raw_log_list = [event["log"] for event in result.json()["logs"]]
        # return result.
        return raw_log_list

    def get_metadata_from_session_id(self, session_id):
        """
        Get meta keys for a session id.
        :param session_id: {string}
        :return: event meta keys for session id{dict}
        """
        # Form request URL.
        request_url = urljoin(self.concentrator_uri, QUERY_URL)
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
        request_url = urljoin(self.concentrator_uri, QUERY_URL)
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
        return event_dict

    def get_events_for_field(self, field, field_value, is_quoted=False):
        """
        Gets event by specific field and it's value.
        :param field: the field as it displayed in RSA {string}
        :param field_value: field value to search for {string}
        :param is_quoted: {bool} # There are two types of queries, some demand quoted value the rest do not.
        :return: list of dict when each dict is an event {list[dict]}
        """
        # form the query.
        if is_quoted:
            query = f"{field}='{field_value}'"
        else:
            query = f"{field}={field_value}"

        # Get session ids for the query.
        session_ids = self.get_session_ids_for_query(query)
        # Get events for the session ids.
        events = []
        for session_id in session_ids:
            events.append(self.get_metadata_from_session_id(session_id))

        return events

    def get_events_for_ip(self, ip_address, csv_format=False):
        """
        Get events for ip address.
        :param ip_address: {string}
        :param csv_format: the format in which the data will be returned {bool}
        :return: list of dict when each dict is an event {list[dict]}
        """

        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_IP_FIELD, ip_address, is_quoted=False
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_IP_FIELD, ip_address, is_quoted=False
        )

        result_list = events_when_source + events_when_destination
        # Return complete result.
        if csv_format:
            return self.list_of_dicts_to_csv(result_list)
        else:
            return result_list

    def get_events_for_user(self, user, csv_format=False):
        """
        Get events for user.
        :param user: {string}
        :param csv_format: the format in which the data will be returned {bool}
        :return: list of dict when each dict is an event {list[dict]}
        """

        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_USER_FIELD, user, is_quoted=True
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_USER_FIELD, user, is_quoted=True
        )

        result_list = events_when_source + events_when_destination
        # Return complete result.
        if csv_format:
            return self.list_of_dicts_to_csv(result_list)
        else:
            return result_list

    def get_events_for_domain(self, domain, csv_format=False):
        """
        Get events for domain.
        :param user: {string}
        :param csv_format: the format in which the data will be returned {bool}
        :return: list of dict when each dict is an event {list[dict]}
        """

        # Get events when ip is a source ip.
        events_when_source = self.get_events_for_field(
            SOURCE_DOMAIN_FIELD, domain, is_quoted=True
        )

        # Get events when ip is a destination ip.
        events_when_destination = self.get_events_for_field(
            DESTINATION_DOMAIN_FIELD, domain, is_quoted=True
        )

        result_list = events_when_source + events_when_destination
        # Return complete result.
        if csv_format:
            return self.list_of_dicts_to_csv(result_list)
        else:
            return result_list

    def get_session_ids_for_field(self, field, field_value, is_quoted=False):
        """
        Get session ids for specific meta field.
        :param field: field as it is presented in RSA {string}
        :param field_value: field to search for {string}
        :param is_quoted: {bool} # There are two types of queries, some demand quoted value the rest do not.
        :return: list of dicts where which dict contains session id and its details {list[dict]}
        """
        # form the query.
        if is_quoted:
            query = f"{field}='{field_value}'"
        else:
            query = f"{field}={field_value}"

        # Get session ids for the query.
        session_ids = self.get_session_ids_for_query(query)

        # Return session ids.
        return session_ids

    def get_pcap_for_ip(self, ip_address):
        """
        Get PCAP file byte array for ip address.
        :param ip_address: {string}
        :return: PCAP file byte array {string}
        """
        # Get session ids when ip is a source ip.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_IP_FIELD, ip_address, is_quoted=False
        )
        # Get session ids when ip is a destination ip.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_IP_FIELD, ip_address, is_quoted=False
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        pcap_result = self.get_pcap_of_session_id(",".join(result_session_ids_list))
        # Return result.
        return pcap_result

    def get_pcap_for_user(self, user):
        """
        Get PCAP file byte array for user.
        :param user: {string}
        :return: PCAP file byte array {string}
        """
        # Get session ids when ip is a source user.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_USER_FIELD, user, is_quoted=True
        )
        # Get session ids when ip is a destination user.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_USER_FIELD, user, is_quoted=True
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        pcap_result = self.get_pcap_of_session_id(",".join(result_session_ids_list))
        # Return result.
        return pcap_result

    def get_pcap_for_domain(self, domain):
        """
         Get PCAP file byte array for host.
        :param domain: {string}
        :return: PCAP file byte array {string}
        """
        # Get events when ip is a source ip.
        session_ids_when_source = self.get_session_ids_for_field(
            SOURCE_DOMAIN_FIELD, domain, is_quoted=True
        )
        # Get events when ip is a destination ip.
        session_ids_when_destination = self.get_session_ids_for_field(
            DESTINATION_DOMAIN_FIELD, domain, is_quoted=True
        )
        # Sum results.
        result_session_ids_list = session_ids_when_source + session_ids_when_destination
        # Get pcap file.
        pcap_result = self.get_pcap_of_session_id(",".join(result_session_ids_list))
        # Return result.
        return pcap_result

    @staticmethod
    def parse_upload_parsers_input(input_string):
        """
        Upload feed to RSA Netwitness.
        :param input_string: {string}  #  Format: 'key:val, key:val, key:val'
        :return: {Bool}
        """
        input_dict = {}
        for pair in input_string.split(","):
            # Split key from val.
            key = pair.split(":")[0]
            val = pair.split(":")[1]
            # Add to dict.
            input_dict[key] = val

        return input_dict

    @staticmethod
    def fix_time_string(time_string):
        """
        Fix the time string according to the
        :param time_string: {string} Timestamp to fix.
        :return: {string} Adjusted timestamp.
        """
        if "." in time_string:
            split_time = time_string.split(".")
            return split_time[0] + ".000Z"
        elif "+" in time_string:
            return time_string[:-6] + "Z"

    def update_json_file(self, watchlist_json_file_path, index, key_val_list):
        """
        Update watchlist json file.
        :param watchlist_json_file_path: watchlist json file path {string}
        :param index: entity identifier {string}
        :param key_val_list: user's input {string}
        :return: {void}
        """
        # Form JSON and update JSON file.
        # Read JSON from file.
        input_dict = self.parse_upload_parsers_input(key_val_list)
        with open(watchlist_json_file_path, "rb") as watchlist_json_file:
            watchlist_json = json.loads(watchlist_json_file.read())
            watchlist_json_file.close()
        # Update JSON
        if not watchlist_json:
            watchlist_json[index] = input_dict
            headers = list(input_dict.keys())
        else:
            # Form headers list.
            headers = list(watchlist_json.values())[0].keys()
            headers += list(input_dict.keys())
            # Unify list.
            headers = list(set(headers))

            for ind in watchlist_json:
                for header in headers:
                    # In case of update.
                    if header in input_dict and index == ind:
                        watchlist_json[ind][header] = input_dict[header]
                    else:
                        if header in watchlist_json[ind]:
                            pass
                        elif header in input_dict:
                            watchlist_json[ind][header] = ""

            if index not in watchlist_json:
                watchlist_json[index] = {}
                for header in headers:
                    if header in input_dict:
                        watchlist_json[index][header] = input_dict[header]
                    else:
                        watchlist_json[index][header] = ""

        # Update JSON file
        os.remove(watchlist_json_file_path)
        with open(watchlist_json_file_path, "w") as watchlist_json_file:
            watchlist_json_file.write(json.dumps(watchlist_json))
            watchlist_json_file.close()

    def update_xml_file(
        self,
        watchlist_json_file_path,
        watchlist_xml_file,
        watchlist_metadata_format,
        key_val_list,
        index,
    ):
        """
        Update watchlist xml file.
        :param watchlist_xml_file: watchlist XML file path{string}
        :param watchlist_metadata_format: default XML watchlist file content {string}
        :param watchlist_json_file_path: watchlist json file path {string}
        :param key_val_list: user's input {string}
        :param index: entity identifier {string}
        :return: {void}
        """

        input_dict = self.parse_upload_parsers_input(key_val_list)
        with open(watchlist_json_file_path, "rb") as watchlist_json_file:
            watchlist_json = json.loads(watchlist_json_file.read())
            watchlist_json_file.close()
        # Update JSON
        if not watchlist_json:
            watchlist_json[index] = input_dict
            headers = list(input_dict.keys())
        else:
            # Form headers list.
            headers = list(watchlist_json.values())[0].keys()
            headers += list(input_dict.keys())
            # Unify list.
            headers = list(set(headers))

        # Parse XML
        self.validate_file_exists(
            watchlist_xml_file, default_file_content=watchlist_metadata_format
        )
        whatchlist_xml = ET.parse(watchlist_xml_file)
        xml_root = whatchlist_xml.getroot()
        # Get count of indexes in element.
        fields_element = xml_root.getchildren()[0].getchildren()[1]
        languege_key_element = xml_root.getchildren()[0].getchildren()[0]
        # Create elements and append them to the XML.
        for indexes_count, header in enumerate(headers, 2):
            new_index = Element(
                "Field", index=str(indexes_count), type="value", key=header
            )
            new_key = Element("LanguageKey", name=header, valuetype="Text")
            fields_element.append(new_index)
            languege_key_element.append(new_key)

        # Update XML file.
        os.remove(watchlist_xml_file)
        open(watchlist_xml_file, "a+").write(ET.tostring(xml_root))

    def update_csv_file(
        self, watchlist_json_file_path, watchlist_csv_file_path, key_val_list, index
    ):
        """
        Update watchlist csv file.
        :param watchlist_json_file_path: {string}
        :param watchlist_csv_file_path: {string}
        :param key_val_list: user's input {string}
        :param index: entity identifier {string}
        :return: {void}
        """

        input_dict = self.parse_upload_parsers_input(key_val_list)
        with open(watchlist_json_file_path, "rb") as watchlist_json_file:
            watchlist_json = json.loads(watchlist_json_file.read())
            watchlist_json_file.close()
        # Update JSON
        if not watchlist_json:
            watchlist_json[index] = input_dict
            headers = list(input_dict.keys())
        else:
            # Form headers list.
            headers = list(watchlist_json.values())[0].keys()
            headers += list(input_dict.keys())
            # Unify list.
            headers = list(set(headers))

        with open(watchlist_csv_file_path, "w") as watchlist_csv:
            for ind in watchlist_json:
                row_val_list = []
                for header in headers:
                    row_val_list.append(watchlist_json[ind][header])
                watchlist_csv.write(f'{ind},{",".join(row_val_list)}\n')
            watchlist_csv.close()

    def upload_parsers_feeds(self, index, key_val_list, run_directory):
        """
        Upload new feed to RSA Netwitness.
        :param key_val_list: {string}  #  Format: 'key:val, key:val, key:val'
        :param index: {string} entity identifier
        :param run_directory: {string} The directory that holds the running files.
        :return: {void}
        """
        # ToDo: There is a logic problem for parallel running.The JSON file will be locked because each playbook will try to access the same JSON file.
        # Form request URL
        request_url = urljoin(self.decoder_uri, UPLOAD_FEED_URL)

        run_folder = os.path.join(run_directory, WATCHLIST_FOLDER_NAME)

        watchlist_json_file_path = os.path.join(run_directory, WATCHLIST_JSON_FILE_NAME)
        watchlist_zip_file_path = os.path.join(run_directory, WATCHLIST_ZIP_FILE_NAME)
        watchlist_csv_file_path = os.path.join(run_folder, WATCHLIST_CSV_FILE_NAME)
        watchlist_xml_file_path = os.path.join(run_folder, WATCHLIST_XML_FILE_NAME)

        # Validate watchlist files.
        self.validate_file_exists(watchlist_csv_file_path)
        self.validate_file_exists(watchlist_json_file_path, default_file_content="{}")
        self.validate_file_exists(
            watchlist_xml_file_path, default_file_content=WATCHLIST_METADATA_FORMAT
        )

        # Form JSON and update JSON file.
        self.update_json_file(watchlist_json_file_path, index, key_val_list)

        # Form CSV file.
        self.update_csv_file(
            watchlist_json_file_path, watchlist_csv_file_path, key_val_list, index
        )

        # Form XML file.
        self.update_xml_file(
            watchlist_json_file_path,
            watchlist_xml_file_path,
            WATCHLIST_METADATA_FORMAT,
            key_val_list,
            index,
        )

        # Zip watchlist files.
        shutil.make_archive(run_folder, "zip", run_folder)
        watchlist_zip_file = open(watchlist_zip_file_path, "rb")
        response = self.session.post(
            request_url,
            json=None,
            files={"archive": (WATCHLIST_ZIP_FILE_NAME, watchlist_zip_file)},
        )
        watchlist_zip_file.close()

        # Validate feed uploaded.
        self.validate_response(response)

        # Remove watchlist files.
        os.remove(watchlist_zip_file_path)
        os.remove(watchlist_xml_file_path)
        os.remove(watchlist_csv_file_path)

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

    def get_incident_in_time_range(
        self,
        from_time=datetime.datetime.utcnow(),
        until_time=datetime.datetime.utcnow(),
        max_page_size=100,
    ):
        """
        Fetch all the pages with the incident.
        :param from_time: {datetime} time to fetch from.
        :param until_time: {datetime} time until to fetch.
        :param max_page_size: {integer} Max amount of objects per page.
        :return: {list} list of incident objects.
        """
        request_url = f"{self.ui_uri}{GET_INCIDENTS_URL}"
        params = copy.deepcopy(GET_INCIDENT_PARAMETERS)
        # Adjust the auto generated ISO format to the requested format.
        params["since"] = self.fix_time_string(from_time.isoformat())
        params["until"] = self.fix_time_string(until_time.isoformat())

        params["pageSize"] = max_page_size

        return self.paginate(request_url, params)

    def fetch_alerts_for_incident_by_id(self, incident_id):
        """
        Get alerts for an incident by it's ID.
        :param incident_id: {string} the id of the incident.
        :return: {list} list of alerts objects.
        """
        request_url = f"{self.ui_uri}{GET_INCIDENT_FOR_ID_URL.format(incident_id)}"

        return self.paginate(request_url)


#
