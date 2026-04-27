# ==============================================================================
# title           :McAfeeWebGatewayManager.py
# description     :This Module contain all McAfeeWebGateway API functions.
# author          :zivh@siemplify.co
# date            :04-26-18
# python_version  :2.7
# libraries       :
# requirements    :
# product_version : v2.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import defusedxml.ElementTree as ET


# =====================================
#              CONSTS                #
# =====================================
API_ROOT = ""
USERNAME = ""
PASSWORD = ""

URL = "{}/Konfigurator/REST"
HEADERS = {"Content-Type": "application/xml"}
INSERT_ERROR_STATUS_CODE = 422
COOKIE_VALIDATION = "JSESSIONID"

SUBSTRING = "substring not found"
DUPLICATE = "duplicate list entry"
INVALID = "Invalid list entry"
LOGIN = "already logged in"

XML_ADD_ENTRY_PAYLOAD = """
        <entry xmlns="http://www.w3org/2011/Atom">
            <content type="application/xml">
                <listEntry>
                    <entry>{0}</entry>
                    <description>{1}</description>
                </listEntry>
            </content> 
        </entry>"""

# =====================================
#              CLASSES                #
# =====================================


class McAfeeWebGatewayManagerError(Exception):
    """
    General Exception for McAfee Web Gateway manager
    """

    pass


class McAfeeWebGatewayManager:
    def __init__(self, api_root, username, password, verify_ssl=False):
        self.api_root = api_root
        self.username = username
        self.password = password
        self.url = URL.format(self.api_root)

        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(HEADERS)
        self.session.auth = (self.username, self.password)

        # Check whether a connection was successful, failed, or if the user is already logged in
        self.login()
        self.logged_in = True

    def login(self):
        """
        Login to McAfeeWebGateway
        Check whether a connection was successful, failed, or if the user is already logged in
        :return: {json} login request response
        """
        response = self.session.post(f"{URL.format(self.api_root)}/login")
        self.validate_login(response)
        return response

    def validate_login(self, response):
        """
        Check if login to McAfeeWebGateway pass successfully
        :param response: {json} login request response
        :return: {boolean} true if login was successful
        """
        if COOKIE_VALIDATION not in response.cookies:
            raise Exception(response.text)

        try:
            response.raise_for_status()
        except Exception as e:
            if LOGIN in str(e) or LOGIN in response.content:
                return True
            raise McAfeeWebGatewayManagerError(f"Error: {e} {response.content}")
        return True

    def get_available_lists(self):
        """
        Get all lists
        :return: {list} of all entries
        """
        response = self.session.get(f"{self.url}/list")
        self.check_for_error(response)

        xm = ET.fromstring(response.content)
        entries_lists = xm.findall("entry")
        return entries_lists

    def get_list_id_by_name(self, name):
        """
        Get specific list
        :param name: {string} list full name (e.g. 'Siemplify-Blacklist')
        :return: {string} list id if found. else raise.
        """
        available_lists = self.get_available_lists()

        for entry_item in available_lists:
            if entry_item.find("title").text == name:
                return entry_item.find("id").text

        raise McAfeeWebGatewayManagerError(f"{name} was not found.")

    def logout(self):
        """
        Close the connection - sign out
        """
        if self.logged_in:
            res = self.session.post(f"{self.url}/logout")
            res.raise_for_status()
            self.logged_in = False

    def commit(self):
        """
        Saving data
        """
        response = self.session.post(f"{self.url}/commit")
        self.check_for_error(response)

    def get_list_entry_id_by_name(self, name, list_id):
        """
        Get list entry index
        :param name: {string} entry full name (e.g. '10.0.0.51/32')
        :param list_id: {string} list id
        :return: {int} if list exist, else - None
        """
        response = self.session.get(f"{self.url}/list/{list_id}")
        self.check_for_error(response)

        xm = ET.fromstring(response.content)
        list_entries = xm.findall(".//listEntry")

        for index, list_entry_item in enumerate(list_entries):
            if list_entry_item.find("entry").text == name:
                return index

    def delete_entry_from_list_by_name(self, list_name, entry_name):
        """
        Remove entry from list by entry name
        :param list_name: {string} list full name (e.g. 'Siemplify-Blacklist')
        :param entry_name: {string} entry full name (e.g. '10.0.0.51/32')
        :return: {boolean} True if delete entry from list was done.
        """
        list_id = self.get_list_id_by_name(list_name)
        return self.delete_entry_from_list_by_id(list_id, entry_name)

    def delete_entry_from_list_by_id(self, list_id, entry_name):
        """
        Remove entry from list by entry id
        :param list_id: {string} list id
        :param entry_name: {string} entry full name (e.g. '10.0.0.51/32')
        :return: {boolean} True if entry deleted, else None
        """
        entry_id = self.get_list_entry_id_by_name(entry_name, list_id)
        if entry_id is not None:
            url = f"{self.url}/list/{list_id}/entry/{entry_id}"
            response = self.session.delete(url)
            self.check_for_error(response)
            self.commit()
            return True

        return False

    def insert_entry_to_list_by_name(self, list_name, entry_name, entry_description=""):
        """
        Add entry to list by entry name
        :param list_name: {string} list full name (e.g. 'Siemplify-Blacklist')
        :param entry_name: {string} entry full name (e.g. '10.0.0.51/32')
        :param entry_description: {string} description ('Added by..')
        :return: {boolean} True if entry was added, else False
        """
        list_id = self.get_list_id_by_name(list_name)
        return self.insert_entry_to_list_by_id(list_id, entry_name, entry_description)

    def insert_entry_to_list_by_id(self, list_id, entry_name, entry_description=""):
        """
        Add entry to list by entry id
        :param list_id: {string} list id
        :param entry_name: {string} entry full name (e.g. '10.0.0.51/32')
        :param entry_description: {string} description ('Added by..')
        :return: {boolean} True if entry was added, else raise
        """
        file_content = XML_ADD_ENTRY_PAYLOAD.format(entry_name, entry_description)
        res = self.session.post(
            f"{self.url}/list/{list_id}/entry/0/insert", data=file_content
        )

        # Validate insert is done
        self.validate_entry(res)
        self.commit()
        return True

    def validate_entry(self, response):
        """
        Check if entry was added successfully to the list.
        :param response: {dict} insert entry response
        """
        try:
            response.raise_for_status()
        except Exception:
            if response.status_code == INSERT_ERROR_STATUS_CODE:
                if DUPLICATE in response.content:
                    return response.content
                elif INVALID in response.content:
                    self.logout()
                    raise McAfeeWebGatewayManagerError(
                        f"Item is not in the correct format of the list type: {response.content}"
                    )
            self.logout()
            raise McAfeeWebGatewayManagerError(f"Error: {response.content}")

    def check_for_error(self, response):
        """
        Check for error, raise if error
        :param response: {response}
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            self.logout()
            raise McAfeeWebGatewayManagerError(f"Error: {response.content}. {e}")
