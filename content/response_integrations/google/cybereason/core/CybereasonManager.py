from __future__ import annotations
import base64
import binascii
import re

import requests

from soar_sdk.SiemplifyDataModel import EntityTypes
from .CybereasonParser import CybereasonParser
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time

from .utils import get_hash_type
from urllib.parse import urljoin
from .exceptions import *
from .constants import (
    CONNECTION_KEY,
    FAILURE_STATUS,
    FILE_FIELDS,
    FILTER_OPERATORS,
    INTEGRATION_NAME,
    MD5,
    PROCESS_FIELDS,
    QUERIES_KEY,
    QUERY_FILTER_DELIMITER,
    QUERY_FILTER_ITEMS_DELIMITER,
    QUERY_FILTER_ITEMS_REQUIRED_COUNT,
    QUERY_FILTER_VALUES_DELIMITER,
    REQUEST_TYPE_KEY,
    REQUEST_TYPE_MAPPING,
    SHA1,
    STATUSES,
)


HEADERS = {"Content-Type": "application/json"}

PAGE_SIZE = 100
DEFAULT_PER_FEATURE_LIMIT = 100
DEFAULT_RESULTS_LIMIT = 10000
DEFAULT_PER_GROUP_LIMIT = 100
DEFAULT_TEMPLATE_CONTEXT = "SPECIFIC"
MALOP_TEMPLATE_CONTEXT = "MALOP"
MACHINE_TEMPLATE_CONTEXT = "Machine"
OVERVIEW_TEMPLATE_CONTEXT = "OVERVIEW"
DEFAULT_QUERY_TIMEOUT = 120000
SUCCESS = ["succeeded", "success"]
UNKNOWN_ERROR = "Unknown error"

MALOP_LOGON_SESSION_TYPE = "MalopLogonSession"
MALOP_PROCESS_TYPE = "MalopProcess"
MALOP_TYPE = "Malop"

ISOLATION_ERRORS = {
    "FailedSending": "The isolation request to the Sensor was not sent",
    "Primed": "Because the Sensor is offline, the request has been prepared to send to the Sensor as soon as it is online",
    "UnknownProbe": "The Sensor specified in the request is unknown",
    "NotSupported": "The Sensor version does not support isolation",
    "Disconnected": "The Sensor in the request is disconnected from the server",
    "TimeoutSending": "The isolation request exceeded the maximum allowable timeout during the period the request was sent",
    "Failed": "The isolation request failed",
    "Timeout": "The isolation request timed out",
    "UnauthorizedUser": "The selected user cannnot perform this request",
    "partialResponse": "The isolation request received a partial response from the Sensor before the timeout period",
    "Aborted": "The isolation request was aborted",
    "ProbeRemoved": "The Sensor was removed",
    "FailedSendingToServer": "The isolation request failed on sending to the server",
}

MALOPS_FIELDS = [
    "elementDisplayName",
    "detectionType",
    "malopActivityTypes",
    "affectedMachines",
    "affectedUsers",
    "rootCauseElements",
    "suspects",
    "totalNumberOfIncomingConnections",
    "totalNumberOfOutgoingConnections",
    "totalReceivedBytes",
    "totalTransmittedBytes",
    "decisionFeature",
    "iconBase64",
    "isBlocked",
    "hasRansomwareSuspendedProcesses",
    "decisionFeatureSet",
    "filesToRemediate",
]

MACHINE_FIELDS = [
    "timeStampSinceLastConnectionTime",
    "freeDiskSpace",
    "platformArchitecture",
    "self",
    "adCompany",
    "adOU",
    "adSid",
    "drivers",
    "hasMalops",
    "hasRemovableDevice",
    "adCanonicalName",
    "isIsolated",
    "mountPoints",
    "osType",
    "adDNSHostName",
    "elementDisplayName",
    "logonFileMissingTimestamp",
    "autoruns",
    "users",
    "pylumId",
    "suspiciousProcesses",
    "isLaptop",
    "isActiveProbeConnected",
    "processes",
    "services",
    "cpuCount",
    "adDescription",
    "adLocation",
    "maliciousTools",
    "lastSeenTimeStamp",
    "deviceModel",
    "uptime",
    "mbrHashString,users",
    "freeMemory",
    "adDepartment",
    "totalDiskSpace",
    "totalMemory",
    "adMachineRole",
    "hasSuspicions",
    "logonSessions",
    "domainFqdn",
    "adOrganization",
    "isSuspiciousOrHasSuspiciousProcessOrFile",
    "maliciousProcesses",
    "adDisplayName",
    "networkInterfaces",
    "osVersionType",
    "removableDevices",
]

API_ENDPOINTS = {
    "login": "/login.html",
    "remove_reputation": "/rest/classification/update",
    "visualsearch": "rest/visualsearch/query/simple",
    "get_files": "/rest/visualsearch/query/simple",
    "prevent_file": "/rest/classification/update",
    "download_classification": "rest/classification/download",
    "get_single_malop": "/rest/detection/details",
    "add_comment": "/rest/crimes/comment/{malop_guid}",
    "unprevent_file": "/rest/classification/update",
    "malop_status_update": "/rest/crimes/status",
    "isolate_machine": "rest/monitor/global/commands/isolate",
    "unisolate_machine": "rest/monitor/global/commands/un-isolate",
    "set_reputation": "/rest/classification/update",
    "detection_inbox": "rest/detection/inbox",
    "get_malop_details": "rest/crimes/unified",
    "execute_query": "/rest/visualsearch/query/simple",
    "get_sensor_details": "/rest/sensors/query",
    "get_remediation_processes": "/rest/detection/custom-remediation",
    "remediate_malop": "/rest/detection/remediate-custom-actions",
    "remediate_status": (
        "/rest/remediate/progress/{username}/{malop_id}/{remediation_id}"
    ),
}

API_ENDPOINTS_WHIT_ROOT = {
    EntityTypes.FILEHASH: "/rest/classification_v1/file_batch",
    EntityTypes.URL: "/rest/classification_v1/domain_batch",
    EntityTypes.ADDRESS: "/rest/classification_v1/ip_batch",
}

