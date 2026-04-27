# ==============================================================================
# title           :Cynet.py
# description     :This Module contain all Cynet functionality
# author          :zivh@siemplify.co
# date            :3-8-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import hashid

# =====================================
#             CONSTANTS               #
# =====================================
API_ROOT = "https://cynet:6443/api"

DUMMY_HASH = "7D8947AC64AAD7FBE2E5EDC232038C4BE0099423FB1B808C0C5690DAD21D0947"

# =====================================
#              CLASSES                #
# =====================================


class CynetManagerError(Exception):
    """
    General Exception for cynet manager
    """

    pass


class CynetManager:
    """
    Responsible for all Cynet operations
    """

    def __init__(self, api_root, username, password, verify_ssl=False):
        self.api_root = api_root
        self.verify = verify_ssl
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.access_token = self.get_token(username, password)
        # Add token header
        self.headers.update({"access_token": f"{self.access_token}"})

    def get_token(self, username, password):
        """
         Authenticates to the Cynet API engine using configured credentials with the API user role.
        :param username:
        :param password:
        :return: access_token
        """
        response = requests.post(
            f"{self.api_root}/account/token",
            headers=self.headers,
            json={"user_name": username, "password": password},
            verify=self.verify,
        )

        is_valid_response = self.response_validation(response)
        if is_valid_response:
            return response.json()["access_token"]

    def is_sha256(self, hash_id):
        """
        Return if type of hash is sha256
        :param hash_id: {string}
        :return: {boolean} Type of hash is sha 256 or not
        """
        hash_object = hashid.HashID()

        hash_types = hash_object.identifyHash(hash_id)
        for hash_type in hash_types:
            if "SHA-256" in hash_type.name:
                return True
        return False

    def response_validation(self, response):
        """
        Validates a response
        :param response: {requests.Response} The response to validate
        :return: {bool} True if response is ok, exception otherwise.
        """
        try:
            response.raise_for_status()
        except Exception as error:
            raise CynetManagerError(f"Error:{error} {response.text}")
        return True

    def get_hash_details(self, hash_identifier):
        """
        Retrieves all information about the specified file
        :param hash_identifier: {String} SHA256 hash
        :return: {json} hash details
        """
        request_url = f"{self.api_root}/full/file?sha256={hash_identifier}"
        response = requests.get(request_url, headers=self.headers, verify=self.verify)
        is_valid_response = self.response_validation(response)
        if is_valid_response and response.content:
            return response.json()

    def quarantine_file_remediation(self, hash_identifier, host_name):
        """
        Performs the quarantine file remediation action by specifying the file hash.
        :param hash_identifier: {string} SHA256 hash
        :param host_name: {string}
        :return: {json} remediation_items which is the id needed for remediation check by id
        """
        body_parameters = {"sha256": hash_identifier, "host": host_name}
        response = requests.post(
            self.api_root + "/file/remediation/quarantine",
            json=body_parameters,
            headers=self.headers,
            verify=self.verify,
        )
        is_valid_response = self.response_validation(response)
        if is_valid_response and response.content:
            return response.json()

    def kill_file_remediation(self, hash_identifier, host_name):
        """
        Performs the kill process file remediation action by specifying the file hash
        :param hash_identifier: {string} SHA256 hash
        :param host_name: {string}
        :return: {json} remediation_items id
        """
        body_parameters = {"sha256": hash_identifier, "host": host_name}
        response = requests.post(
            self.api_root + "/file/remediation/kill",
            json=body_parameters,
            headers=self.headers,
            verify=self.verify,
        )
        is_valid_response = self.response_validation(response)
        if is_valid_response and response.content:
            return response.json()

    def delete_file_remediation(self, hash_identifier, host_name):
        """
        Performs the delete file remediation action by specifying the file hash.
        :param hash_identifier: {string} SHA256 hash
        :param host_name: {string}
        :return: {json} remediation_items id
        """
        body_parameters = {"sha256": hash_identifier, "host": host_name}
        response = requests.post(
            self.api_root + "/file/remediation/delete",
            json=body_parameters,
            headers=self.headers,
            verify=self.verify,
        )
        is_valid_response = self.response_validation(response)
        if is_valid_response and response.content:
            return response.json()

    def get_remediation_status(self, remediation_action_id):
        """
        Retrieves the status of a requested file remediation action.
        :param remediation_action_id: {integer}
        :return: {json} remediation status including: status(Remediation action type),
        statusInfo (Remediation action result - success or not)
        """
        response = requests.get(
            self.api_root + f"/file/remediation/{remediation_action_id}",
            headers=self.headers,
            verify=self.verify,
        )
        is_valid_response = self.response_validation(response)
        if is_valid_response and response.content:
            return response.json()
