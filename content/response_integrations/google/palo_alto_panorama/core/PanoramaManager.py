# coding=utf-8
# ============================================================================#
# title           :PanoramaManager.py
# description     :This Module contain all Panorama operations functionality
# author          :avital@siemplify.co
# date            :22-04-2018
# python_version  :2.7
# libreries       :
# requirments     : For URL blocking configure Url Black list and attach it to the policy
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
import tempfile
import datetime
import json
import uuid
import os
from defusedxml import minidom
import defusedxml.ElementTree as ET
import xmltodict
import copy
import urllib.parse
from time import sleep
from .PanoramaParser import PanoramaParser
from .PanoramaExceptions import JobNotFinishedException
from .PanoramaCommon import PanoramaCommon, convert_server_time_to_datetime
from .PanoramaConstants import (
    ITEMS_PER_REQUEST,
    HEADERS,
    ENDPOINTS,
    LOG_TYPE_MAP,
    TIME_FORMAT,
    JOB_FINISHED_STATUS,
    LOGS_LIMIT,
    COMMIT_STATUS_FAILED,
)
from bs4 import BeautifulSoup


# ============================= CLASSES ===================================== #


class PanoramaException(Exception):
    pass


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
            raise PanoramaException(f"Matching nodes count != 1! {nodeName}")

        return nodes[0].firstChild.data


