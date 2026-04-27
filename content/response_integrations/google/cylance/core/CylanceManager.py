# ============================================================================#
# title           :CylanceManager.py
# description     :This Module contain all Cylance Manager functionality.
# author          :yair@siemplify.co
# date            :03-29-2018
# python_version  :2.7
# requirements    :jwt
# api_version     : v2
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
import uuid
import jwt
from datetime import datetime, timedelta
import urllib.parse
from .constants import ENDPOINTS
from .CylanceParser import CylanceParser
from functools import reduce


# ============================= CONSTS ===================================== #
URI_AUTH = "{0}/auth/v2/token"
URI_USERS = "{0}/users/v2"
URI_DEVICES = "{0}/devices/v2"
URI_DEVICE = "{0}/devices/v2/{1}"
URI_POLICIES = "{0}/policies/v2"
URI_THREATS = "{0}/threats/v2"
URI_THREAT = "{0}/threats/v2/{1}"
URI_THREAT_DEVICES = "{0}/threats/v2/{1}/devices"
URI_GLOBAL_LIST = "{0}/globallists/v2"
URI_ZONES = "{0}/zones/v2"

PAGE_SIZE = 50
GLOBAL_LISTS = {"GlobalSafe": 1, "GlobalQuarantine": 0}

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
}
AUTHORIZATION = "Bearer {}"
ACCESS_TOKEN_TIMEOUT = 1800

SHA256 = "sha256"
MD5 = "md5"


# ============================= CLASSES ===================================== #


class CylanceManagerException(Exception):
    """
    Cylance Manager Exception
    """

    pass


