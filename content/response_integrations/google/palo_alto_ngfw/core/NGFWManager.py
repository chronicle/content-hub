from __future__ import annotations
import datetime
import json
import os
import tempfile
import uuid

import defusedxml.ElementTree as ET
from defusedxml import minidom
import requests
import xmltodict

from .constants import ITEMS_PER_REQUEST
from .exceptions import (
    AlreadyExistsException,
    CategoryNotExistsException,
    GroupNotExistsException,
    NGFWException,
)


class XmlHelper:
    """
    A class for extending action on xml
    """

    def GetSimpleValue(self, inputString, nodeName, root=None):
        xmldoc = minidom.parseString(inputString)

        if not root:
            root = xmldoc

        nodes = root.getElementsByTagName(nodeName)

        if nodes.__len__() != 1:
            raise NGFWException(f"Matching nodes count != 1! {nodeName}")

        return nodes[0].firstChild.data


class NGFWManager:

    def __init__(
        self,
        server_address,
        username,
        password,
        backup_folder=None,
        logger=None,
        verify_ssl=None,
    ):
        self.server_address = server_address
        self.username = username
        self.password = password
        self.logger = logger

        self.session = requests.Session()
        self.session.verify = verify_ssl

        if not backup_folder:
            self.backup_folder = tempfile.gettempdir()
        else:
            self.backup_folder = backup_folder

        self._xml_helper = XmlHelper()

        self.api_key = self.set_api_key()

    def set_api_key(self) -> str:
        """
        Authenticates with the Palo Alto Networks firewall using API key. Tries the POST
        method first and falls back to the deprecated GET method if necessary.

        Returns:
            str: API key.
        """
        try:
            response = self._get_api_key_using_post()

        except requests.exceptions.RequestException:
            response = self._get_api_key_using_get()

        return self._xml_helper.GetSimpleValue(response, "key")

    def _get_api_key_using_post(self) -> None:
        """Attempts to get the API key using the POST method."""
        url = f"{self.server_address}/?type=keygen"
        payload = {"user": self.username, "password": self.password}

        response = self.session.post(url, data=payload)
        self._validate_authentication(response)

        return response.content

    def _get_api_key_using_get(self) -> None:
        """Attempts to get the API key using the deprecated GET method."""
        url = (
            f"{self.server_address}/?type=keygen&user="
            f"{self.username}&password={self.password}"
        )
        response = self.session.get(url)
        self._validate_authentication(response)

        return response.content

    def _validate_authentication(self, response: requests.Response) -> None:
        """
        Validates the response from the firewall.

        Args:
            response (requests.Response): Response from API.

        Raises:
            NGFWException: If the response is invalid.
        """
        response.raise_for_status()

        if not self.is_valid_response(response):
            error_message = self._get_error_message(response)
            raise NGFWException(f"Could not login: {error_message}")

    def _get_error_message(self, response: requests.Response) -> str:
        """Extracts the error message from the response content.

        Args:
            response (requests.Response): Response from API

        Returns:
            str: Error message.
        """
        return (
            self._xml_helper.GetSimpleValue(response.content, "msg")
            if hasattr(response, "content")
            else "Unknown error"
        )

    def generate_backup_file(self, method_name, content):
        file_name = f"{method_name}_{datetime.datetime.now().strftime( '%Y%m%d-%H%M%S')}_{str(uuid.uuid4())}.json"

        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)

        with open(os.path.join(self.backup_folder, file_name), "w") as f:
            f.write(content)

        return os.path.join(self.backup_folder, file_name)

    def GetCurrenCanidateConfig(self):
        """
        Get the full configuration xml of panorama.
        :return:
        """
        cmd = "<show><config><saved>candidate-config</saved></config></show>"
        request_path = f"{self.server_address}/?type=op&cmd={cmd}&key={self.api_key}"
        r = self.session.get(request_path)
        r.raise_for_status()

        # Return config xml
        return r.content

    def FindRuleBlockedApplications(self, config, deviceName, vsysName, policyName):
        """
        List all blocked applications from a given rule
        :param config: {str} panorama config xml
        :param deviceName: {str} the device name in which the rule is located
        :param vsysName: {str} the vsys in which the rule is located
        :param policyName: {str} The policy name
        :return: Set of blocked applications
        """
        xpath = f"./result/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/rulebase/security/rules/entry[@name='{policyName}']/application"
        tree = ET.fromstring(config)
        element = tree.findall(xpath)
        applications = []

        if element:
            for memeber in element[0]:
                applications.append(memeber.text)
            return set(applications)

        return set(applications)

    def FindRuleBlockedUrls(self, deviceName, vsysName, policyName):
        """
        List all blocked urls from a given blacklist
        :param deviceName: {str} the device name in which the rule is located
        :param vsysName: {str} the vsys in which the rule is located
        :param policyName: {str}  The policy name
        :return: Set of blocked urls
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/profiles/custom-url-category/entry[@name='{policyName}']/list/member"

        request_path = f"{self.server_address}/?type=config&action=get&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            element = ET.fromstring(r.content)
            urls = []

            if element:
                for memeber in element[0]:
                    urls.append(memeber.text)
                return set(urls)

            return set(urls)

    def FindAddresses(self, deviceName, vsysName):
        """
        Get all the address objects.
        :param deviceName: {str} Device name
        :param vsysName: {str} Vsys to which the objects are attached
        :return: set of addresses
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address/entry"

        request_path = f"{self.server_address}/?type=config&action=get&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            element = ET.fromstring(r.content)
            if element:
                return [ET.tostring(entry) for entry in element[0]]
        return set()

    def ListAddressesInGroup(self, deviceName, vsysName, groupName):
        """
        Get all the address objects from an address group.
        :param deviceName: {str} Device name
        :param vsysName: {str} Vsys to which the objects are attached
        :param groupName: {str} Address group name
        :return: set of addresses
        """
        xpath = rf"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address-group/entry[@name='{groupName}']/static/member"

        request_path = f"{self.server_address}/?type=config&action=get&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            element = ET.fromstring(r.content)
            addresses = []

            if element:
                for address in element[0]:
                    addresses.append(address.text)
                return set(addresses)

            return set(addresses)

    def FindRuleBlockedIps(self, deviceName, vsysName, policyName, target):
        """
        List all blocked ips from a given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param vsysName: {str} the vsys in which the rule is located
        :param policyName: {str} The policy name
        :param target: {str} source / destination
        :return: Set of blocked ips
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/rulebase/security/rules/entry[@name='{policyName}']/{target}/member"

        request_path = f"{self.server_address}/?type=config&action=get&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            element = ET.fromstring(r.content)
            ips = []

            if element:
                for memeber in element[0]:
                    ips.append(memeber.text)
                return set(ips)

            return set(ips)

    def EditBlockedApplicationRequest(
        self, applications, deviceName, vsysName, policyName
    ):
        """
        Edit the blocked applications in a rule
        :param applications: {set} the applications list ot set to the policy
        :param deviceName: {str} the device name in which the rule is located
        :param vsysName: {str} the vsys in which the rule is located
        :param policyName: {str} the policy name
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/rulebase/security/rules/entry[@name='{policyName}']/application"

        request_path = f"{self.server_address}/?type=config&action=delete&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise NGFWException(r.content)

        if applications:
            for applications_chunk in self.chunks(
                list(applications), ITEMS_PER_REQUEST
            ):
                ips_xml = "".join(
                    f"<member>{application}</member>"
                    for application in applications_chunk
                )
                request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise NGFWException(r.content)

    def EditBlockedApplication(
        self, deviceName, vsysName, policyName, applicationsToAdd, applicationsToRemove
    ):
        """
        Block and unblock applications in given rule
        :param deviceName: {str} the device name in which the rule is located
        :param vsysName: {str} the vsys in which the rule is located
        :param policyName: {str} the policy name
        :param applicationsToAdd: {list} the applications to block
        :param applicationsToRemove: {list} the applications to unblock
        :return: {bool} True if edit was successful, exception otherwise
        """
        config = self.GetCurrenCanidateConfig()
        currentApplications = self.FindRuleBlockedApplications(
            config, deviceName, vsysName, policyName
        )

        backup = self.generate_backup_file(
            "EditBlockedApplication", json.dumps(list(currentApplications))
        )

        dirty = False
        result = False

        for app in applicationsToAdd:
            if app not in currentApplications:
                currentApplications.add(app)
                dirty = True

        for app in applicationsToRemove:
            if app in currentApplications:
                currentApplications.remove(app)
                dirty = True

        if dirty:

            result = self.EditBlockedApplicationRequest(
                currentApplications, deviceName, vsysName, policyName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def CommitChanges(self, only_my_changes=True):
        """
        Commit all changes at Panorama
        :param only_my_changes: {bool} Commit only changes that were made by
        the current user (has to be admin).
        :return: True if request is successful, exception otherwise.
        """
        if only_my_changes:
            request_path = f"{self.server_address}/?&type=commit&action=partial&cmd=<commit><partial><admin><member>{self.username}</member></admin></partial></commit>&key={self.api_key}"
        else:
            request_path = f"{self.server_address}/?type=commit&cmd=<commit><force></force></commit>&key={self.api_key}"

        r = self.session.get(request_path)

        r.raise_for_status()
        return True

    def EditBlockedUrlsRequest(self, urls, deviceName, vsysName, policyName):
        """
        Edit the blocked urls in a URL black list
        :param urls: {set} the updated urls
        :param deviceName: {str} the device name in which the blacklist is located
        :param vsysName: {str} the vsys in which the blacklist is located
        :param policyName: {str} The policy name
        :return: {bool} True if edit was successful, exception otherwise
        """

        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/profiles/custom-url-category/entry[@name='{policyName}']/list"

        request_path = f"{self.server_address}/?type=config&action=delete&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise NGFWException(r.content)

        if urls:
            for urls_chunk in self.chunks(list(urls), ITEMS_PER_REQUEST):
                ips_xml = "".join(
                    f"<member>{url.replace('&amp;', '&').replace('&', '&amp;')}</member>"
                    for url in urls_chunk
                )

                params = {
                    "type": "config",
                    "xpath": xpath,
                    "element": ips_xml,
                    "action": "set",
                }

                headers = {
                    "Accept": "application/xml",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-PAN-KEY": self.api_key,
                }

                r = self.session.get(
                    self.server_address, headers=headers, params=params
                )
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise NGFWException(r.content)

    def EditBlockedIpsRequest(self, ips, deviceName, vsysName, policyName, target):
        """
        Edit the blocked ips in a black list
        :param ips: {set} the updates xml elements
        :param deviceName: {str} the device name in which the blacklist is located
        :param vsysName: {str} the vsys in which the blacklist is located
        :param policyName: {str} Policy name
        :param target: {str} source or destination
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/rulebase/security/rules/entry[@name='{policyName}']/{target}"

        request_path = f"{self.server_address}/?type=config&action=delete&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise NGFWException(r.content)

        if ips:
            for ips_chunk in self.chunks(list(ips), ITEMS_PER_REQUEST):
                ips_xml = "".join(f"<member>{ips}</member>" for ips in ips_chunk)
                request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise NGFWException(r.content)

    def EditIpsInGroupRequest(self, ips, deviceName, vsysName, groupName):
        """
        Edit the ips in a group
        :param ips: {set} the ips that will remain in the group
        :param deviceName: {str} the device name in which the group is located
        :param vsysName: {str} the vsys in which the group is located:
        :param groupName: {str} Ip group name
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = rf"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address-group/entry[@name='{groupName}']/static"

        request_path = f"{self.server_address}/?type=config&action=delete&key={self.api_key}&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise NGFWException(r.content)

        if ips:
            for ips_chunk in self.chunks(list(ips), ITEMS_PER_REQUEST):
                ips_xml = "".join(f"<member>{ip}</member>" for ip in ips_chunk)
                request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise NGFWException(r.content)

        return True

    def EditBlockedUrls(
        self, deviceName, vsysName, policyName, urlsToAdd=None, urlsToRemove=None
    ):
        """
        Block and unblock urls in given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param vsysName: {str} the vsys in which the blacklist is located
        :param policyName: {str} the policy name
        :param urlsToAdd: {list} the urls to block
        :param urlsToRemove: {list} the urls to unblock
        :return: {bool} True if edit was successful, exception otherwise
        """
        if not urlsToAdd:
            urlsToAdd = []

        if not urlsToRemove:
            urlsToRemove = []

        currentUrls = self.FindRuleBlockedUrls(deviceName, vsysName, policyName)

        if currentUrls is None:
            currentUrls = set([])

        backup = self.generate_backup_file(
            "EditBlockedUrls", json.dumps(list(currentUrls))
        )

        dirty = False
        result = False

        for url in urlsToAdd:
            if url not in currentUrls:
                currentUrls.add(url)
                dirty = True

        for url in urlsToRemove:
            if url in currentUrls:
                currentUrls.remove(url)
                dirty = True

        if dirty:
            result = self.EditBlockedUrlsRequest(
                currentUrls, deviceName, vsysName, policyName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def EditBlockedIps(
        self, deviceName, vsysName, policyName, target, IpsToAdd=None, IpsToRemove=None
    ):
        """
        Block and unblock ips in given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param vsysName: {str} the vsys in which the blacklist is located
        :param policyName: {str} the policy name
        :param target: {str} source / destination
        :param IpsToAdd: {list} the ips to block
        :param IpsToRemove: {list} the ips to unblock
        :return: {bool} True if edit was successful, exception otherwise
        """

        if not IpsToAdd:
            IpsToAdd = []

        if not IpsToRemove:
            IpsToRemove = []

        currentIps = (
            self.FindRuleBlockedIps(deviceName, vsysName, policyName, target) or set()
        )

        backup = self.generate_backup_file(
            "EditBlockedIps", json.dumps(list(currentIps))
        )

        dirty = False
        result = False

        addresses = self.FindAddresses(deviceName, vsysName)
        existing_ips = []

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if isinstance(entry.get("ip-netmask"), dict) and existing_ips.append(
                entry.get("ip-netmask", {}).get("#text")
            ):
                existing_ips.append(entry.get("ip-netmask", {}).get("#text"))
            elif entry.get("ip-netmask"):
                existing_ips.append(entry.get("ip-netmask"))

        for ip in IpsToAdd:
            if ip not in currentIps:
                currentIps.add(ip)
                if ip not in existing_ips:
                    self.CreateAddressObject(deviceName, vsysName, ip)
                dirty = True

        for ip in IpsToRemove:
            if ip in currentIps:
                currentIps.remove(ip)
                dirty = True

        if dirty:
            result = self.EditBlockedIpsRequest(
                currentIps, deviceName, vsysName, policyName, target
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def EditBlockedIpsInGroup(
        self, deviceName, vsysName, groupName, IpsToAdd=None, IpsToRemove=None
    ):
        """
        Add or remove ips in given group
        :param deviceName: {str} the device name in which the group is located
        :param vsysName: {str} the vsys in which the group is located
        :param groupName: {str} the group name
        :param IpsToAdd: {list} the ips to add
        :param IpsToRemove: {list} the ips to remove
        :return: {bool} True if edit was successful, exception otherwise
        """

        if not IpsToAdd:
            IpsToAdd = []

        if not IpsToRemove:
            IpsToRemove = []

        currentIps = self.ListAddressesInGroup(deviceName, vsysName, groupName) or set()

        backup = self.generate_backup_file(
            "EditBlockedIpsInGroup", json.dumps(list(currentIps))
        )

        addresses = self.FindAddresses(deviceName, vsysName)
        existing_ips = []

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if isinstance(entry.get("ip-netmask"), dict) and existing_ips.append(
                entry.get("ip-netmask", {}).get("#text")
            ):
                existing_ips.append(entry.get("ip-netmask", {}).get("#text"))
            elif entry.get("ip-netmask"):
                existing_ips.append(entry.get("ip-netmask"))

        dirty = False
        result = False

        for ip in IpsToAdd:
            if ip not in currentIps:
                currentIps.add(ip)

                if ip not in existing_ips:
                    self.CreateAddressObject(deviceName, vsysName, ip)
                dirty = True

        for ip in IpsToRemove:
            if ip in currentIps:
                currentIps.remove(ip)
                dirty = True

        if dirty:
            result = self.EditIpsInGroupRequest(
                currentIps, deviceName, vsysName, groupName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def CreateAddressObject(self, deviceName, vsysName, new_address):
        """
        Create a new address object
        :param deviceName: {str} Device name
        :param vsysName: {str} Vsys to which the objects are attached
        :param new_address: {str} the new address to create
        :return: True if succuss, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address"

        addresses = self.FindAddresses(deviceName, vsysName)

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if (
                isinstance(entry.get("ip-netmask"), dict)
                and entry.get("ip-netmask", {}).get("#text") == new_address
                or entry.get("ip-netmask") == new_address
            ):
                # Ip already exists - return True
                return True

        element_value = f"<entry name='{new_address}'><ip-netmask>{new_address}</ip-netmask></entry>"

        request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={element_value}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def GetGroup(self, group_name):
        """
        Get Shared Group
        :param group_name: {str} Group Name
        :return: {Response.content} if group found GroupNotExistsException otherwise
        """
        params = {
            "type": "config",
            "action": "get",
            "xpath": f"/config/shared/address-group/entry[@name='{group_name}']",
            "key": self.api_key,
        }
        request_path = f"{self.server_address}/"

        r = self.session.get(request_path, params=params)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise GroupNotExistsException

        return r.content

    def EnitityExistsInGroup(self, group_name, entity_identifier):
        """
        Check entity exists in group or not
        :param group_name: {str} Group Name
        :param entity_identifier: {str} Entity identifier
        :return: {bool} False if entity not exists in group AlreadyExistsException otherwise
        """
        content = self.GetGroup(group_name)
        addresses = self.GetAddressesFromSharedGroup(content)

        if entity_identifier in addresses:
            raise AlreadyExistsException

        return False

    def IsEntityShared(self, entity_identifier):
        """
        Check is entity shared
        :param entity_identifier: {str} Entity identifier
        :return: {bool} True if entity is shared False otherwise
        """
        params = {
            "type": "config",
            "action": "get",
            "xpath": "/config/shared/address/entry",
            "key": self.api_key,
        }
        request_path = f"{self.server_address}/"
        r = self.session.get(request_path, params=params)
        r.raise_for_status()

        addresses = self.GetSharedAddresses(r.content)

        return entity_identifier in addresses

    def GetSharedAddresses(self, content):
        """
        Get shared addresses
        :param content: {Response.content} Response content with shared addresses
        :return: {list} shared addresses
        """
        element = ET.fromstring(content)
        parsed_addresses, addresses = [], []

        if element:
            addresses = [ET.tostring(entry) for entry in element[0]]

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]
            parsed_addresses.append(
                entry.get("ip-netmask")
                if not isinstance(entry.get("ip-netmask"), dict)
                else entry.get("ip-netmask").get("#text")
            )

        return list(set(parsed_addresses))

    def GetAddressesFromSharedGroup(self, content):
        """
        Get addresses from shared group
        :param content: {Response.content} Response content with shared addresses from group
        :return: {list} shared addresses
        """
        element = ET.fromstring(content)
        parsed_addresses, addresses = [], []

        if element:
            addresses = [ET.tostring(entry) for entry in element[0]]

        for address in addresses:
            entries = (
                xmltodict.parse(address)
                .get("entry", {})
                .get("static", {})
                .get("member", [])
            )
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str) or isinstance(entry, str):
                        parsed_addresses.append(entry)
                    else:
                        parsed_addresses.append(entry.get("#text"))
            elif isinstance(entries, str) or isinstance(entries, str):
                parsed_addresses.append(entries)
            else:
                parsed_addresses.append(entries.get("#text"))

        return list(set(parsed_addresses))

    def ListSharedAddressesFromGroup(self, group_name):
        """
        Get list addresses from shared group
        :param group_name: {str} Shared Group name
        :return: {list} shared addresses
        """
        content = self.GetGroup(group_name)
        addresses = self.GetAddressesFromSharedGroup(content)

        return addresses

    def AddSharedEntity(self, entity_identifier):
        """
        Get addresses from shared group
        :param entity_identifier: {str} entity identifier
        :return: {list} shared addresses
        """
        params = {
            "type": "config",
            "action": "set",
            "xpath": f"/config/shared/address/entry[@name='{entity_identifier}']",
            "element": f"<ip-netmask>{entity_identifier}</ip-netmask>",
            "key": self.api_key,
        }

        request_path = f"{self.server_address}/"
        r = self.session.get(request_path, params=params)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def EditSharedIpsInGroup(self, group_name, entity_identifier, action):
        """
        Add entity to shared group
        :param group_name: {str} shared group name
        :param entity_identifier: {str} entity identifier
        :param action: {str} can be set or delete
        :return: {list} shared addresses
        """
        params = {
            "type": "config",
            "action": action,
            "xpath": f"/config/shared/address-group/entry[@name='{group_name}']/static",
            "element": f"<member>{entity_identifier}</member>",
            "key": self.api_key,
        }
        request_path = f"{self.server_address}/"
        r = self.session.get(request_path, params=params)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def GetCategory(self, category_name):
        """
        Get Shared Category
        :param category_name: {str} Category Name
        :return: {Response.content} if Category found CategoryNotExistsException otherwise
        """
        params = {
            "type": "config",
            "action": "get",
            "xpath": f"/config/shared/profiles/custom-url-category/entry[@name='{category_name}']",
            "key": self.api_key,
        }
        request_path = f"{self.server_address}/"

        r = self.session.get(request_path, params=params)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise CategoryNotExistsException

        return r.content

    def GetUrlsFromSharedCategory(self, content):
        """
        Get urls from shared category
        :param content: {Response.content} Response content with shared addresses from group
        :return: {list} shared addresses
        """
        element = ET.fromstring(content)
        parsed_urls, urls = [], []

        if element:
            urls = [ET.tostring(entry) for entry in element[0]]

        for url in urls:
            entries = (
                xmltodict.parse(url).get("entry", {}).get("list", {}).get("member", [])
            )

            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str) or isinstance(entry, str):
                        parsed_urls.append(entry)
                    else:
                        parsed_urls.append(entry.get("#text"))
            elif isinstance(entries, str) or isinstance(entries, str):
                parsed_urls.append(entries)
            else:
                parsed_urls.append(entries.get("#text"))

        return list(set(parsed_urls))

    def EnitityExistsInCategory(self, category_name, entity_identifier):
        """
        Check entity exists in category or not
        :param category_name: {str} Category Name
        :param entity_identifier: {str} Entity identifier
        :return: {bool} False if entity not exists in group AlreadyExistsException otherwise
        """
        content = self.GetCategory(category_name)
        urls = self.GetUrlsFromSharedCategory(content)

        if entity_identifier in urls:
            raise AlreadyExistsException

        return False

    def EditSharedUrlInCategory(self, category_name, entity_identifier, action):
        """
        Add entity to shared category
        :param category_name: {str} shared category name
        :param entity_identifier: {str} entity identifier
        :param action: {str} can be set or delete
        :return: {list} shared addresses
        """
        params = {
            "type": "config",
            "action": action,
            "xpath": f"/config/shared/profiles/custom-url-category/entry[@name='{category_name}']/list",
            "element": f'<member>{entity_identifier.replace("&amp;", "&").replace("&", "&amp;")}</member>',
            "key": self.api_key,
        }

        headers = {
            "Accept": "application/xml",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-PAN-KEY": self.api_key,
        }

        r = self.session.get(self.server_address, headers=headers, params=params)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def ListSharedUrlsFromCategory(self, category_name):
        """
        Get list urls from shared category
        :param category_name: {str} Shared Category name
        :return: {list} shared urls
        """
        content = self.GetCategory(category_name)
        urls = self.GetUrlsFromSharedCategory(content)

        return urls

    def CreateFQDNObject(self, deviceName, vsysName, new_fqdn):
        """
        Create a new address object
        :param deviceName: {str} Device name
        :param vsysName: {str} Vsys to which the objects are attached
        :param new_address: {str} the new address to create
        :return: True if succuss, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address"

        addresses = self.FindAddresses(deviceName, vsysName)

        # Validate that fqdn doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if (
                isinstance(entry.get("fqdn"), dict)
                and entry.get("fqdn", {}).get("#text") == new_fqdn
                or entry.get("fqdn") == new_fqdn
            ):
                # fqdn already exists - return True
                return True

        element_value = f"<entry name='{new_fqdn}'><fqdn>{new_fqdn}</fqdn></entry>"

        request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={element_value}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def CreateIpRangeObject(self, deviceName, vsysName, ip_range):
        """
        Create a new address object
        :param deviceName: {str} Device name
        :param vsysName: {str} Vsys to which the objects are attached
        :param ip_range: {str} the new ip range to create
        :return: True if succuss, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/vsys/entry[@name='{vsysName}']/address"

        addresses = self.FindAddresses(deviceName, vsysName)
        # Validate that ip_range doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if (
                isinstance(entry.get("ip-range"), dict)
                and entry.get("ip-range", {}).get("#text") == ip_range
                or entry.get("ip-range") == ip_range
            ):
                # ip_range already exists - return True
                return True

        element_value = (
            f"<entry name='{ip_range}'><ip-range>{ip_range}</ip-range></entry>"
        )

        request_path = f"{self.server_address}/?type=config&action=set&key={self.api_key}&xpath={xpath}&element={ET.tostring(element_value)}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            return True

    def is_valid_response(self, response):
        """
        IGven a response, checks if valid
        :param response: {requests.Response} The response
        :return: True if valid, excpetion otherwise
        """
        if (
            response.text
            == '<response status="success" code="7"><result/></response>'
        ):
            return False

        if not response.text:
            return True

        if "success" in response.text:
            return True

        if (
            response.text
            == '<response status="unauth" code="16"><msg><line>Unauthorized request</line></msg></response>'
        ):
            raise NGFWException("Unauthorized request")

        raise NGFWException(f"Invalid Response: {response.text}")

    @staticmethod
    def chunks(l, n):
        # For item i in a range that is a length of l,
        for i in range(0, len(l), n):
            # Create an index range for l of n items:
            yield l[i : i + n]
