# coding=utf-8
# ============================================================================#
# title           :CarbonBlackDefenseManager.py
# description     :This Module contain all Carbon Black Defense operations functionality
# author          :avital@siemplify.co
# date            :08-10-2020
# python_version  :3.7
# libreries       :cbapi
# requirments     :
# product_version :1.0
# ============================================================================#

from __future__ import annotations
import requests
from cbapi import CbDefenseAPI
from cbapi.defense import Device
from .CBDefenseParser import CBDefenseParser

# CB API timeframe error - there is a problem with
# random searchWindow (=timeframe) values. Some of the values are working,
# i.e: 3h, 1d, 2w... but others do not (including exmaples from api docs)
# No solution is possible from our side.
TIMEFRAME = "3h"
POLICY_URL = "{0}/integrationServices/v3/policy/{1}"
RULE_IN_POLICY_URL = "{0}/integrationServices/v3/policy/{1}/rule/{2}"
POLICY_DEFAULT_VERSION = 2
RESPONSE_SUCCESS = "success"


class CBDefenseManagerException(Exception):
    """
    General Exception for CB Defense manager
    """

    pass


class CBDefenseManager:
    """
    CB Defense Manager
    """

    def __init__(self, server_address, api_key):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.headers = {"X-Auth-Token": api_key}

        # Connect
        self.cb_defense = CbDefenseAPI(url=server_address, token=api_key)
        self.parser = CBDefenseParser()

    def test_connectivity(self):
        try:
            url = f"{self.server_address}/integrationServices/v3/device"

            response = self.session.get(url)
            self.validate_response(response)
        except Exception as e:
            raise CBDefenseManagerException(
                f"Unable to connect to CB Defense. Please validate your credentials. "
                f"Error: {e}"
            )

    def get_device_data_by_ip(self, ip_address):
        """
        Get device data by ip address
        :param ip_address: The ip address
        :return: {datamodels.Device} Device info
        """
        url = f"{self.server_address}/integrationServices/v3/device"

        response = self.session.get(url, params={"ipAddress": ip_address})

        self.validate_response(response)
        devices = response.json()["results"]

        if devices:
            return self.parser.build_siemplify_device_obj(devices[0])

        raise CBDefenseManagerException(f"No device found for {ip_address}")

    def get_device_data_by_hostname(self, hostname):
        """
        Get device data by hostname
        :param hostname: The hostname
        :return: {datamodels.Device} Device info
        """
        url = f"{self.server_address}/integrationServices/v3/device"

        response = self.session.get(url, params={"hostNameExact": hostname})

        self.validate_response(response)
        devices = response.json()["results"]

        if devices:
            return self.parser.build_siemplify_device_obj(devices[0])

        raise CBDefenseManagerException(f"No device found for {hostname}")

    def get_device_data(self, device_id):
        """
        Get device data by device_id
        :param device_id: The device's id
        :return: {datamodels.Device} Device info
        """
        url = f"{self.server_address}/integrationServices/v3/device/{device_id}"

        response = self.session.get(url)

        self.validate_response(response)
        device = response.json()["results"]

        if device:
            return self.parser.build_siemplify_device_obj(device)

        raise CBDefenseManagerException(f"No device found for {device_id}")

    def get_processes_by_ip(self, ip, timeframe=TIMEFRAME):
        """
        Get processes by ip
        :param ip: The ip
        :param timeframe: Timeframe of the search
        :return: {[datamodels.Process]} Processes list
        """
        url = f"{self.server_address}/integrationServices/v3/process"

        response = self.session.get(
            url, params={"ipAddress": ip, "searchWindow": timeframe}
        )

        self.validate_response(response)

        return [
            self.parser.build_siemplify_process_obj(process)
            for process in response.json().get("results", [])
        ]

    def get_processes_by_hostname(self, hostname, timeframe=TIMEFRAME):
        """
        Get processes by hostname
        :param hostname: The hostname
        :param timeframe: Timeframe of the search
        :return: {[datamodels.Process]} Processes list
        """
        url = f"{self.server_address}/integrationServices/v3/process"

        response = self.session.get(
            url, params={"ownerNameExact": hostname, "searchWindow": timeframe}
        )

        self.validate_response(response)

        return [
            self.parser.build_siemplify_process_obj(process)
            for process in response.json().get("results", [])
        ]

    def change_policy(self, device_id, policy_name):
        """
        Change device's policy
        :param device_id: The device's id
        :param policy_name: The new policy name
        """
        device = Device(self.cb_defense, device_id)

        if not device:
            raise CBDefenseManagerException(f"Device {device_id} not found.")

        device.policyName = policy_name
        device.save()

    def get_events_by_ip(self, ip, timeframe=TIMEFRAME):
        """
        Get events by ip
        :param ip: The ip
        :param timeframe:  Timeframe of the search
        :return: {[datamodels.Event]} Events list
        """
        url = f"{self.server_address}/integrationServices/v3/event"

        response = self.session.get(
            url, params={"ipAddress": ip, "searchWindow": timeframe}
        )

        self.validate_response(response)

        return [
            self.parser.build_siemplify_event_obj(event)
            for event in response.json().get("results", [])
        ]

    def get_events_by_hostname(self, hostname, timeframe=TIMEFRAME):
        """
        Get events by hostname
        :param hostname: The hostname
        :param timeframe:  Timeframe of the search
        :return: {[datamodels.Event]} Events list
        """
        url = f"{self.server_address}/integrationServices/v3/event"

        response = self.session.get(
            url, params={"hostNameExact": hostname, "searchWindow": timeframe}
        )

        self.validate_response(response)

        return [
            self.parser.build_siemplify_event_obj(event)
            for event in response.json().get("results", [])
        ]

    def change_device_status(self, device_id, status):
        """
        Change device's status
        :param device_id: {int} The device's id
        :param status: {string} The new status (e.g. REGISTERED)
        """
        device = Device(self.cb_defense, device_id)

        if not device:
            raise CBDefenseManagerException(f"Device {device_id} not found.")

        device.status = status
        device.save()

    def get_policies(self):
        """
        Get the list of policies available
        :return: {[datamodels.Policy]} Policies
        """
        url = POLICY_URL.format(self.server_address, "")
        response = self.session.get(url)
        self.validate_response(response)
        return [
            self.parser.build_siemplify_policy_obj(policy)
            for policy in response.json().get("results", [])
        ]

    def get_policy_by_id(self, policy_id):
        """
        Retrieve a policy object by ID
        :param policy_id: {int} policy id
        :return: {datamodels.Policy} policy object
        """
        url = POLICY_URL.format(self.server_address, policy_id)
        response = self.session.get(url)
        self.validate_response(response)
        return self.parser.build_siemplify_policy_obj(response.json()["policyInfo"])

    def create_new_policy(
        self,
        description,
        name,
        priority_level,
        policy_details={},
        version=POLICY_DEFAULT_VERSION,
    ):
        """
        Create a new Policy on the Cb Defense from a policy JSON string.
        :param description:  A description of the policy (can be multiple lines)
        :param name: A one-line name for the policy
        :param version: Must be set to “2” for the current policy API
        :param priority_level: HIGH, MEDIUM or LOW - the priority score associated with
                               sensors assigned to this policy.
        :param policy_details: JSON object containing the policy details.
        :return: {int} new policy ID
        """
        # The new policy must be contained in a JSON object named policyInfo.
        policy_object = {
            "policyInfo": {
                "description": description,
                "name": name,
                "policy": policy_details,
                "priorityLevel": priority_level,
                "version": version,
            }
        }
        url = POLICY_URL.format(self.server_address, "")
        response = self.session.post(url, json=policy_object)
        self.validate_response(response)
        if response.json()[RESPONSE_SUCCESS]:
            return response.json()["policyId"]

    def delete_policy(self, policy_name):
        """
        Delete a policy from the Cb Defense.
        May return an error if devices are actively assigned to the policy id requested
        for deletion.
        :param policy_name: {string} policy name
        :return: {boolean}
        """
        policy_id = self.get_policy_id_by_policy_name(policy_name)
        url = POLICY_URL.format(self.server_address, policy_id)
        response = self.session.delete(url)
        self.validate_response(response)
        return response.json()[RESPONSE_SUCCESS]

    def delete_rule_from_policy(self, policy_name, rule_id):
        """
        Removes a rule from an existing policy.
        :param policy_name: {string} policy name
        :param rule_id: {int} rule id
        :return: {boolean}
        """
        policy_id = self.get_policy_id_by_policy_name(policy_name)
        url = RULE_IN_POLICY_URL.format(self.server_address, policy_id, rule_id)
        response = self.session.delete(url)
        self.validate_response(response)
        return response.json()[RESPONSE_SUCCESS]

    def get_policy_id_by_policy_name(self, policy_name):
        """
        Retrieve policy ID by policy name
        :param policy_name: {string} policy name
        :return: {int} policy id
        """
        policies = self.get_policies()
        for policy in policies:
            if policy_name == policy.name:
                return policy.id
        raise CBDefenseManagerException(f"Can not find {policy_name} Policy.")

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise CBDefenseManagerException(f"{e}. {response.text}")