class CylanceManager:
    """
    Cylance Manager
    """

    def __init__(self, server_address, app_id, app_secret, tenant_identifier):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers = HEADERS
        self.access_token = self.get_authentication_access_token(
            app_id, app_secret, tenant_identifier
        )
        self.session.headers.update(
            {"Authorization": AUTHORIZATION.format(self.access_token)}
        )
        self.parser = CylanceParser()

    def get_authentication_access_token(self, app_id, app_secret, tenant_identifier):
        """
        Gets a JWT authorization token for accessing the API
        :param app_id: {string} Used to indicate the token requested
        :param app_secret: {string} Used to sign the app_id
        :param tenant_identifier: {string} ID number of tenant information being queried
        :return: Token used to authenticate with API
        """

        # Generates the epoch time window in which the token will be valid
        timeout = ACCESS_TOKEN_TIMEOUT
        now = datetime.utcnow()
        timeout_datetime = now + timedelta(seconds=timeout)
        epoch_time = int((now - datetime(1970, 1, 1)).total_seconds())
        epoch_timeout = int((timeout_datetime - datetime(1970, 1, 1)).total_seconds())

        # Generate token ID
        jti = str(uuid.uuid4())

        claims = {
            "exp": epoch_timeout,
            "iat": epoch_time,
            "iss": "http://cylance.com",
            "sub": app_id,
            "tid": tenant_identifier,
            "jti": jti,
        }

        # Encode the token
        encoded = jwt.encode(claims, app_secret, algorithm="HS256")

        url = URI_AUTH.format(self.server_address)

        res = self.session.post(url, json={"auth_token": encoded})
        self.validate_response(res, "Unable to obtain token")

        return res.json()["access_token"]

    def get_policies(self):
        """
        Gets all policies from Cylance
        :return: {json} The found policies
        """
        res = self.session.get(
            URI_POLICIES.format(self.server_address),
            params={"page": 1, "page_size": PAGE_SIZE},
        )
        self.validate_response(res, "Unable to get policies")

        total_pages = res.json()["total_pages"]
        policies = res.json()["page_items"]

        # CR: Implement paging fetching in one method
        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_POLICIES.format(self.server_address),
                params={"page": page, "page_size": PAGE_SIZE},
            )
            self.validate_response(res, "Unable to get policies")
            policies.extend(res.json()["page_items"])

        return policies

    def get_device_by_id(self, device_id):
        """
        Gets device by id
        :param device_id: {string} Unique identifier for a device in Cylance
        :return: {json} Device information
        """
        res = self.session.get(URI_DEVICE.format(self.server_address, device_id))
        self.validate_response(res, f"Unable to get device {device_id}")
        return res.json()

    def get_device_by_name(self, device_name, is_address=False):
        """
        Translates device name into an ID and gets details about a device in Cylance
        :param device_name: {string} Device name
        :param is_address: {boolean} Whether the device name is an address
        :return: {json} Device Information
        """
        device_id = self.get_device_id(device_name, is_address)
        return self.get_device_by_id(device_id)

    def get_devices(self):
        """
        Gets all devices from Cylance
        :return: {json List} All devices with device information
        """
        res = self.session.get(
            URI_DEVICES.format(self.server_address),
            params={"page": 1, "page_size": PAGE_SIZE},
        )
        self.validate_response(res, "Unable to get devices")

        total_pages = res.json()["total_pages"]
        devices = res.json()["page_items"]

        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_DEVICES.format(self.server_address),
                params={"page": page, "page_size": PAGE_SIZE},
            )
            self.validate_response(res, "Unable to get devices")
            devices.extend(res.json()["page_items"])

        return devices

    def get_device_id(self, identifier, is_address=False):
        """
        Get device ID by name or ip address.
        :param identifier: {string} Name of the device
        :param is_address: {boolean} Whether the device name is an address
        :return: {string} Device ID Number
        """
        for device in self.get_devices():
            if is_address and identifier in device["ip_addresses"]:
                return device["id"]
            elif identifier.lower() == device["name"].lower():
                return device["id"]

        raise CylanceManagerException(f"Device {identifier} not found.")

    def change_device_policy(self, device_id, policy_name):
        """
        Assign a device policy using the ID number
        :param device_id: {string} Unique identifier for a device
        :param policy_name: {string} The name of the policu to change to
        :return: {bool} True if successful, exception otherwise.
        """
        policy_id = self.get_policy_id(policy_name)
        device_name = self.get_device_by_id(device_id)["name"]

        url = URI_DEVICE.format(self.server_address, device_id)

        res = self.session.put(url, json={"name": device_name, "policy_id": policy_id})
        self.validate_response(res, f"Unable change policy for device {device_id}")

        return True

    def change_device_zone(
        self, device_id, zone_names_to_add=None, zone_names_to_remove=None
    ):
        """
        Change the device's zone
        :param device_id: {string} The device id to change the zone of
        :param zone_names_to_add: {list} The names of the zone to add
        :param zone_names_to_remove: {list} The names of the zone to remove
        :return: {bool} True if successful, exception otherwise.
        """
        zone_ids_to_add = []
        zone_ids_to_remove = []
        device_name = self.get_device_by_id(device_id)["name"]
        policy_id = self.get_device_by_id(device_id)["policy"]["id"]

        for zone in zone_names_to_add:
            zone_id = self.get_zone_id_by_name(zone)

            if not zone_id:
                raise CylanceManagerException(f'Invalid zone name for "{zone}".')

            zone_ids_to_add.append(zone_id)

        for zone in zone_names_to_remove:
            zone_id = self.get_zone_id_by_name(zone)

            if not zone_id:
                raise CylanceManagerException(f'Invalid zone name for "{zone}".')

            zone_ids_to_remove.append(zone_id)

        url = URI_DEVICE.format(self.server_address, device_id)

        res = self.session.put(
            url,
            json={
                "name": device_name,
                "add_zone_ids": zone_ids_to_add,
                "remove_zone_ids": zone_ids_to_remove,
                "policy_id": policy_id,
            },
        )
        self.validate_response(res, f"Unable change zone for device {device_id}")

        return True

    def get_policy_id(self, policy_name):
        """
        Get policy id by its name
        :param policy_name: {string} The policy name
        :return: {str} The policy id
        """
        for policy in self.get_policies():
            if policy["name"].lower() == policy_name.lower():
                return policy["id"]

        raise CylanceManagerException(f"Policy {policy_name} not found.")

    def get_threat(self, filehash):
        """
        Gets threat by filehash
        :param filehash: SHA256 or MD5 hash of the threat
        :return: {json} The found threat
        """
        hash_type = self.get_hash_type(filehash)

        if hash_type == SHA256:
            res = self.session.get(URI_THREAT.format(self.server_address, filehash))
            self.validate_response(res, f"Unable to get threat {filehash}")

            return res.json()

        elif hash_type == MD5:
            threats = self.get_threats()
            for threat in threats:
                if filehash.lower() == threat["md5"].lower():
                    return threat

            raise CylanceManagerException(f"Threat not found for {filehash}")

        raise CylanceManagerException(
            "Unsupported hash (only sha256 or md5 are supported.)"
        )

    def get_threats(self):
        """
        Retrieves all threats from Cylance
        :return: {json} The found threats
        """
        res = self.session.get(
            URI_THREATS.format(self.server_address),
            params={"page": 1, "page_size": PAGE_SIZE},
        )
        self.validate_response(res, "Unable to get threats")

        total_pages = res.json()["total_pages"]
        threats = res.json()["page_items"]

        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_THREATS.format(self.server_address),
                params={"page": page, "page_size": PAGE_SIZE},
            )
            self.validate_response(res, "Unable to get threats")
            threats.extend(res.json()["page_items"])

        return threats

    def get_threat_devices(self, filehash):
        """
        Retrieves devices infected with the threat hash
        :param filehash: {string} SHA256 hash of the threat
        :return: {JSON} The threat devices
        """
        if self.get_hash_type(filehash) == MD5:
            raise CylanceManagerException(
                "Unsupported hash (MD5 is not supported for direct search)"
            )

        res = self.session.get(
            URI_THREAT_DEVICES.format(self.server_address, filehash),
            params={"page": 1, "page_size": PAGE_SIZE},
        )
        self.validate_response(res, "Unable to get threat's devices.")

        total_pages = res.json()["total_pages"]
        devices = res.json()["page_items"]

        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_THREATS.format(self.server_address, filehash),
                params={"page": page, "page_size": PAGE_SIZE},
            )
            self.validate_response(res, "Unable to get threat's devices.")
            devices.extend(res.json()["page_items"])

        return devices

    def get_global_list(self, list_type="GlobalSafe"):
        """
        Retrieves values in the global list indicated
        :param list_type: {string} Name of the global list
        :return: {JSON} The global list
        """
        if list_type not in GLOBAL_LISTS:
            raise CylanceManagerException(
                "List type is not a valid. Please choose from the following list:\n{1}".format(
                    list_type, "\n".join(GLOBAL_LISTS)
                )
            )

        list_type_id = GLOBAL_LISTS[list_type]

        res = self.session.get(
            URI_GLOBAL_LIST.format(self.server_address),
            params={"page": 1, "page_size": PAGE_SIZE, "listTypeId": list_type_id},
        )
        self.validate_response(res, "Unable to get threats")

        total_pages = res.json()["total_pages"]
        global_list = res.json()["page_items"]

        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_GLOBAL_LIST.format(self.server_address),
                params={
                    "page": page,
                    "page_size": PAGE_SIZE,
                    "listTypeId": list_type_id,
                },
            )
            self.validate_response(res, "Unable to get threats")

            global_list.extend(res.json()["page_items"])

        return global_list

    def add_to_global_list(
        self, filehash, list_type="GlobalSafe", category="None", reason="Default reason"
    ):
        """
        Adds hash to global list
        :param filehash: {string} The hash to add to the list - sha256.
        :param list_type: {str} The list to add the hash to
        :param category: {str} The category of the hash
        :param reason: {str} The reason for adding the hash to the list
        :return: {bool} True if successful, False if status code is 409(already exist), exception otherwise.
        """
        payload = {
            "sha256": filehash,
            "list_type": list_type,
            "category": category,
            "reason": reason,
        }

        res = self.session.post(
            URI_GLOBAL_LIST.format(self.server_address), json=payload
        )
        if res.status_code == 409:
            return False
        self.validate_response(res, f"Unable to add {filehash} to {list_type}")

        return True

    def delete_from_global_list(self, filehash, list_type="GlobalSafe"):
        """
        Delete a hash from global list
        :param filehash: {string} The hash to delete from the list - sha256.
        :param list_type: {str} The list to delete the hash from
        :return: {bool} True if successful, exception otherwise.
        """
        payload = {"sha256": filehash, "list_type": list_type}

        res = self.session.delete(
            URI_GLOBAL_LIST.format(self.server_address), json=payload
        )
        self.validate_response(res, f"Unable to delete {filehash} from {list_type}")

        return True

    def get_zones(self):
        """
        Get all zones from Cylance
        :return: {JSON} The zones
        """

        res = self.session.get(
            URI_ZONES.format(self.server_address),
            params={"page": 1, "page_size": PAGE_SIZE},
        )
        self.validate_response(res, "Unable to get threats")

        total_pages = res.json()["total_pages"]
        zones = res.json()["page_items"]

        for page in range(2, total_pages + 1):
            res = self.session.get(
                URI_ZONES.format(self.server_address),
                params={"page": page, "page_size": PAGE_SIZE},
            )
            self.validate_response(res, "Unable to get threats")
            zones.extend(res.json()["page_items"])

        return zones

    def get_zone_id_by_name(self, zone_name):
        """
        Get zone ID by name
        :param zone_name: {string} Name of the zone
        :return: {str} The zone id
        """
        for zone in self.get_zones():
            if zone_name.lower() == zone["name"].lower():
                return zone["id"]

        raise CylanceManagerException(f"Zone {zone_name} not found.")

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise CylanceManagerException(
                f"{error_msg}: {error} {error.response.content}"
            )

    @staticmethod
    def get_hash_type(filehash):
        """
        Checks whether has is MD5 or SHA256
        :param hash: {string} hash of a threat
        :return: {string} MD5 or SHA256
        """
        if len(filehash) == 32:
            return MD5
        elif len(filehash) == 64:
            return SHA256

    @staticmethod
    def construct_csv(results):
        """
        Constructs a csv from results
        :param results: The results to add to the csv (results are list of flat dicts)
        :return: {list} csv formatted list
        """
        csv_output = []
        headers = reduce(set.union, map(set, map(dict.keys, results)))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in [str(result.get(h, None)) for h in headers]
                    ]
                )
            )

        return csv_output

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {unicode} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {unicode} The full url
        """
        return urllib.parse.urljoin(
            self.server_address, ENDPOINTS[url_id].format(**kwargs)
        )

    def get_threat_download_link(self, hash):
        """
        Get the download link of a threat file by hash
        :param hash: The file hash
        :return: {DownloadLink} The DownloadLink object
        """
        url = self._get_full_url("get_threat_download_link", hash=hash)
        response = self.session.get(url)
        self.validate_response(response)
        return self.parser.build_download_link_object(response.json())
