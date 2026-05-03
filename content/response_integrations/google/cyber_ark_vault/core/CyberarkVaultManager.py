# ============================================================================#
# title           :CyberarkManager.py
# description     :This Module contain all Cyberark operations functionality
# author          :zivh@siemplify.co
# date            :06-06-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :v2
# Docs            :https://help.skytap.com/API_v2_Documentation.html#User2
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests


# ============================= CONSTS ===================================== #
CYBERARK_URL = "{0}/CyberArk/scim/v2/{1}/{2}"
# ============================= CLASSES ===================================== #


class CyberarkManagerError(Exception):
    """
    General Exception for Cyberark manager
    """

    pass


class CyberarkManager:
    """
    Cyberark Manager
    """

    def __init__(self, username, password, api_root, use_ssl=False):
        self.session = requests.Session()
        self.api_root = api_root
        self.session.verify = use_ssl
        self.session.auth = (username, password)

    def test_connectivity(self):
        """
        Test connectivity to Cyberark
        :return: {bool} True if successful, exception otherwise.
        """
        try:
            self.get_users_list()
        except Exception as e:
            raise CyberarkManagerError(str(e))
        return True

    def get_user_id(self, user_name):
        """
        Get user id
        :param user_name: {String} full user name as exist in the CyberArkVault
        :return: {string} user id
        """
        for user in self.get_users_list():
            if user["userName"] == user_name:
                return user["id"]
        raise CyberarkManagerError("User not found.")

    def get_user_details(self, user_name):
        """
        Get user details
        :param user_name: {string} full user name as exist in the CyberArkVault
        :return: {json} user information
        """
        response = self.session.get(
            CYBERARK_URL.format(self.api_root, "Users", user_name)
        )
        self.validate_response(response)
        return response.json()

    def change_user_active_status(self, user_name, user_details, active_status):
        """
        Update a user attribute - disable/enable
        :param user_name: {string}
        :param user_details: {json} user information from Cyberark
        :param active_status: {boolean} True=Enable/False=Disable
        :return: {boolean} True if user in desire activate status
        """
        # Check if active status is already set as needed
        if active_status == user_details["active"]:
            return True

        user_details["active"] = not user_details["active"]
        response = self.session.put(
            CYBERARK_URL.format(self.api_root, "Users", user_name), json=user_details
        )
        self.validate_response(response)

        return active_status == user_details["active"]

    def get_users_list(self):
        """
        Get all Cyberark users
        :return: {list} of users {dicts} or None
        """
        response = self.session.get(CYBERARK_URL.format(self.api_root, "Users", ""))
        self.validate_response(response)
        return response.json().get("Resources", [])

    def get_groups_list(self):
        """
        Get all Cyberark groups
        :return: {list} of groups {dicts} or None
        """
        response = self.session.get(CYBERARK_URL.format(self.api_root, "Groups", ""))
        self.validate_response(response)
        return response.json().get("Resources", [])

    def get_group_details(self, group_name):
        """
        Get the group details
        :param group_name: {string}
        :return: {json} group information
        """
        response = self.session.get(
            CYBERARK_URL.format(self.api_root, "Groups", group_name)
        )
        self.validate_response(response)
        return response.json()

    @staticmethod
    def validate_response(response):
        """
        Check for error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CyberarkManagerError(e)


class PasswordVaultManager:
    """
    Class manager for Password Manager vault functionality
    """

    def __init__(self, api_root, app_id, ssl_verification=False):
        self.api_root = api_root
        self.app_id = app_id
        self.session = requests.Session()
        self.session.headers = {"Content-Type": "application/json"}
        self.session.verify = ssl_verification

    def test_connectivity(self, safe, folder):
        """
        Test connection to server
        :return: {boolean}
        """
        ping_url = f"{self.api_root}/{'/AIMWebService/api/Accounts'}"
        res = self.session.get(
            ping_url,
            params={
                "AppID": self.app_id,
                "Safe": safe,
                "Folder": folder,
                "Object": "test",
            },
        )

        if res.ok or res.status_code == 404:
            # The connection is ok, and the account name was not found (as predicted)
            return True

        # An error occurred
        self.validate_response(res)

    def get_account_by_name(self, safe, folder, account_name):
        """
        GEt account object by its name (also password property is attached during the process)
        :param safe: {string} Safe of the account
        :param folder: {string} Folder of the account
        :param account_name: {string} The account name
        :return: {dict} account details
        """
        ping_url = f"{self.api_root}/{'/AIMWebService/api/Accounts'}"
        res = self.session.get(
            ping_url,
            params={
                "AppID": self.app_id,
                "Safe": safe,
                "Folder": folder,
                "Object": account_name,
            },
        )
        self.validate_response(res, f"Unable to find account with name: {account_name}")

        return res.json()

    def get_password_from_account_id(self, account_id):
        """
        Get password property from account
        :param account_id: {string}
        :return: {string} password
        """
        paaword_uri = f"PasswordVault/API/Accounts/{account_id}/Password/Retrieve"
        get_password_url = f"{self.api_root}/{paaword_uri}"
        payload = {"Reason": "Automatically retrieved password by Siemplify"}
        res = self.session.post(get_password_url, json=payload)
        self.validate_response(res)
        return res.json()

    @staticmethod
    def validate_response(response, err_msg="An error occurred"):
        """
        Check for error
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                response.json()["ErrorMsg"]
            except:
                raise CyberarkManagerError(f"{err_msg}: {str(e)}")

            raise CyberarkManagerError(f"{err_msg}: {response.json()['ErrorMsg']}")


#