HASH_FILTER = {
    SHA1: {"facetName": "sha1String", "values": [], "filterType": "ContainsIgnoreCase"},
    MD5: {"facetName": "md5String", "values": [], "filterType": "ContainsIgnoreCase"},
}

ENTITY_QUERY = {
    SHA1: {"requestData": [{"requestKey": {"sha1": " "}}]},
    MD5: {"requestData": [{"requestKey": {"md5": " "}}]},
    EntityTypes.URL: {"requestData": [{"requestKey": {"domain": " "}}]},
    EntityTypes.ADDRESS: {"requestData": [{"requestKey": {"ipAddress": " "}}]},
}

CLASSIFICATION_FILTER_CONTAINS = "Contains"

CA_CERTIFICATE_FILE_PATH: str = "cert.cer"


class CybereasonManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        verify_ssl=False,
        ca_certificate_b64=None,
        logger=None,
        force_check_connectivity=False,
    ):
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.username = username
        self.logger = logger
        self.parser = CybereasonParser()
        self.all_classifications = None

        self._verify_certificate_file(ca_certificate_b64)
        self.login(username, password)

        if force_check_connectivity:
            self.test_connectivity()

    def login(self, username, password):
        """
        Fetch authentication token for Devices payloads.
        :param username: {string} The user to login with
        :param password: {string} The password to login with
        """
        payload = {"username": username, "password": password}
        response = self.session.post(self._get_full_url("login"), data=payload)

        self.validate_response(response, "Failed to login to the Cybereason")

    def _verify_certificate_file(self, ca_certificate_b64: str | None) -> None:
        """Verifies and sets up the CA certificate file for SSL verification.
        Args:
            ca_certificate_b64: The CA certificate content encoded in base64.
        """
        if ca_certificate_b64 and self.session.verify:
            self._save_certificate_file(ca_certificate_b64)
            self.session.verify = CA_CERTIFICATE_FILE_PATH

    def _save_certificate_file(self, ca_certificate_b64: str | None) -> None:
        """
        Decodes and saves the base64 encoded CA certificate to a file.

        Args:
            ca_certificate_b64: The CA certificate content encoded in base64.

        Raises:
            CybereasonCertificateError: If there is an error during decoding or
                saving the certificate file.
        """
        try:
            file_content = base64.b64decode(ca_certificate_b64)
            with open(CA_CERTIFICATE_FILE_PATH, "wb") as f:
                f.write(file_content)

        except (TypeError, binascii.Error, UnicodeDecodeError, OSError, IOError) as e:
            raise CybereasonCertificateError(
                "Certificate Error: Failed to process the certificate file. "
                f"Error: {e}"
            ) from e

    def _get_full_url(self, url_id, api_root=None, **kwargs):
        """
        Get full url for session.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        if api_root:
            return urljoin(api_root, API_ENDPOINTS_WHIT_ROOT[url_id].format(**kwargs))
        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to CrowdFalcon.
        :return: {bool} True if successful, exception otherwise.
        """
        query_path = [
            {"requestedType": "MalopProcess", "filters": [], "isResult": True}
        ]

        query = self.construct_query(
            MALOPS_FIELDS, query_path, template_context="MALOP", limit=1
        )
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        try:
            self.validate_response(
                response,
                error_msg="Unable to list malops",
                check_with_key="data",
                validate_json_response=True,
            )
        except Exception as e:
            raise CybereasonManagerError(
                f"Failed to connect to the {INTEGRATION_NAME} server! "
                f"Error is related to invalid credentials."
            ) from e
        return True

    def load_classifications(self):
        """
        Load classifications
        :return: {dict} Dict of classifications if with_reputation is False else return {list} of classifications.
        """
        if self.all_classifications is None:
            import csv

            self.all_classifications = {}
            try:
                raw_csv_data = self.session.get(
                    self._get_full_url("download_classification")
                ).text
                classifications = list(
                    csv.reader(raw_csv_data.split("\n"), delimiter=",")
                )
                keys = classifications[0]
                for classification in classifications[1:]:
                    if classification and len(classification) > 0:
                        self.all_classifications[classification[0]] = True
                        current_classification = {}
                        for i in range(5):
                            try:
                                current_classification[keys[i]] = classification[i]
                            except Exception as e:
                                if self.logger:
                                    self.logger.error(
                                        f"{classification[0]} don't have {keys[i]} value"
                                    )
                                continue
                            if current_classification:
                                self.all_classifications[classification[0]] = (
                                    current_classification
                                )

            except Exception as e:
                self.add_to_log(f"Error is: {e}")

        return self.all_classifications

    def search_for_entity(self, identifier):
        """
        Search for entity to see if it exists in Cybereason or not
        :param identifier: {str} Entity identifier to search
        :return: {bool} True if exists
        """
        return self.load_classifications().get(identifier, False)

    def get_machine_guid_by_name_or_fqdn(self, machine_identifier, exact_match=True):
        """
        Get machine's GUID by the searching by ElementName or FQDN
        :param machine_identifier: {str} The machine identifier to search for
        :param exact_match: {bool} Whether to search for exact match to the identifier or "contains"
        :return: {str} The GUID of the machine if found, exception otherwise.
        """
        try:
            self.add_to_log("Looking for machine guid by Element Name")
            return self.get_machine_guid_by_name(machine_identifier, exact_match)

        except CybereasonManagerNotFoundError:
            self.add_to_log(f"Machine with name {machine_identifier} was not found.")

            try:
                self.add_to_log("Looking for machine guid by FQDN")
                return self.get_machine_guid_by_fqdn(machine_identifier)

            except CybereasonManagerNotFoundError:
                raise CybereasonManagerNotFoundError(
                    f"Machine guid was not found neither by Element Name nor by FQDN for value {machine_identifier}"
                )

    def get_machine_pylum_id_by_name(self, machine_identifier, exact_match=True):
        """
        Get machine by the searching by ElementName
        :param machine_identifier: {str} The machine identifier to search for
        :param exact_match: {bool} Whether to search for exact match to the identifier or "contains"
        :return: {MachineObject} The machine if found, exception otherwise.
        """
        query_path = [
            {
                "requestedType": MACHINE_TEMPLATE_CONTEXT,
                "filters": [
                    {
                        "facetName": "elementDisplayName",
                        "values": [machine_identifier],
                        "filterType": "Equals" if exact_match else "ContainsIgnoreCase",
                    }
                ],
                "isResult": True,
            }
        ]
        custom_fields = ["pylumId", "isIsolated"]

        query = self.construct_query(
            custom_fields=custom_fields, path=query_path, limit=1
        )
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"Unable to get machine by name {machine_identifier}",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )

        return self.parser.build_siemplify_machine_object(response.json())

    def get_machines_by_names(self, machine_identifier):
        """
        Get machine by the searching by ElementName
        :param machine_identifier: {str} The machine identifiers to search for
        :return: {MachineObject} The machine if found, exception otherwise.
        """
        query_path = [
            {
                "requestedType": MACHINE_TEMPLATE_CONTEXT,
                "filters": [
                    {
                        "facetName": "elementDisplayName",
                        "values": [machine_identifier],
                        "filterType": "Equals",
                    }
                ],
                "isResult": True,
            }
        ]
        query = self.construct_query(custom_fields=MACHINE_FIELDS, path=query_path)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"Unable to get machines by name {machine_identifier}",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )

        return self.parser.build_siemplify_machine_object(response.json())

    def get_machine_pylum_id_by_fqdn(self, machine_identifier, exact_match=True):
        """
        Get machine by the searching by FQDN
        :param machine_identifier: {str} The machine identifier to search for
        :param exact_match: {bool} Whether to search for exact match to the identifier or "contains"
        :return: {MachineObject} The machine if found, exception otherwise.
        """
        query_path = [
            {
                "requestedType": MACHINE_TEMPLATE_CONTEXT,
                "filters": [
                    {
                        "facetName": "adDNSHostName",
                        "values": [machine_identifier],
                        "filterType": "Equals" if exact_match else "ContainsIgnoreCase",
                    }
                ],
                "isResult": True,
            }
        ]
        custom_fields = ["pylumId", "isIsolated"]

        query = self.construct_query(
            custom_fields=custom_fields, path=query_path, limit=1
        )
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"Unable to get machine by fqdn {machine_identifier}",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )

        return self.parser.build_siemplify_machine_object(response.json())

    def get_machine_guid_by_name(self, machine_name, exact_match=True):
        """
        Get machine's PylumID by the searching by ElementName
        :param machine_name: {str} The machine identifier to search for
        :param exact_match: {bool} Whether to search for exact match to the identifier or "contains"
        :return: {str} The GUID of the machine if found, exception otherwise.
        """
        query_path = [
            {
                "requestedType": "Machine",
                "filters": [
                    {
                        "facetName": "elementDisplayName",
                        "values": [machine_name],
                        "filterType": "Equals" if exact_match else "ContainsIgnoreCase",
                    }
                ],
                "isResult": True,
            }
        ]

        query = self.construct_query(["pylumId"], query_path, limit=1)

        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response, f"Unable to get machine by name {machine_name}"
        )
        data = self.parser.get_result_id_to_element_data_map(response.json())

        if not data:
            raise CybereasonManagerNotFoundError(
                f"No machines found with name {machine_name}"
            )

        return list(data.keys())[0]

    def get_machine_guid_by_fqdn(self, fqdn, exact_match=True):
        """
        Get machine's PylumID by the searching by FQDN
        :param machine_identifier: {str} The machine identifier to search for
        :param exact_match: {bool} Whether to search for exact match to the identifier or "contains"
        :return: {str} The GUID of the machine if found, exception otherwise.
        """

        query_path = [
            {
                "requestedType": "Machine",
                "filters": [
                    {
                        "facetName": "adDNSHostName",
                        "values": [fqdn],
                        "filterType": "Equals" if exact_match else "ContainsIgnoreCase",
                    }
                ],
                "isResult": True,
            }
        ]

        query = self.construct_query(["pylumId"], query_path, limit=1)

        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(response, f"Unable to get machine by fqdn {fqdn}")

        data = self.parser.get_result_id_to_element_data_map(response.json())

        if not data:
            raise CybereasonManagerNotFoundError(f"No machines found with fqdn {fqdn}")

        return list(data.keys())[0]

    def isolate_machine(self, machine_pylum_id):
        """
        Isolate a machine
        :param machine_pylum_id: {str} The PylumID of the machine to isolate
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"pylumIds": [machine_pylum_id]}

        response = self.session.post(
            self._get_full_url("isolate_machine"), json=payload
        )
        self.validate_response(
            response, f"Unable to isolate machine {machine_pylum_id}"
        )

        status = self.parser.get_machine_update_status(
            response.json(), machine_pylum_id
        )
        if status.lower() not in SUCCESS:
            raise CybereasonManagerIsolationError(
                f"Isolation of machine {machine_pylum_id} failed.", status
            )

        return True

    def unisolate_machine(self, machine_pylum_id):
        """
        Unisolate a machine
        :param machine_pylum_id: {str} The PylumID of the machine to unisolate
        :return: {bool} True if successful, exception otherwise
        """
        payload = {"pylumIds": [machine_pylum_id]}

        response = self.session.post(
            self._get_full_url("unisolate_machine"), json=payload
        )
        self.validate_response(
            response, f"Unable to unisolate machine {machine_pylum_id}"
        )

        status = self.parser.get_machine_update_status(
            response.json(), machine_pylum_id
        )
        if status.lower() not in SUCCESS:
            raise CybereasonManagerIsolationError(
                f"Unisolation of machine {machine_pylum_id} failed.", status
            )

        return True

    def add_malop_comment(self, malop_guid, comment):
        """
        Add a comment to a given malop
        :param malop_guid: {str} The GUID of the malop to add the comment to
        :param comment: {str} The content of the comment to add
        :return: {bool} True if successful, exception otherwise
        """
        response = self.session.post(
            self._get_full_url("add_comment", malop_guid=malop_guid), data=comment
        )
        self.validate_response(response, f"Unable to add comment to malop {malop_guid}")

        return True

    def get_processes(
        self,
        machine_name=None,
        process_name=None,
        only_suspicious=False,
        has_incoming_connection=False,
        has_outgoing_connection=False,
        has_external_connection=False,
        unsigned_unknown_reputation=False,
        from_temporary_folder=False,
        privileges_escalation=False,
        malicious_psexec=False,
        limit=None,
    ):
        """
        List processes
        :param machine_name: {str} Filter by machine name that runs the process
        :param process_name: {str} Filter by process name
        :param only_suspicious: {bool} Fetch only processes with suspicions
        :param has_incoming_connection: {bool} Fetch only processes with incoming connection
        :param has_outgoing_connection: {bool} Fetch only processes with outgoing connection
        :param has_external_connection: {bool} Fetch only processes with external connection
        :param unsigned_unknown_reputation: {bool} Fetch only unsigned processes or with unknown reputation
        :param from_temporary_folder: {bool} Fetch only processes that ran from temporary folders
        :param privileges_escalation: {bool} Fetch only processes that were identified elevating their privileges
        :param malicious_psexec: {bool} Fetch only processes that were executed by PsExec and are suspicious as being executed maliciously
        :param limit: {int} The max number of results to fetch
        :return: {[Process]} The found processes
        """
        machine_filters = []
        process_filters = []

        if machine_name:
            machine_filters.append(
                {
                    "facetName": "elementDisplayName",
                    "values": machine_name,
                    "filterType": "Equals",
                }
            )

        if process_name:
            process_filters.append(
                {
                    "facetName": "elementDisplayName",
                    "values": process_name,
                    "filterType": "Equals",
                }
            )

        if only_suspicious:
            process_filters.append(
                {"facetName": "hasSuspicions", "values": [True], "filterType": "Equals"}
            )

        if has_incoming_connection:
            process_filters.append(
                {
                    "facetName": "hasIncomingConnection",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if has_outgoing_connection:
            process_filters.append(
                {
                    "facetName": "hasOutgoingConnection",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if has_external_connection:
            process_filters.append(
                {
                    "facetName": "hasExternalConnection",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if unsigned_unknown_reputation:
            process_filters.append(
                {
                    "facetName": "unknownUnsignedEvidence",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if from_temporary_folder:
            process_filters.append(
                {
                    "facetName": "runningFromTempEvidence",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if privileges_escalation:
            process_filters.append(
                {
                    "facetName": "privilegeEscalationSuspicion",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if malicious_psexec:
            process_filters.append(
                {
                    "facetName": "executedByPsexecSuspicion",
                    "values": [True],
                    "filterType": "Equals",
                }
            )

        if machine_name:
            query_path = [
                {
                    "requestedType": "Machine",
                    "filters": machine_filters,
                    "connectionFeature": {
                        "elementInstanceType": "Machine",
                        "featureName": "processes",
                    },
                },
                {
                    "requestedType": "Process",
                    "filters": process_filters,
                    "isResult": True,
                },
            ]

        else:
            query_path = [
                {
                    "requestedType": "Process",
                    "filters": process_filters,
                    "isResult": True,
                }
            ]

        query = self.construct_query(PROCESS_FIELDS, query_path, limit=limit)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(response, "Unable to list processes")
        data = self.parser.get_result_id_to_element_data_map(response.json())

        return [
            self.parser.build_siemplify_process_obj(process_guid, process_data)
            for process_guid, process_data in data.items()
        ]

    def get_malop_processes(self, malop_guid, limit=None):
        """
        Get the processes of a given malop
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The max number of results to fetch
        :return: {[Process]} List of found processes
        """

        query_path = [
            {
                "requestedType": "MalopProcess",
                "guidList": [malop_guid],
                "filters": [],
                "connectionFeature": {
                    "elementInstanceType": "MalopProcess",
                    "featureName": "suspects",
                },
            },
            {"requestedType": "Process", "filters": [], "isResult": True},
        ]

        query = self.construct_query(PROCESS_FIELDS, query_path, limit=limit)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )
        data = self.parser.get_result_id_to_element_data_map(response.json())

        return [
            self.parser.build_siemplify_process_obj(process_guid, process_data)
            for process_guid, process_data in data.items()
        ]

    def get_malop_machines(self, malop_guid, limit=None):
        """
        Get the affected machines of a given malop
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The max number of results to fetch
        :return: {[Machine]} List of found machines
        """
        query_path = [
            {
                "requestedType": "MalopProcess",
                "guidList": [malop_guid],
                "filters": [],
                "connectionFeature": {
                    "elementInstanceType": "MalopProcess",
                    "featureName": "affectedMachines",
                },
            },
            {"requestedType": "Machine", "filters": [], "isResult": True},
        ]

        query = self.construct_query(MACHINE_FIELDS, query_path, limit=limit)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )
        data = self.parser.get_result_id_to_element_data_map(response.json())

        return [
            self.parser.build_siemplify_machine_obj(machine_guid, machine_data)
            for machine_guid, machine_data in data.items()
        ]

    def get_malop_machines_or_raise(self, malop_guid, limit=None):
        """
        Get the affected machines of a given malop
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The max number of results to fetch
        :return: {[Machine]} List of found machines
        """
        try:
            machines = []
            all_machines_for_malop = self.get_single_malop_machines(
                malop_guid=malop_guid, limit=limit
            )
            display_names = [machine.element_name for machine in all_machines_for_malop]

            for display_name in display_names:
                machines.append(self.get_machines_by_names(display_name))

            return machines
        except:
            # API return one more machine in case of limit=limit so we need to send limit-1
            return self.get_malop_machines(malop_guid=malop_guid, limit=limit - 1)

    def get_single_malop_machines(self, malop_guid, limit=None):
        """
        Get the machines of a given malop
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The limit
        :return: {MalopProcess} The found malop info
        """
        payload = {"malopGuid": malop_guid}
        response = self.session.post(
            self._get_full_url("get_single_malop"), json=payload
        )
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            custom_error=True,
            validate_json_response=True,
        )
        data = self.parser.get_machines(response.json())

        return [
            self.parser.build_siemplify_single_malop_machine_object(machine)
            for machine in data[:limit]
        ]

    def get_files(self, file_hash=None, limit=None, fields_to_return=None):
        """
        List files
        :param file_hash: {str} File hash to filter by
        :param limit: {int} Max number of results to fetch
        :param fields_to_return: {list} fields to return
        :return: {[File]} The found files
        """

        query_path = [
            {
                "requestedType": "File",
                "filters": self.bulid_filter_for_hash(file_hash) if file_hash else [],
                "isResult": True,
            }
        ]

        query = self.construct_query(
            fields_to_return or FILE_FIELDS, query_path, limit=limit
        )
        response = self.session.post(self._get_full_url("get_files"), json=query)
        self.validate_response(response, "Unable to list files")

        return self.parser.build_siemplify_obj(response.json())

    def get_malop_or_raise(self, malop_guid):
        """
        Get information about a malop
        :param malop_guid: {str} The GUID of the malop
        :return: The found malop info
        """
        try:
            return self.get_single_malop(malop_guid=malop_guid)
        except:
            return self.get_malop_with_visual_search(malop_guid=malop_guid)

    def get_malop_with_visual_search(self, malop_guid):
        """
        Get information about a malop
        :param malop_guid: {str} The GUID of the malop
        :return: {MalopProcess} The found malop info
        """
        query_path = [
            {
                "requestedType": "MalopProcess",
                "filters": [],
                "isResult": True,
                "guidList": [malop_guid],
            }
        ]

        query = self.construct_query(
            MALOPS_FIELDS, query_path, template_context=MALOP_TEMPLATE_CONTEXT
        )
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            check_with_key="data",
            check_sub_key="resultIdToElementDataMap",
            custom_error=True,
            validate_json_response=True,
        )

        return self.parser.build_siemplify_malop_obj(response.json())

    def get_single_malop(self, malop_guid):
        """
        Get information about a malop with malop_guid
        :param malop_guid: {str} The GUID of the malop
        :return: {MalopProcess} The found malop info
        """
        payload = {"malopGuid": malop_guid}
        response = self.session.post(
            self._get_full_url("get_single_malop"), json=payload
        )
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            custom_error=True,
            validate_json_response=True,
        )

        return self.parser.build_siemplify_single_malop_object(response.json())

    def get_machine(self, machine_guid):
        """
        Get a machine by its GUID
        :param machine_guid: {str} The GUID of the machine to fetch
        :return: {Machine} The machine
        """

        query_path = [
            {
                "requestedType": "Machine",
                "filters": [],
                "isResult": True,
                "guidList": [machine_guid],
            }
        ]

        query = self.construct_query(MACHINE_FIELDS, query_path)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(response, f"Unable to get machine {machine_guid}")
        data = self.parser.get_result_id_to_element_data_map(response.json())

        if not data:
            raise CybereasonManagerNotFoundError(
                f"Machine {machine_guid} was not found."
            )

        return self.parser.build_siemplify_machine_obj(
            list(data.keys())[0], list(data.values())[0]
        )

    def is_probe_connected(self, machine_name):
        """
        Check whether a machine is connected and active
        :param machine_name: {str} The machine name
        :return: {bool} True if active and connected, False otherwise
        """
        query_path = [
            {
                "requestedType": "Machine",
                "filters": [
                    {
                        "facetName": "elementDisplayName",
                        "filterType": "Equals",
                        "values": [machine_name],
                    },
                    {"facetName": "isActiveProbeConnected", "values": [True]},
                ],
                "isResult": True,
            }
        ]

        query = self.construct_query(["elementDisplayName"], query_path)
        response = self.session.post(self._get_full_url("visualsearch"), json=query)
        self.validate_response(response, "Unable to list malops")
        return self.parser.get_result_id_to_element_data_map(response.json())

    def update_malop_status(self, malop_guid, status):
        """
        Update the status of a malop
        :param malop_guid: {str} The GUID of the malop to update
        :param status: {str} The status to update to. Must be one of STATUSES
        :return: {bool} True if successful, exception otherwise
        """
        payload = {malop_guid: STATUSES[status]}
        response = self.session.post(
            self._get_full_url("malop_status_update"), json=payload
        )
        self.validate_response(response)
        status = self.parser.get_responsne_status(response.json())

        if status.lower() not in SUCCESS:
            raise CybereasonManagerError(f"Updating malop {malop_guid} failed.")

        return True

    def prevent_file(self, file_hash):
        """
        Prevent a file
        :param file_hash: {str} The file hash of the file to prevent
        :return: {bool} True if successful, exception otherwise
        """
        payload = [
            {
                "keys": [file_hash],
                "maliciousType": "blacklist",
                "remove": False,
                "prevent": True,
            }
        ]

        response = self.session.post(self._get_full_url("prevent_file"), json=payload)
        self.validate_response(response, f"Unable to prevent file hash {file_hash}")
        outcome = self.parser.get_outcome_value(raw_data=response.json())
        if outcome.lower() not in SUCCESS:
            raise CybereasonManagerError(
                f"Preventing file hash {file_hash} failed. Reason: {outcome}"
            )

        return True

    def unprevent_file(self, file_hash):
        """
        Unrevent a file
        :param file_hash: {str} The file hash of the file to unprevent
        :return: {bool} True if successful, exception otherwise
        """
        payload = [{"keys": [file_hash], "remove": True, "prevent": False}]

        response = self.session.post(
            self._get_full_url("remove_reputation"), json=payload
        )
        self.validate_response(response, f"Unable to allow file hash {file_hash}")
        outcome = self.parser.get_outcome_value(raw_data=response.json())
        if outcome.lower() not in SUCCESS:
            raise CybereasonManagerError(
                f"Allowing file hash {file_hash} failed. Reason: {outcome}"
            )

        return True

    def set_custom_reputation(self, entity_identifier, whitelist=True):
        """
        Set custom reputation (whitelist / blacklist) to a file
        :param entity_identifier: {str} entity identifier
        :param whitelist: {bool} If true, the file will be added to whitelist, otherwise it will be added to blacklist.
        :return: {bool} True if successful, exception otherwise
        """

        payload = [
            {
                "keys": [entity_identifier],
                "maliciousType": "whitelist" if whitelist else "blacklist",
                "remove": False,
                "prevent": False,
            }
        ]

        response = self.session.post(self._get_full_url("set_reputation"), json=payload)
        self.validate_response(
            response, f"Unable to remove reputation of entity {entity_identifier}"
        )
        outcome = self.parser.get_outcome_value(raw_data=response.json())
        if outcome.lower() not in SUCCESS:
            raise CybereasonManagerError(
                f"Setting reputation of entity {entity_identifier} failed. Reason: {outcome}"
            )

        return True

    def remove_custom_reputation(self, entity_identifier):
        """
        Clear the custom reputation of a file
        :param entity_identifier: {str} entity identifier
        :return: {bool} True if successful, exception otherwise
        """
        payload = [{"keys": [entity_identifier], "remove": True, "prevent": False}]

        response = self.session.post(
            self._get_full_url("remove_reputation"), json=payload
        )
        self.validate_response(
            response, f"Unable to remove reputation of entity {entity_identifier}"
        )
        outcome = self.parser.get_outcome_value(raw_data=response.json())
        if outcome.lower() not in SUCCESS:
            raise CybereasonManagerError(
                f"Removal of reputation of file hash {entity_identifier} failed. Reason: {outcome}"
            )

        return True

    def get_remediation_status(self, malop_id: str, remediation_id: str) -> dict:
        """Get remediation status of a file with malop id and remediation id.

        Args:
            malop_id: {str} the guid of the malop on which the remediation is running
            remediation_id: {str} The id of the remediation task
        Returns:
            dict: {dict} The remediaion task status.
        """
        params = {
            "username": self.username,
            "malop_id": malop_id,
            "remediation_id": remediation_id,
        }
        response = self.session.get(self._get_full_url("remediate_status", **params))
        self.validate_response(
            response, f"Unable get status for remediation {remediation_id}"
        )

        return response.json()

    def get_sensor_details(self, identifier, field_name):
        """
        Get sensor details.
        :param identifier: {str} The entity identifier to search with.
        :param field_name: {str} The name of the field to search by.
        :return: {Sensor}
        """
        payload = {
            "limit": "100",
            "sortDirection": "ASC",
            "filters": [
                {"fieldName": field_name, "operator": "Equals", "values": [identifier]},
                {
                    "fieldName": "status",
                    "operator": "NotEquals",
                    "values": ["Archived"],
                },
            ],
        }
        response = self.session.post(
            self._get_full_url("get_sensor_details"), json=payload
        )
        self.validate_response(response, "Unable to get sensor details")

        return self.parser.build_siemplify_sensor_obj(result=response.json())

    def get_malops_inbox_alerts(self, start_time, end_time):
        """
        Fetch alerts.
        :param start_time: {str} The datetime from where to fetch incidents.
        :param end_time: {str} The datetime to where to fetch incidents.
        :return: {list} List of Alert objects.
        """
        payload = {
            "startTime": convert_datetime_to_unix_time(start_time),
            "endTime": convert_datetime_to_unix_time(end_time),
        }
        response = self.session.post(
            self._get_full_url("detection_inbox"), json=payload
        )
        self.validate_response(response, "Unable to get alerts")

        return self.parser.build_all_alerts(raw_json=response.json())

    def get_malop_details(self, malop_guid, requested_type):
        """
        Get malop events.
        :param malop_guid: {str} The id of malop.
        :param requested_type: {str} The type of events to fetch.
        :return: {list} List of Malop events.
        """
        payload = {
            "totalResultLimit": 10,
            "perGroupLimit": DEFAULT_RESULTS_LIMIT,
            "perFeatureLimit": 100,
            "templateContext": OVERVIEW_TEMPLATE_CONTEXT,
            "queryPath": [
                {
                    "requestedType": requested_type,
                    "guidList": [malop_guid],
                    "result": True,
                    "filters": None,
                }
            ],
        }
        response = self.session.post(
            self._get_full_url("get_malop_details"), json=payload
        )
        self.validate_response(response, "Unable to get malop details")

        return self.parser.build_malop_details_list(
            raw_data=response.json(), malop_guid=malop_guid
        )

    def get_malop_details_for_events(self, malop_guid):
        """
        Get all types of malop events.
        :param malop_guid: {str} The id of malop.
        :return: {list} List of Malop events
        """
        malop_events = self.get_malop_detection_details(malop_guid=malop_guid)

        if malop_events:
            return malop_events, MALOP_TYPE

        return (
            self.get_malop_details(
                malop_guid=malop_guid, requested_type=MALOP_PROCESS_TYPE
            ),
            MALOP_PROCESS_TYPE,
        )

    def get_malop_detection_details(self, malop_guid):
        """
        Get all types of malop events.
        :param malop_guid: {str} The id of malop.
        :return: {list} List of Malop events
        """
        try:
            return (self.get_single_malop(malop_guid=malop_guid),)
        except:
            return []

    def validate_response(
        self,
        response,
        error_msg="An error occurred",
        check_with_key=None,
        check_sub_key=None,
        validate_json_response=False,
        custom_error=False,
        check_success_with_failure=False,
        catch_client_error=False,
    ):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        :param validate_json_response: {bool} If True exception will be raised if response is not json
        :param check_with_key: {str} Key to
        :param check_sub_key: {str} checking additional key for api response
        :param custom_error: {str} if custom error print only error_msg
        :param check_success_with_failure: {bool} check if request is successful but with status Failure
        :param catch_client_error: {bool} if client error should be caught
        """
        try:
            response.raise_for_status()
            if check_with_key:
                try:
                    if not response.json().get(check_with_key):
                        raise CybereasonManagerError(
                            f"Key {check_with_key} is missing in the json"
                        )
                    if check_sub_key:
                        if not response.json().get(check_with_key).get(check_sub_key):
                            raise CybereasonManagerError
                except:
                    if validate_json_response:
                        if custom_error:
                            raise CybereasonManagerNotFoundError(f"{error_msg}")
                        raise CybereasonManagerError(
                            f"Response is not valid json. Response is: {response.content}"
                        )

            if (
                check_success_with_failure
                and response.json().get("status") == FAILURE_STATUS
            ):
                raise CybereasonSuccessWithFailureError

        except requests.HTTPError as error:
            if catch_client_error and response.status_code == 400:
                raise CybereasonClientError

            try:
                response.json()
            except Exception:
                if custom_error:
                    raise CybereasonManagerError(f"{error_msg}")
                raise CybereasonManagerError(f"{error_msg}: {error} {response.content}")

            raise CybereasonManagerError(
                f"{error_msg}: {error} "
                f"{response.json().get('result') or response.content}"
            )

    @staticmethod
    def construct_query(
        custom_fields,
        path,
        template_context=DEFAULT_TEMPLATE_CONTEXT,
        limit=None,
        group_limit=None,
    ):
        """
        Construct a query
        :param custom_fields: {list} The fields to fetch
        :param path: {list} The query path
        :param template_context: {str} The template context of the query
        :param limit: {int} Max number of results to fetch
        :return: {dict} The constructed query
        """
        return {
            "customFields": custom_fields,
            "perFeatureLimit": DEFAULT_PER_FEATURE_LIMIT,
            "perGroupLimit": (
                group_limit if group_limit else limit or DEFAULT_PER_GROUP_LIMIT
            ),
            "queryPath": path,
            "queryTimeout": DEFAULT_QUERY_TIMEOUT,
            "templateContext": template_context,
            "totalResultLimit": limit or DEFAULT_RESULTS_LIMIT,
        }

    def bulid_filter_for_hash(self, file_hash):
        """
        Files hash filter
        :param file_hash: {str} File hash to filter by
        :return: {list} filters
        """
        hash_type = get_hash_type(file_hash)
        filters = HASH_FILTER.get(hash_type, {})
        filters["values"] = [file_hash]

        return [filters]

    def add_to_log(self, message):
        """
        Add Log for with specific message
        :param message: {str} Log message
        """
        if self.logger:
            self.logger.info(message)

    def get_reputation_list(self, filter_logic=None, filter_value=None, limit=None):
        """
        Get Reputation list
        :param filter_logic: {str} Filter logic. Can be equal or contains
        :param filter_value: {str} value to filter by
        :param limit: {int}  limit the result
        :return:{list} Reputation obj.
        """
        self.load_classifications()
        filtered_classifications = (
            list(self.all_classifications.values())
            if not filter_value
            else self.pass_classifications_filter(
                filter_logic=filter_logic, filter_value=filter_value
            )
        )[:limit]
        return [
            self.parser.build_siemplify_reputation_obj(result)
            for result in filtered_classifications
        ]

    def pass_classifications_filter(self, filter_logic, filter_value):
        """
        Filter classification by filter_value with equal logic
        :param filter_logic: {str} Filter logic. Can be equal or contains
        :param filter_value: {str} value to filter by
        :return: {list}
        """
        if filter_logic == CLASSIFICATION_FILTER_CONTAINS:
            return [
                classification
                for value, classification in self.all_classifications.items()
                if classification and filter_value in value
            ]

        return (
            [self.all_classifications.get(filter_value)]
            if self.all_classifications.get(filter_value)
            else []
        )

    def get_malop_processes_or_raise(self, malop_guid, limit):
        """
        Get malop processes
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The limit
        :return: {MalopProcess} The found malop info
        """
        try:
            return self.get_single_malop_processes(malop_guid=malop_guid, limit=limit)
        except:
            return self.get_malop_processes(malop_guid=malop_guid, limit=limit)

    def get_single_malop_processes(self, malop_guid, limit):
        """
        Get the processes of a given malop
        :param malop_guid: {str} The GUID of the malop
        :param limit: {int} The limit
        :return: {MalopProcess} The found malop info
        """
        payload = {"malopGuid": malop_guid}
        response = self.session.post(
            self._get_full_url("get_single_malop"), json=payload
        )
        self.validate_response(
            response,
            f"malop with ID {malop_guid} was not found in {INTEGRATION_NAME}.",
            custom_error=True,
            validate_json_response=True,
        )
        data = self.parser.get_process_suspects(response.json())

        return [
            self.parser.build_siemplify_single_malop_process_object(process)
            for process in data[:limit]
        ]

    def get_entity_details(self, entity_identifier, entity_type):
        query_path = self.bulid_query_for_entity(entity_identifier, entity_type)
        response = self.session.post(
            self._get_full_url(
                url_id=entity_type, api_root="https://sage.cybereason.com"
            ),
            json=query_path,
        )
        self.validate_response(response)
        data = self.parser.get_classification_responses(response.json())

        return self.parser.build_siemplify_entity_details_obj(data[0])

    def bulid_query_for_entity(self, entity_identifier, entity_type):
        if entity_type == EntityTypes.FILEHASH:
            hash_type = get_hash_type(entity_identifier)
            query = ENTITY_QUERY.get(hash_type, {})
        else:
            query = ENTITY_QUERY.get(entity_type, {})
        for key in (query.get("requestData")[0].get("requestKey")).keys():
            query.get("requestData")[0].get("requestKey")[key] = entity_identifier
        return query if query else {}

    def execute_query(self, request_type, query_filters, fields_to_return, limit):
        """
        Execute query
        :param request_type: {str} request type for query
        :param query_filters: {str} filters for query
        :param fields_to_return: {list} list of fields that need to be returned
        :param limit: {int} limit for results
        :return: {list} list of InvestigationSearchItem object
        """
        url = self._get_full_url("execute_query")
        payload = {
            "queryPath": [
                {
                    "requestedType": REQUEST_TYPE_MAPPING.get(request_type),
                    "filters": (
                        self.build_query_filters(
                            [
                                item.strip()
                                for item in query_filters.split(QUERY_FILTER_DELIMITER)
                                if item.strip()
                            ]
                        )
                        if query_filters
                        else []
                    ),
                    "isResult": "true",
                }
            ],
            "totalResultLimit": limit,
            "perGroupLimit": 1,
            "perFeatureLimit": 100,
            "templateContext": "SPECIFIC",
            "queryTimeout": 120000,
            "customFields": fields_to_return,
        }

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, check_success_with_failure=True, catch_client_error=True
        )
        investigation_search_item_objects = (
            self.parser.build_investigation_search_item_objects(response.json())
        )

        return (
            investigation_search_item_objects[:limit]
            if len(investigation_search_item_objects) > limit
            else investigation_search_item_objects
        )

    def execute_custom_query(self, query_filters_json, fields_to_return, limit):
        """
        Execute custom query
        :param query_filters_json: {dict} filters json for query
        :param fields_to_return: {list} list of fields that need to be returned
        :param limit: {int} limit for results
        :return: {list} list of InvestigationSearchItem object
        """
        url = self._get_full_url("execute_query")
        payload = {
            "queryPath": self.build_query_path(query_filters_json),
            "totalResultLimit": limit,
            "perGroupLimit": 1,
            "perFeatureLimit": 100,
            "templateContext": "SPECIFIC",
            "queryTimeout": 120000,
            "customFields": fields_to_return,
        }

        response = self.session.post(url, json=payload)
        self.validate_response(
            response, check_success_with_failure=True, catch_client_error=True
        )
        investigation_search_item_objects = (
            self.parser.build_investigation_search_item_objects(response.json())
        )

        return (
            investigation_search_item_objects[:limit]
            if len(investigation_search_item_objects) > limit
            else investigation_search_item_objects
        )

    def build_query_path(self, query_filters_json):
        query_path = []

        for item in query_filters_json:
            if (
                not isinstance(item, dict)
                or item.get(QUERIES_KEY) is None
                or not item.get(REQUEST_TYPE_KEY)
            ):
                raise CybereasonInvalidFormatError

            filter_item = {
                "requestedType": item.get(REQUEST_TYPE_KEY),
                "filters": self.build_query_filters(item.get(QUERIES_KEY, [])),
            }

            if item.get(CONNECTION_KEY):
                filter_item["connectionFeature"] = {
                    "elementInstanceType": item.get(REQUEST_TYPE_KEY),
                    "featureName": item.get(CONNECTION_KEY),
                }
            else:
                filter_item["isResult"] = "true"

            query_path.append(filter_item)

        return query_path

    def build_query_filters(self, filters_list):
        """
        Build filters for query from provided filters list
        :param filters_list: {str} list of filters
        :return: {list} list of filters dicts
        """
        filters = []

        for filter_string in filters_list:
            filter_string = QUERY_FILTER_ITEMS_DELIMITER.join(filter_string.split())
            filter_list = filter_string.split(QUERY_FILTER_ITEMS_DELIMITER, 2)

            if len(filter_list) < QUERY_FILTER_ITEMS_REQUIRED_COUNT:
                raise CybereasonInvalidQueryError

            filed_name, operator, values = [
                item for item in filter_list if item.strip()
            ]
            values, values_type = self.prepare_filter_values(values)

            filter_item = {"facetName": filed_name, "values": values}

            if values_type is not bool:
                filter_item["filterType"] = operator
            else:
                if operator.lower() != FILTER_OPERATORS.get("equals"):
                    raise CybereasonInvalidQueryError(
                        'Boolean filter can only have "Equals" as logical operator'
                    )

            filters.append(filter_item)

        return filters

    @staticmethod
    def prepare_filter_values(values_string):
        """
        Prepare filter values
        :param values_string: {str} filter values
        :return: {tuple} list of filter values, filter values type
        """
        values = []
        values_type = str

        for value in re.split(
            QUERY_FILTER_VALUES_DELIMITER, values_string, flags=re.IGNORECASE
        ):
            value = value.strip()

            if value:
                try:
                    value = int(value)
                except Exception:
                    try:
                        value = float(value)
                    except Exception:
                        if value.lower() in ["true", "false"]:
                            value = True if value.lower() == "true" else False

                values.append(value)

        if all(isinstance(value, bool) for value in values):
            values_type = bool
        elif all(isinstance(value, int) for value in values):
            values_type = int

        return values, values_type

    def get_malop_suspicious_details(self, malop_id: str) -> list:
        """Get malop details from cybereason for all possible remediations.

        Args:
            malop_guid: {str} The id of malop.

        Returns:
            list: {list} List of MalopSuspeciousDetails objects.
        """
        payload = {
            "detectionEventMalopGuids": [malop_id],
            "processMalopGuids": [malop_id],
        }
        response = self.session.post(
            self._get_full_url("get_remediation_processes"), json=payload
        )
        self.validate_response(response, "Unable to get malop details")

        return self.parser.get_malop_suspecious_process_details(
            raw_data=response.json(), malop_id=malop_id
        )

    def remediate_melop(self, remediate_data: dict[str, Any]) -> RemediateDetails:
        """Remediate Malop action call on the remediate_data.

        Args:
            remediate_data (dict): Malop ID response data for remediate.

        Returns:
            RemediateDetails: RemediateDetails datamodel object.
        """
        payload = [remediate_data]

        response = self.session.post(
            self._get_full_url("remediate_malop"), json=payload
        )
        self.validate_response(response, "Unable to get remediate details.")

        return self.parser.build_remediate_object(
            raw_data=response.json(),
            remediation_type=remediate_data.get("remediationType"),
        )