class PanoramaManager:

    def __init__(
        self,
        server_address,
        username,
        password,
        verify_ssl=False,
        backup_folder=None,
        siemplify_logger=None,
    ):
        self.server_address = server_address
        self.username = username
        self.password = password
        self.session = requests.session()
        self.session.headers = HEADERS
        self.session.verify = verify_ssl
        self.parser = PanoramaParser()
        self.siemplify_logger = siemplify_logger
        self.panorama_common = PanoramaCommon(self.siemplify_logger)
        self.server_time = None
        if not backup_folder:
            self.backup_folder = tempfile.gettempdir()
        else:
            self.backup_folder = backup_folder

        self._xml_helper = XmlHelper()

        payload = {"user": self.username, "password": self.password, "type": "keygen"}
        r = self.session.post(self.server_address, data=payload)

        if not self.is_valid_response(r):
            raise PanoramaException(f"Could not login: {r.content}")

        self.api_key = self._xml_helper.GetSimpleValue(r.content, "key")
        self.session.headers.update({"X-PAN-KEY": self.api_key})

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
        request_path = f"{self.server_address}/?type=op&cmd={cmd}"
        r = self.session.get(request_path)
        r.raise_for_status()

        # Return config xml
        return r.content

    def FindRuleBlockedApplications(
        self, config, deviceName, deviceGroupName, policyName
    ):
        """
        List all blocked applications from a given rule
        :param config: {str} panorama config xml
        :param deviceName: {str} the device name in which the rule is located
        :param deviceGroupName: {str} the device group in which the rule is located
        :param policyName: {str} The policy name
        :return: Set of blocked applications
        """
        xpath = f"./result/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/pre-rulebase/security/rules/entry[@name='{policyName}']/application"
        tree = ET.fromstring(config)
        element = tree.findall(xpath)
        applications = []

        if element:
            for memeber in element[0]:
                applications.append(memeber.text)
            return set(applications)

        return set(applications)

    def FindRuleBlockedUrls(self, deviceName, deviceGroupName, policyName):
        """
        List all blocked urls from a given blacklist
        :param deviceName: {str} the device name in which the rule is located
        :param deviceGroupName: {str} the device group in which the rule is located
        :param policyName: {str}  The policy name
        :return: Set of blocked urls
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/profiles/custom-url-category/entry[@name='{policyName}']/list/member"

        request_path = f"{self.server_address}/?type=config&action=get&xpath={xpath}"

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

    def FindAddresses(self, deviceName, deviceGroupName):
        """
        Get all the address objects.
        :param deviceName: {str} Device name
        :param deviceGroupName: {str} device group to which the objects are attached
        :return: set of addresses
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/address/entry"

        request_path = f"{self.server_address}/?type=config&action=get&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if self.is_valid_response(r):
            element = ET.fromstring(r.content)
            if element:
                return [ET.tostring(entry) for entry in element[0]]
            return set()

    def ListAddressesInGroup(self, deviceName, deviceGroupName, groupName):
        """
        Get all the address objects from an address group.
        :param deviceName: {str} Device name
        :param deviceGroupName: {str} device group to which the objects are attached
        :param groupName: {str} Address group name
        :return: set of addresses
        """
        xpath = rf"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/address-group/entry[@name='{groupName}']/static/member"

        request_path = f"{self.server_address}/?type=config&action=get&xpath={xpath}"

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

    def FindRuleBlockedIps(self, deviceName, deviceGroupName, policyName, target):
        """
        List all blocked ips from a given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param deviceGroupName: {str} the device group in which the rule is located
        :param policyName: {str} The policy name
        :param target: {str} source / destination
        :return: Set of blocked ips
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/pre-rulebase/security/rules/entry[@name='{policyName}']/{target}/member"

        request_path = f"{self.server_address}/?type=config&action=get&xpath={xpath}"

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
        self, applications, deviceName, deviceGroupName, policyName
    ):
        """
        Edit the blocked applications in a rule
        :param applications: {set} the applications list ot set to the policy
        :param deviceName: {str} the device name in which the rule is located
        :param deviceGroupName: {str} the device group in which the rule is located
        :param policyName: {str} the policy name
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/pre-rulebase/security/rules/entry[@name='{policyName}']/application"

        request_path = f"{self.server_address}/?type=config&action=delete&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise PanoramaException(r.content)

        if applications:
            for applications_chunk in self.chunks(
                list(applications), ITEMS_PER_REQUEST
            ):
                ips_xml = "".join(
                    f"<member>{application}</member>"
                    for application in applications_chunk
                )
                request_path = f"{self.server_address}/?type=config&action=set&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise PanoramaException(r.content)

    def EditBlockedApplication(
        self,
        deviceName,
        deviceGroupName,
        policyName,
        applicationsToAdd=[],
        applicationsToRemove=[],
    ):
        """
        Block and unblock applications in given rule
        :param deviceName: {str} the device name in which the rule is located
        :param deviceGroupName: {str} the device group in which the rule is located
        :param policyName: {str} the policy name
        :param applicationsToAdd: {list} the applications to block
        :param applicationsToRemove: {list} the applications to unblock
        :return: {bool} True if edit was successful, exception otherwise
        """

        if not applicationsToAdd:
            applicationsToAdd = []

        if not applicationsToRemove:
            applicationsToRemove = []

        config = self.GetCurrenCanidateConfig()
        currentApplications = self.FindRuleBlockedApplications(
            config, deviceName, deviceGroupName, policyName
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
                currentApplications, deviceName, deviceGroupName, policyName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def CommitChanges(self, only_my_changes=False):
        """
        Commit all changes at Panorama
        :param only_my_changes: {bool} Commit only changes that were made by
        :return: job_id {str} ID of the commit job
        """
        if only_my_changes:
            request_path = f"{self.server_address}/?&type=commit&action=partial&cmd=<commit><partial><admin><member>{self.username}</member></admin></partial></commit>"
        else:
            request_path = f"{self.server_address}/?type=commit&cmd=<commit><force></force></commit>"

        r = self.session.get(request_path)
        r.raise_for_status()
        job_id = None
        element = ET.fromstring(r.content)

        if element:
            for member in element[0]:
                if member.tag == "job":
                    job_id = member.text

        return job_id

    def check_commit_status(self, job_id):
        """
        Function that checks the commit status
        :param {str}: Job ID to check status of
        :return {str}: Status of the Job
        """
        request_path = f"{self.server_address}?type=op&cmd=<show><jobs><id>{job_id}</id></jobs></show>"

        r = self.session.get(request_path)
        r.raise_for_status()

        status = None
        result = None
        output_message = []

        element = ET.fromstring(r.content)

        if element:
            for member in element[0]:
                if member.tag == "job":
                    for status_member in member:
                        if status_member.tag == "status":
                            status = status_member.text

                        if status_member.tag == "result":
                            result = status_member.text

        if result == COMMIT_STATUS_FAILED:
            soup = BeautifulSoup(r.content, "lxml")
            details = soup.findAll("details")
            if details:
                for detail in details:
                    output_message.append(detail.text)

        output_message = "\n".join(output_message)

        return status, result, output_message

    def PushChanges(self, device_group):
        """
        Commit all changes at Panorama
        :param device_group: {string} Name of the device group to push its commits
        :return: job_id {str} ID of the push job
        """
        request_path = f'{self.server_address}/?&type=commit&action=all&cmd=<commit-all><shared-policy><device-group><entry name="{device_group}"/></device-group></shared-policy></commit-all>'
        request_headers = copy.deepcopy(self.session.headers)
        request_headers["Content-Type"] = "application/xml"
        r = self.session.get(request_path, headers=request_headers)

        r.raise_for_status()
        job_id = None
        element = ET.fromstring(r.content)

        if element:
            for member in element[0]:
                if member.tag == "job":
                    job_id = member.text

        return job_id

    def EditBlockedUrlsRequest(self, urls, deviceName, deviceGroupName, policyName):
        """
        Edit the blocked urls in a URL black list
        :param urls: {set} the updated urls
        :param deviceName: {str} the device name in which the blacklist is located
        :param deviceGroupName: {str} the device group in which the blacklist is located
        :param policyName: {str} The policy name
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/profiles/custom-url-category/entry[@name='{policyName}']/list"

        request_path = f"{self.server_address}/?type=config&action=delete&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise PanoramaException(r.content)

        if urls:
            for urls_chunk in self.chunks(list(urls), ITEMS_PER_REQUEST):
                ips_xml = "".join(f"<member>{url}</member>" for url in urls_chunk)
                request_path = f"{self.server_address}/?type=config&action=set&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise PanoramaException(r.content)

    def EditBlockedIpsRequest(
        self, ips, deviceName, deviceGroupName, policyName, target
    ):
        """
        Edit the blocked ips in a black list
        :param ips: {set} the updates xml elements
        :param deviceName: {str} the device name in which the blacklist is located
        :param deviceGroupName: {str} the device group in which the blacklist is located
        :param policyName: {str} Policy name
        :param target: {str} source or destination
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/pre-rulebase/security/rules/entry[@name='{policyName}']/{target}"

        request_path = f"{self.server_address}/?type=config&action=delete&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise PanoramaException(r.content)

        if ips:
            for ips_chunk in self.chunks(list(ips), ITEMS_PER_REQUEST):
                ips_xml = "".join(f"<member>{ips}</member>" for ips in ips_chunk)
                request_path = f"{self.server_address}/?type=config&action=set&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise PanoramaException(r.content)

    def EditIpsInGroupRequest(self, ips, deviceName, deviceGroupName, groupName):
        """
        Edit the ips in a group
        :param ips: {set} the ips that will remain in the group
        :param deviceName: {str} the device name in which the group is located
        :param deviceGroupName: {str} the device group in which the group is located:
        :param groupName: {str} Ip group name
        :return: {bool} True if edit was successful, exception otherwise
        """
        xpath = rf"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/address-group/entry[@name='{groupName}']/static"

        request_path = f"{self.server_address}/?type=config&action=delete&xpath={xpath}"

        r = self.session.get(request_path)
        r.raise_for_status()

        if not self.is_valid_response(r):
            raise PanoramaException(r.content)

        if ips:
            for ips_chunk in self.chunks(list(ips), ITEMS_PER_REQUEST):
                ips_xml = "".join(f"<member>{ip}</member>" for ip in ips_chunk)
                request_path = f"{self.server_address}/?type=config&action=set&xpath={xpath}&element={ips_xml}"

                r = self.session.get(request_path)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise PanoramaException(r.content)

        return True

    def AddBlockedUrls(
        self, device_name, device_group_name, policy_name, urls_to_add=None
    ):
        """
        Add urls to block in a given blacklist
        :param device_name: {str} the device name in which the blacklist is located
        :param device_group_name: {str} the device group in which the blacklist is located
        :param policy_name: {str} the policy name
        :param urls_to_add: {[str]} the urls to block
            raise PanoramaException if failed to add urls to a blacklist
        """
        current_urls = self.FindRuleBlockedUrls(
            device_name, device_group_name, policy_name
        )
        non_existing_urls_in_blocklist_to_add = set(urls_to_add) - current_urls

        if non_existing_urls_in_blocklist_to_add:
            params = {
                "type": "config",
                "xpath": f"/config/devices/entry[@name='{device_name}']/device-group/entry[@name='{device_group_name}']/profiles/custom-url-category/entry[@name='{policy_name}']/list",
            }
            for urls_chunk in self.chunks(
                list(non_existing_urls_in_blocklist_to_add), ITEMS_PER_REQUEST
            ):
                ips_xml = "".join(f"<member>{url}</member>" for url in urls_chunk)
                params.update({"element": ips_xml, "action": "set"})
                r = self.session.get(self.server_address, params=params)
                r.raise_for_status()

                if not self.is_valid_response(r):
                    raise PanoramaException(r.content)

    def RemoveBlockedUrls(
        self, device_name, device_group_name, policy_name, urls_to_remove=None
    ):
        """
        Remove urls from block in a given blacklist
        :param device_name: {str} the device name in which the blacklist is located
        :param device_group_name: {str} the device group in which the blacklist is located
        :param policy_name: {str} the policy name
        :param urls_to_remove: {[str]} the urls to unblock
            raise PanoramaException if failed to add urls to a blacklist
        """
        current_urls = self.FindRuleBlockedUrls(
            device_name, device_group_name, policy_name
        )
        existing_urls_in_block_list_to_remove = list(
            set(current_urls).intersection(urls_to_remove)
        )
        if (
            existing_urls_in_block_list_to_remove
            and existing_urls_in_block_list_to_remove[0]
        ):
            params = {
                "type": "config",
                "xpath": "/config/devices/entry[@name='%s']/device-group/entry[@name='%s']/profiles/custom-url-category/entry[@name='%s']/list/member[text()='%s']"
                % (
                    device_name,
                    device_group_name,
                    policy_name,
                    existing_urls_in_block_list_to_remove[0],
                ),
            }
            params.update({"action": "delete"})

            r = self.session.get(self.server_address, params=params)
            r.raise_for_status()

            if not self.is_valid_response(r):
                raise PanoramaException(r.content)
        else:
            error_msg = (
                f"The url {(urls_to_remove[0])} does not exists or invalid."
                if urls_to_remove and urls_to_remove[0]
                else "No url provided"
            )
            raise PanoramaException(error_msg)

    def EditBlockedUrls(
        self, deviceName, deviceGroupName, policyName, urlsToAdd=None, urlsToRemove=None
    ):
        """
        Block and unblock urls in given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param deviceGroupName: {str} the device group in which the blacklist is located
        :param policyName: {str} the policy name
        :param urlsToAdd: {list} the urls to block
        :param urlsToRemove: {list} the urls to unblock
        :return: {bool} True if edit was successful, exception otherwise
        """
        if not urlsToAdd:
            urlsToAdd = []

        if not urlsToRemove:
            urlsToRemove = []

        currentUrls = self.FindRuleBlockedUrls(deviceName, deviceGroupName, policyName)

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
                currentUrls, deviceName, deviceGroupName, policyName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def EditBlockedIps(
        self,
        deviceName,
        deviceGroupName,
        policyName,
        target,
        IpsToAdd=None,
        IpsToRemove=None,
    ):
        """
        Block and unblock ips in given blacklist
        :param deviceName: {str} the device name in which the blacklist is located
        :param deviceGroupName: {str} the device group in which the blacklist is located
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

        currentIps = self.FindRuleBlockedIps(
            deviceName, deviceGroupName, policyName, target
        )

        backup = self.generate_backup_file(
            "EditBlockedIps", json.dumps(list(currentIps))
        )

        dirty = False
        result = False

        addresses = self.FindAddresses(deviceName, deviceGroupName)
        existing_ips = []

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if isinstance(entry.get("ip-netmask"), dict) and entry.get(
                "ip-netmask", {}
            ).get("#text"):

                existing_ips.append(entry.get("ip-netmask", {}).get("#text"))
            elif entry.get("ip-netmask"):
                existing_ips.append(entry.get("ip-netmask"))

        for ip in IpsToAdd:
            if ip not in currentIps:
                currentIps.add(ip)
                if ip not in existing_ips:
                    self.CreateAddressObject(deviceName, deviceGroupName, ip)
                dirty = True

        for ip in IpsToRemove:
            if ip in currentIps:
                currentIps.remove(ip)
                dirty = True

        if dirty:
            result = self.EditBlockedIpsRequest(
                currentIps, deviceName, deviceGroupName, policyName, target
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def EditBlockedIpsInGroup(
        self, deviceName, deviceGroupName, groupName, IpsToAdd=None, IpsToRemove=None
    ):
        """
        Add or remove ips in given group
        :param deviceName: {str} the device name in which the group is located
        :param deviceGroupName: {str} the device group in which the group is located
        :param groupName: {str} the group name
        :param IpsToAdd: {list} the ips to add
        :param IpsToRemove: {list} the ips to remove
        :return: {bool} True if edit was successful, exception otherwise
        """

        if not IpsToAdd:
            IpsToAdd = []

        if not IpsToRemove:
            IpsToRemove = []

        currentIps = self.ListAddressesInGroup(deviceName, deviceGroupName, groupName)

        backup = self.generate_backup_file(
            "EditBlockedIpsInGroup", json.dumps(list(currentIps))
        )

        addresses = self.FindAddresses(deviceName, deviceGroupName)
        existing_ips = []

        # Validate that ip doesn't already exist
        for address in addresses:
            entry = xmltodict.parse(address)["entry"]

            if isinstance(entry.get("ip-netmask"), dict) and entry.get(
                "ip-netmask", {}
            ).get("#text"):
                existing_ips.append(entry.get("ip-netmask", {}).get("#text"))
            elif entry.get("ip-netmask"):
                existing_ips.append(entry.get("ip-netmask"))

        dirty = False
        result = False

        for ip in IpsToAdd:
            if ip not in currentIps:
                currentIps.add(ip)

                if ip not in existing_ips:
                    self.CreateAddressObject(deviceName, deviceGroupName, ip)
                dirty = True

        for ip in IpsToRemove:
            if ip in currentIps:
                currentIps.remove(ip)
                dirty = True

        if dirty:
            result = self.EditIpsInGroupRequest(
                currentIps, deviceName, deviceGroupName, groupName
            )

        try:
            os.remove(backup)
        except:
            # Unable to delete backup - continue
            pass

        return result

    def CreateAddressObject(self, deviceName, deviceGroupName, new_address):
        """
        Create a new address object
        :param deviceName: {str} Device name
        :param deviceGroupName: {str} device group to which the objects are attached
        :param new_address: {str} the new address to create
        :return: True if succuss, exception otherwise
        """
        xpath = f"/config/devices/entry[@name='{deviceName}']/device-group/entry[@name='{deviceGroupName}']/address"

        addresses = self.FindAddresses(deviceName, deviceGroupName)

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

        request_path = f"{self.server_address}/?type=config&action=set&xpath={xpath}&element={element_value}"

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
        if "success" in str(response.content, "utf-8"):
            return True
        elif (
            response.content
            == '<response status="unauth" code="16"><msg><line>Unauthorized request</line></msg></response>'
        ):
            raise PanoramaException("Unauthorized request")
        else:
            raise PanoramaException(f"Invalid Response: {response.content}")

    @staticmethod
    def chunks(l, n):
        # For item i in a range that is a length of l,
        for i in range(0, len(l), n):
            # Create an index range for l of n items:
            yield l[i : i + n]

    def get_log_entities_from_json(self, log_entities_json):
        """
        Get log entity from json
        :param log_entities_json: {list} Log entities json.
        :return: {LogEntity}
        """
        return self.parser.get_log_entities_from_json(log_entities_json)

    def build_query_from_ip_pair(self, source_ip, destination_ip):
        """
        Build query from ip pair
        :param source_ip: {str} Source IP.
        :param destination_ip: {str} Destination IP.
        :return: {str} query for API
        """
        return f"(src eq '{source_ip}') and (dst eq '{destination_ip}')"

    def build_api_query(self, query, max_hours_backwards):
        """
        Build api query
        :param query: {str} Specify what query filter should be used to return logs.
        :param max_hours_backwards: {str} Specify the amount of hours from where to fetch logs.
        :return: {str} Full query for API
        """
        collected_queries = []
        if query:
            collected_queries.append(f"({query})")
        if max_hours_backwards:
            time_query = f"(time_generated geq '{(convert_server_time_to_datetime(self.get_server_time(load_cached=True)) - datetime.timedelta( hours=max_hours_backwards)).strftime(TIME_FORMAT)}')"
            collected_queries.append(time_query)
        return " and ".join(collected_queries)

    def build_connector_query(self, query, severity, last_success_time):
        """
        Build api query
        :param query: {str} Specify what query filter should be used to return logs.
        :param severity: {str} Specify severity that will be used to fetch threat logs.
        :param last_success_time: {str} Specify the datetime from where to fetch logs.
        :return: {str} Full query for API
        """
        collected_queries = []
        if query:
            collected_queries.append(f"({query})")
        if severity:
            collected_queries.append(f"(severity geq {severity})")
        if last_success_time:
            time_query = f"(time_generated geq '{last_success_time}')"
            collected_queries.append(time_query)

        return " and ".join(collected_queries)

    def get_query_result(self, job_id, server_time=""):
        """
        Get query result
        :param job_id: {str} The job id to get result.
        :param server_time: {str} The time fetched from server.
        :return: {list} The list LogEntity for specified job id
        """
        params = {"type": "log", "action": "get", "job-id": job_id}

        response = self.session.get(self._get_full_url("main_endpoint"), params=params)

        self.is_valid_response(response)
        self.parser.set_response(response)
        progress = self.parser.get_query_result_progress()
        if self.parser.get_job_status() != JOB_FINISHED_STATUS:
            raise JobNotFinishedException(progress=progress)

        return self.parser.get_log_entities_from_query_result(server_time=server_time)

    def initialize_search_log_query(
        self, log_type, query, max_hours_backwards, max_logs_to_return
    ):
        """
        Initialize search log query
        :param log_type: {str} Specify which log type should be returned.
        :param query: {str} Specify what query filter should be used to return logs.
        :param max_hours_backwards: {str} Specify the amount of hours from where to fetch logs.
        :param max_logs_to_return: {str} Specify how many logs to return. Maximum is 1000.
        :return: {str} The job id for specified request
        """

        params = {"type": "log", "log-type": LOG_TYPE_MAP.get(log_type)}

        api_query = self.build_api_query(query, max_hours_backwards)
        if api_query:
            params["query"] = api_query

        if max_logs_to_return:
            params["nlogs"] = max_logs_to_return

        response = self.session.get(self._get_full_url("main_endpoint"), params=params)

        self.is_valid_response(response)
        self.parser.set_response(response)
        return self.parser.get_job_id()

    def get_threat_logs(
        self,
        existing_ids,
        log_type,
        query,
        last_success_time,
        max_logs_to_return,
        severity,
        server_time,
    ):
        """
        Initialize threat log connector query
        :param existing_ids: {list} The list of existing ids.
        :param log_type: {str} Specify which log type should be returned.
        :param query: {str} Specify what query filter should be used to return logs.
        :param severity: {str} Specify severity that will be used to fetch threat logs.
        :param last_success_time: {str} Specify the datetime from where to fetch logs.
        :param max_logs_to_return: {str} Specify how many logs to return. Maximum is 1000.
        :param server_time: {str} Current server time
        :return: {list} The list of LogEntities
        """

        params = {
            "type": "log",
            "log-type": LOG_TYPE_MAP.get(log_type),
            "dir": "forward",
        }

        api_query = self.build_connector_query(query, severity, last_success_time)
        if api_query:
            params["query"] = api_query

        results = self._paginate_results(
            method="GET",
            url=self._get_full_url("main_endpoint"),
            limit=max_logs_to_return,
            params=params,
            existing_ids=existing_ids,
            server_time=server_time,
        )

        return sorted(results, key=lambda threat: threat.receive_time)

    def get_server_time(self, load_cached=False):
        """
        Get server time
        :param load_cached: {bool} If False we will send request each time this action works, if True we will use already loaded time.
        :return: Current server time with timezone
        """
        if load_cached and self.server_time:
            return self.server_time

        params = {"type": "op", "cmd": "<show><clock></clock></show>"}
        response = self.session.get(self._get_full_url("main_endpoint"), params=params)
        self.is_valid_response(response)
        self.parser.set_response(response)
        self.server_time = self.parser.get_timezone_string()
        return self.server_time

    def _paginate_results(
        self,
        method,
        url,
        limit=LOGS_LIMIT,
        params=None,
        body=None,
        existing_ids=None,
        server_time="",
    ):
        """
        Paginate the results
        :param method: {unicode} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {unicode} The url to send request to
        :param limit: {int} The response limit
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param existing_ids: {list} The list of existing ids.
        :param server_time: {str} Current server time
        :return: {list} List of results
        """

        if params is None:
            params = {}
        if existing_ids is None:
            existing_ids = []

        results = self._fetch_results(
            method=method,
            url=url,
            params=params,
            body=body,
            existing_ids=existing_ids,
            server_time=server_time,
        )
        if not results:
            return []

        params.update({"nlogs": max(limit, LOGS_LIMIT), "skip": 0})

        while True:
            if len(results) >= limit:
                break

            params.update({"skip": len(results)})
            last_result = self._fetch_results(
                method=method,
                url=url,
                params=params,
                body=body,
                existing_ids=existing_ids,
                server_time=server_time,
            )
            if not last_result:
                break
            results.extend(last_result)

        return results

    def _fetch_results(self, method, url, params, body, existing_ids, server_time):
        """
        Get query result
        :param method: {unicode} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {unicode} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param existing_ids: {list} The list of existing ids
        :param server_time: {str} Current server time
        :return: {list} The list of LogEntities
        """
        response = self.session.request(method, url, params=params, json=body)
        self.is_valid_response(response)
        self.parser.set_response(response)
        job_id = self.parser.get_job_id()
        while True:
            try:
                results = self.get_query_result(job_id=job_id, server_time=server_time)
                break
            except JobNotFinishedException as e:
                self.siemplify_logger.info(
                    f"Continuing processing query.... Progress {e.progress}%"
                )
                sleep(2)

        return self.panorama_common.filter_old_ids(
            threats=results, existing_ids=existing_ids
        )

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
