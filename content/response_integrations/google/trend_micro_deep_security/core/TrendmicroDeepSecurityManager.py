# ============================================================================#
# title           :TrendmicroDeepSecurityManager.py
# description     :This Module contain all Trend micro operations functionality
# author          :zivh@siemplify.co
# date            :09-30-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :11.1.230, on-premise
# doc : https://automation.deepsecurity.trendmicro.com/article/11_1/api-reference?platform=on-premise#operation/listPolicies
# doc2:
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests

# ============================== CONSTS ===================================== #
BASE_URL = "{0}/api/{1}"
COMPUTERS_URL = "computers"

# ============================= CLASSES ===================================== #


class TrendmicroManagerError(Exception):
    """
    General Exception for Trend micro manager
    """

    pass


class TrendmicroManager:
    """
    Trend micro Manager
    """

    def __init__(self, api_root, api_secret_key, api_version, verify_ssl=False):
        """
        :param api_secret_key:
        :param api_root: {string} https://<host or IP>:<port> (e.g. https://192.168.0.1:4119)
        :param verify_ssl: {boolean}
        :param api_version: {string} The version of the api being called (e.g. v1)
        """
        self.api_root = api_root
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "api-secret-key": api_secret_key,
                "api-version": api_version,
                "Content-Type": "application/json",
            }
        )

    def test_connectivity(self):
        """
        Check to see if the Manager is up and responding to requests by lists all computers
        """
        return self.get_all_computers()

    def get_all_computers(self):
        """
        lists all computers
        :return: list of computers (dicts)
        """
        url = BASE_URL.format(self.api_root, COMPUTERS_URL)
        computers_list = self.session.get(url)
        return self.validate_response(computers_list)

    def get_computer_id_by_name(self, computer_name):
        """
        Get all hosts and find id of specific host
        :param computer_name: {string}
        :return: {int} host id
        """
        url = BASE_URL.format(self.api_root, COMPUTERS_URL)
        computers_list = self.session.get(url)
        self.validate_response(computers_list)

        for computer in computers_list.json().get("computers"):
            if computer.get("hostName").lower() == computer_name.lower():
                return computer.get("ID")

        raise TrendmicroManagerError(f"Can not find {computer_name} computer.")

    def get_policy_id_by_name(self, policy_name):
        """
        Get all policies and find id of specific policy
        :param policy_name: {string}
        :return: {int} policy id
        """
        url = BASE_URL.format(self.api_root, "policies")
        policies_list = self.session.get(url)
        self.validate_response(policies_list)

        for policy in policies_list.json().get("policies"):
            if policy.get("name").lower() == policy_name.lower():
                return policy.get("ID")
        raise TrendmicroManagerError(f"Can not find {policy_name} policy.")

    def modify_computer(self, computer_id, data):
        """
        Modify a computer by ID
        :param computer_id: {int} the ID number of the computer
        :param computer_details: {dict} computer info
        :return: {dict} computer updated details
        """
        url = BASE_URL.format(self.api_root, f"{COMPUTERS_URL}/{computer_id}")

        response = self.session.post(url, json=data)
        self.validate_response(response)
        return response.json()

    def assign_policy_to_computers(self, policy_id, computer_id):
        """
        Assign the specified policy to the specified computers
        :param policy_id: {int} The ID numbers of the firewall rules to add
        :param computer_id: {int} the ID number of the computer
        :return: {dict} computer updated details
        """
        # Get computer payload
        computer_details = self.get_computer_info(computer_id)
        # Modify computer
        data = {"policyID": policy_id}
        return self.modify_computer(computer_id, data)

    def get_computer_info(self, computer_id):
        """
        Describe a computer by ID
        :param computer_id: {int} the ID number of the computer to describe
        :return: {dict} computer details
        """
        url = BASE_URL.format(self.api_root, f"{COMPUTERS_URL}/{computer_id}")

        response = self.session.get(url)
        self.validate_response(response)
        return response.json()

    def scan_computers_for_malware(self, computer_name):
        """
        Request a malware scan be run on the specified computers, by modify the computer
        TODO: is this the way? maybe change the policy ID or state of intrusionPrevention/firewall?
        :param computer_name: {string} computer display name
        :param computer_name: {string} computer display name
        :return: {dict} computer updated details
        """
        # Get computer ID
        computer_id = self.get_computer_id_by_name(computer_name)
        # Get computer payload
        data = {"antiMalware": {"state": "on"}}
        # Modify computer
        return self.modify_computer(computer_id, data)

    def get_all_security_profiles(self):
        """
        Get all of the policies from Deep Security
        :return: list of policies (dicts)
        """
        url = BASE_URL.format(self.api_root, "policies")

        response = self.session.get(url)
        self.validate_response(response)
        return response.json().get("policies")

    @staticmethod
    def build_csv(policies_list):
        """
        Build csv table from policies list
        :param policies_list: {list} of policies {dict}
        :return: {list} summary from the policies
        """
        csv_results = []
        for policy in policies_list:
            csv_results.append(
                {
                    "Name": policy.get("name"),
                    "Description": policy.get("description"),
                    "ID": policy.get("ID"),
                }
            )
        return csv_results

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise TrendmicroManagerError(f"{e}. {response.content}.")


if __name__ == "__main__":
    pass
