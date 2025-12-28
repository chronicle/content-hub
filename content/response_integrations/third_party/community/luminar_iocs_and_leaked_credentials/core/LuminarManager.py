"""LuminarManager"""

from __future__ import annotations

import re

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

TIMEOUT = 60.0

STIX_PARSER = re.compile(
    r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[OR|AND|FOLLOWEDBY]?",
)
SIEMPLIFY_MAPPING = {
    "file:hashes.'SHA-1'": "SHA1",
    "file:hashes.MD5": "MD5",
    "file:hashes.'SHA-256'": "SHA256",
    "file:hashes.'SHA-512'": "SHA512",
    "ipv4-addr": "IP",
    "file:name": "File_Extension",
    "file:size": "File_Size",
    "url": "URL",
    "email-addr": "EMAIL",
    "domain-name": "DOMAIN",
    "ipv6-addr": "IP",
    "mac-addr": "MAC",
    "directory": "DIR",
    "mutex": "MUTEX",
    "windows-registry-key": "WINDOWS_REGISTRY_KEY",
}


class LuminarManager:
    def __init__(self, siemplify, client_id, client_secret, account_id, base_url):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_id = account_id

        self.siemplify = siemplify
        self.client_credentials = "client_credentials"

    def test_connectivity(self):
        """Test connection with Siemplify Luminar server
        :return: return_value,output_message,status
         return_value is true if successfully connected to Luminar
            exception if failed to connect
        """
        req_url = self.base_url + "/externalApi/realm/" + self.account_id + "/token"
        req_headers = {"Content-Type": "application/x-www-form-urlencoded"}

        payload = (
            f"client_id={self.client_id}&client_secret={self.client_secret}&"
            f"grant_type={self.client_credentials}"
        )

        try:
            response = requests.request(
                "POST",
                req_url,
                headers=req_headers,
                data=payload,
                timeout=TIMEOUT,
            )
            if response.status_code in (401, 403, 400, 404):
                return_value = False
                output_message = "Please provide valid Luminar API Credentials"
                status = EXECUTION_STATE_FAILED
            elif response.ok:
                return_value = True
                output_message = "Luminar API Connected successfully"
                status = EXECUTION_STATE_COMPLETED
            else:
                return_value = False
                output_message = "Connection Failed"
                status = EXECUTION_STATE_FAILED
        except Exception as err:
            output_message = f"Failed to connect to Luminar API... Error is {err}"
            self.siemplify.LOGGER.error(output_message)
            self.siemplify.LOGGER.exception(err)
            return_value = False
            status = EXECUTION_STATE_FAILED
        return return_value, output_message, status

    def get_access_token(self):
        """Get luminar access token once connected to luminar server.
        :return: access token: {str}
        """
        try:
            req_url = self.base_url + "/externalApi/realm/" + self.account_id + "/token"
            req_headers = {"Content-Type": "application/x-www-form-urlencoded"}
            client_credentials = "client_credentials"
            payload = (
                f"client_id={self.client_id}&"
                f"client_secret={self.client_secret}&grant_type={client_credentials}"
            )

            response = requests.request(
                "POST",
                req_url,
                headers=req_headers,
                data=payload,
                timeout=TIMEOUT,
            )
            if response.ok:
                return (
                    response.json()["access_token"]
                    if response.json()["access_token"]
                    else False
                )
            self.siemplify.LOGGER.error("Connection Failed")
            return False
        except Exception as err:
            output_message = f"Failed to connect to Luminar API... Error is {err}"
            self.siemplify.LOGGER.error(output_message)
            self.siemplify.LOGGER.exception(err)
            return False


def slice_list_to_max_sub_lists(data: list, max_size_sublist: int) -> list:
    """Slice list into sublists. Each sublist will have max size of <max_size_sublist>
    :param data: {[]} list of values to split to sublists
    :param max_size_sublist: {int} max size of sublist
    :return: {[]} list of sublists of max size <max_size_sublist>
    """
    for i in range(0, len(data), max_size_sublist):
        yield data[i : i + max_size_sublist]


def generic_item_finder(all_objects: list, item_id: str) -> object:
    """Filtering malware id from all object list and returning the malware dict
    :param all_objects: {[]} list of all objects
    :param item_id: {str} malware id
    :return: filter object: {object}
    """
    return filter(lambda x: x.get("id") == item_id, all_objects)


def field_mapping(ind: str, value: str) -> dict:
    """Assigning associated indicator type and indicator value
    :param ind: {str} indicator type
    :param value: {str} indicator value
    :return: {dict}
    """
    return {"indicator_type": ind, "indicator_value": value}


IndicatorTypes = {
    "file:hashes.'SHA-1'": field_mapping,
    "file:hashes.MD5": field_mapping,
    "file:hashes.'SHA-256'": field_mapping,
    "file:hashes.'SHA-512'": field_mapping,
    "ipv4-addr": field_mapping,
    "file:name": field_mapping,
    "file:size": field_mapping,
    "url": field_mapping,
    "email-addr": field_mapping,
    "domain-name": field_mapping,
    "ipv6-addr": field_mapping,
    "mac-addr": field_mapping,
    "directory": field_mapping,
    "mutex": field_mapping,
    "windows-registry-key": field_mapping,
}


def enrich_incident_items(parent: dict, childrens: dict):
    """Enriching user account with associated incident details
    :param parent: {dict} incident dict
    :param childrens: {dict} user-account dict
    :return: tuple (parent, childrens)
        WHERE
        dict parent is incident
        dict children is user-account
    """
    enrich_info = {}
    for keys, values in parent.items():
        enrich_info[keys] = values

    for children in childrens:
        children.update(enrich_info)

    return parent, childrens


def enrich_malware_items(parent: dict, childrens: dict):
    """Enriching indicator with associated malware details
    :param parent: {dict} malware dict
    :param childrens: {dict} indicator dict
    :return: tuple (parent, childrens)
        WHERE
        dict parent is malware
        dict childrens is indicator
    """
    ioc = dict
    for children in childrens:
        indicator_type = None
        pattern = children.get("pattern")
        for match in STIX_PARSER.findall(pattern):
            stix_type, stix_property, value = match

            if stix_type == "file":
                indicator_type = f"{stix_type}:{stix_property}"
            else:
                indicator_type = stix_type
        if indicator_type is None:
            continue
        if SIEMPLIFY_MAPPING.get(indicator_type):
            mapping_method = IndicatorTypes.get(indicator_type)
            ioc = mapping_method(SIEMPLIFY_MAPPING[indicator_type], value)
        children["malware_details"] = parent
        children["indicator_type"] = ioc["indicator_type"]
        children["indicator_value"] = ioc["indicator_value"]

        parent["name"] = children["name"]

    return parent, childrens
