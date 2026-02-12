# ==============================================================================
# title           :NSMManager.py
# description     :This Module contain all NSM API functionality
# author          :itaih@siemplify.co
# date            :2-1-2018
# python_version  :2.7
# ==============================================================================

# =====================================
#            REQUIREMENTS             #
# =====================================
# Firewall policy dedicated for Siemplify.
# List of sensor names which contain the policy.

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import base64
import copy
import datetime
import urllib.parse

import requests

# =====================================
#               CONSTS                #
# =====================================
RULE_NAME_TIME_FORMAT = "%Y-%m-%d %H_%M_%S.%f"  # c#: "yyyy-MM-dd HH_mm_ss.ff"
RULE_OBJEST_NAME_PREFIX = "Siemplify_Block"
MAX_ADDRESSES_PER_RULE_OBJECT = 10
MAX_RULE_OBJECTS_PER_RULE = 10
# URLs
GET_SESSION_URL = "session"
CREATE_RULE_OBJECT_URL = "ruleobject"
GET_UPDATE_POLICY_URL = "firewallpolicy/{0}"  # {0} - Policy ID.
QUARANTINE_IP_URL = "sensor/{0}/action/quarantinehost"  # {0} - Sensor ID.
REQUEST_RULE_OBJECTS_IN_DOMAIN_URL = "domain/{0}/ruleobject?type=HOSTIPV4"  # {0} - Domain ID.
GET_POLICIES_URL = "domain/{0}/firewallpolicy"  # {0} - Domain ID.
UPDATE_RULE_OBJECT_URL = "ruleobject/{0}"  # {0} - Rule Object ID.
GET_SENSORS_URL = "sensors?domain={0}"  # {0} - Domain ID.
UPDATE_SENSOR_CONFIG_URL = "sensor/{0}/action/update_sensor_config"  # {0} - Sensor ID.
GET_ALERTS_BY_ID_URL = "alerts/{0}?sensorId={1}"  # {0} -  Alert ID, {1} - Sensor ID
# Headers
HEADERS = {
    "Accept": "application/vnd.nsm.v2.0+json",
    "Content-Type": "application/json",
    "NSM-SDK-API": "post64EncodedCredKey",
}

# Payloads
QUARANTINE_IP_PAYLOAD = {"IPAddress": "ip_address", "Duration": "duration"}

CREATE_RULE_OBJECT_PAYLOAD = {
    "RuleObjDef": {
        "ruleobjType": "HOST_IPV_4",
        "HostIPv4": {"hostIPv4AddressList": ["ip_address"]},
        "name": "rule_name",
        "description": "Siemplify Generated IPv4 block object",
        "domain": "domain_id",  # integer
        "visibleToChild": True,
    }
}

# For deploy changes.
UPDATE_SENSOR_CONFIG_PAYLOAD = {
    "isBotnetPushRequired": False,
    "isSSLPushRequired": False,
    "isSigsetConfigPushRequired": True,
    "pendingChanges": {
        "isConfigurationChanged": True,
        "isMalwareConfigurationChanged": False,
        "isBotnetConfigurationChanged": False,
        "isGloablPolicyConfigurationChanged": True,
        "isSSLConfigurationChanged": False,
        "isSignatureSetConfigurationChanged": True,
        "isPolicyConfigurationChanged": True,
    },
}

UPDATE_RULE_OBJECT_PAYLOAD = {"RuleObjDef": {}}  # {} - Must be rule object json.

RULE_OBJECT_TO_PUSH = {"RuleObjectId": "", "Name": "", "RuleObjectType": ""}


# =====================================
#              CLASSES                #
# =====================================
class NSMManagerException(Exception):
    """
    NSM manager custom exception.
    """

    pass


class NsmManager:
    def __init__(
        self,
        api_root,
        username,
        password,
        domain_id,
        siemplify_policy_name,
        sensors_names_string_list,
        siemplify_rules_description="",
        ignore_ssl=True,
    ):
        # User Input Parameters.
        self.api_root = api_root if api_root[-1] == "/" else api_root + "/"
        self.domain_id = domain_id
        self.siemplify_policy_name = siemplify_policy_name
        self.sensors_names_string_list = sensors_names_string_list
        self.siemplify_rules_description = siemplify_rules_description
        # Dynamic parameters.(Set session)
        self.session = requests.session()
        self.session.verify = not ignore_ssl
        # Set session headers.
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["NSM-SDK-API"] = self.get_token(username, password)

    def get_token(self, username, password):
        """
        Obtain NSM connection token.
        :param username:  {string}
        :param password: {string}
        :param ignore_ssl: {bool}
        :return: token {string}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SESSION_URL)
        # Organize post base64 key.
        post_64_cred_key = base64.b64encode(bytes(f"{username}:{password}".encode("utf-8")))
        # Organize request headers.
        headers = HEADERS
        headers["NSM-SDK-API"] = post_64_cred_key

        response = self.session.get(request_url, headers=headers)
        self.response_validation(response)
        # Fetch login params.
        session = response.json()["session"]
        user_id = response.json()["userId"]
        # Form session key
        post_64_cred_session_key = base64.b64encode(bytes(f"{session}:{user_id}"))

        return post_64_cred_session_key

    @staticmethod
    def response_validation(response):
        """
        Validation of a HTTP response.
        :param response: HTTP response object {HTTP response}
        :return: {void}
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            raise NSMManagerException(f"Error: {err}, Content: {response.content}")

    def get_rule_objects(self):
        """
        Get all rule objects for configured domain.
        :return:  list of rule objects {list}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, REQUEST_RULE_OBJECTS_IN_DOMAIN_URL.format(self.domain_id)
        )
        response = self.session.get(request_url)
        self.response_validation(response)

        return response.json()["RuleObjDef"]

    def get_firewall_policy_object(self, policy_name):
        """
        Get firewall policy information.
        :param policy_name: NSM policy name {string}
        :return: policy information {dict}
        """
        policy_id = self.get_policy_id_by_name(policy_name)
        request_url = urllib.parse.urljoin(self.api_root, GET_UPDATE_POLICY_URL.format(policy_id))
        response = self.session.get(request_url)
        self.response_validation(response)
        return response.json()

    def get_all_sensors_by_domain_id(self, domain_id):
        """
        Get all sensors for domain.
        :param domain_id: NSM domain id {string}
        :return: list of dicts when each is a sensor data {list}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SENSORS_URL.format(domain_id))
        response = self.session.get(request_url)
        self.response_validation(response)

        return response.json()["SensorDescriptor"]

    def get_policy_id_by_name(self, policy_name):
        """
        Get policy ID by its name.
        :param policy_name: firewall policy name {string}
        :return: policy id {integer}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_POLICIES_URL.format(self.domain_id))
        response = self.session.get(request_url)
        # Validate response.
        self.response_validation(response)
        # Run over policies -> Has to fetch all the policies
        # and find the suitable one by running over them.
        for policy in response.json()["FirewallPoliciesForDomainResponseList"]:
            if policy["policyName"] == policy_name:
                return policy["policyId"]

    def create_new_rule_object(self, ip_address):
        """
        Create new firewall rule object(IP block type)
        :param ip_address: IP address to block {string}
        :return: rule object data {dict}
        """
        request_url = urllib.parse.urljoin(self.api_root, CREATE_RULE_OBJECT_URL)
        payload = copy.deepcopy(CREATE_RULE_OBJECT_PAYLOAD)
        payload["RuleObjDef"]["HostIPv4"]["hostIPv4AddressList"][0] = ip_address
        payload["RuleObjDef"]["name"] = (
            f"{RULE_OBJEST_NAME_PREFIX}_{datetime.datetime.now().strftime(RULE_NAME_TIME_FORMAT)}"
        )
        payload["RuleObjDef"]["domain"] = int(self.domain_id)

        response = self.session.post(request_url, json=payload)
        self.response_validation(response)
        # Form rule object.
        rule_object = payload["RuleObjDef"]
        rule_object["obj_id"] = response.json()["createdResourceId"]

        return rule_object

    def get_policy_member_rules(self, policy_name):
        """
        Get list of rules which are member of the configured policy.
        :param policy_name: policy's name {string}
        :return: policy members {list}
        """
        # Define result variable.
        member_rules = []
        # Get the firewall policy object.
        firewall_policy = self.get_firewall_policy_object(policy_name)
        # Running over member rules and fetching only the rules that belong to Siemplify by checking the description.
        for member_rule in firewall_policy["MemberDetails"]["MemberRuleList"]:
            # Rule created manually each contains 10x10 addresses.
            if (
                member_rule["Description"]
                .lower()
                .startswith(self.siemplify_rules_description.lower())
            ):
                member_rules.append(member_rule)
        return member_rules

    def is_rule_object_part_of_the_policy(self, rule_object_id):
        """
        Check if rule is contained at the configured policy.
        :param rule_object_id: an rule object id {string}
        :return: {bool}
        """
        # Get list of rules which are members of the policy.
        policy_member_rules = self.get_policy_member_rules(self.siemplify_policy_name)

        # Run over policy member rules.
        for member_rule in policy_member_rules:
            for rule_object in member_rule["SourceAddressObjectList"]:
                if rule_object["RuleObjectId"] == rule_object_id:
                    return True
        # If not found return false.
        return False

    def get_rule_object_from_policy_by_ip_address(self, ip_address):
        """
        Get rule object which is related to an specific ip address.
        :param ip_address: IP address to get the rule object by {string}
        :return: rule object {dict}
        """
        rule_objects = self.get_rule_objects()
        for rule_object in rule_objects:
            # Validate rule is created by Siemplify and Validate ip address exists in rule.
            if (
                rule_object["name"].lower().startswith(RULE_OBJEST_NAME_PREFIX.lower())
                and ip_address in rule_object["HostIPv4"]["hostIPv4AddressList"]
                and self.is_rule_object_part_of_the_policy(rule_object["ruleobjId"])
            ):
                return rule_object

    def get_rule_objects_by_name_prefix(self, prefix):
        """
        Get rule objects which name starts with prefix.
        :param prefix: rule object name prefix {string}
        :return: list of dicts when each one is a rule object {list}
        """
        result_rule_objects = []
        rule_objects_list = self.get_rule_objects()
        # Run over rule object and check if it's name contains the prefix.
        for rule_object in rule_objects_list:
            if rule_object["name"].lower().startswith(prefix.lower()):
                result_rule_objects.append(rule_object)

        return result_rule_objects

    def get_available_rule_object(self):
        """
        Get rule object that's ip addresses block list is not full.
        :return: rule object {dict}
        """
        siemplify_rule_objects = self.get_rule_objects_by_name_prefix(RULE_OBJEST_NAME_PREFIX)
        # Run over Siemplify rule objects.
        for siemplify_rule_obj in siemplify_rule_objects:
            # Check the amount of ip addresses.
            if (
                len(siemplify_rule_obj["HostIPv4"]["hostIPv4AddressList"])
                < MAX_ADDRESSES_PER_RULE_OBJECT
            ):
                # Validate rule is part of the policy.
                if self.is_rule_object_part_of_the_policy(siemplify_rule_obj["ruleobjId"]):
                    return siemplify_rule_obj

    def add_rule_object_to_firewall_policy(self, rule_object):
        """
        Update firewall policy by inserting new rule object.
        :param rule_object: rule object {dict}
        :return: is success {bool}
        """
        available_rule_found = False
        policy_id = self.get_policy_id_by_name(self.siemplify_policy_name)
        policy_object = self.get_firewall_policy_object(self.siemplify_policy_name)

        # Form rule object for policy update.
        rule_object_to_push = copy.deepcopy(RULE_OBJECT_TO_PUSH)
        rule_object_to_push["RuleObjectId"] = rule_object["obj_id"]
        rule_object_to_push["Name"] = rule_object["name"]
        rule_object_to_push["RuleObjectType"] = rule_object["ruleobjType"]

        # Run over policy member rules.
        # Update policy object -> The loop is for finding the spesific avilable rule in a policy object.
        for rule in policy_object["MemberDetails"]["MemberRuleList"]:
            # Policy rules total number is limited to 10
            if (
                len(rule["SourceAddressObjectList"]) < MAX_RULE_OBJECTS_PER_RULE
                and len(rule["DestinationAddressObjectList"]) < MAX_RULE_OBJECTS_PER_RULE
            ):
                # check if object rule does not already exists in rule.
                for rule_obj in rule["SourceAddressObjectList"]:
                    if rule_object["name"] == rule_obj["Name"]:
                        # Return true if rule already exists(IP already blocked.)
                        return True

                rule["SourceAddressObjectList"].append(rule_object_to_push)
                rule["DestinationAddressObjectList"].append(rule_object_to_push)
                # Available rule found flag.
                available_rule_found = True
                break

        # Validate available rule found.
        if not available_rule_found:
            raise NSMManagerException(
                f"No available rule found in policy: {self.siemplify_policy_name} "
            )
        else:
            # If available rule found update.
            request_url = urllib.parse.urljoin(
                self.api_root, GET_UPDATE_POLICY_URL.format(policy_id)
            )
            response = self.session.put(request_url, json=policy_object)
            self.response_validation(response)

        # Return positive result.
        return True

    def update_existing_rule_object(self, rule_object, ip_address):
        """
        Update existing rule object.
        :param rule_object: rule object {dict}
        :param ip_address: ip address to block {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, UPDATE_RULE_OBJECT_URL.format(rule_object["ruleobjId"])
        )
        payload = copy.deepcopy(UPDATE_RULE_OBJECT_PAYLOAD)
        payload["RuleObjDef"].update(rule_object)
        # Insert IP address to the rule object/payload.
        if ip_address not in payload["RuleObjDef"]["HostIPv4"]["hostIPv4AddressList"]:
            payload["RuleObjDef"]["HostIPv4"]["hostIPv4AddressList"].append(ip_address)

        response = self.session.put(request_url, json=payload)
        self.response_validation(response)

        return True

    def remove_ip_from_rule_object(self, rule_object, ip_address):
        """
        Remove an IP address from rule object's IPs to block list.
        :param rule_object: rule object {dict}
        :param ip_address: ip address {string}
        :return: is success {bool}
        """

        request_url = urllib.parse.urljoin(
            self.api_root, UPDATE_RULE_OBJECT_URL.format(rule_object["ruleobjId"])
        )
        payload = copy.deepcopy(UPDATE_RULE_OBJECT_PAYLOAD)
        payload["RuleObjDef"].update(rule_object)
        # Insert IP address to the rule object/payload.
        if ip_address in payload["RuleObjDef"]["HostIPv4"]["hostIPv4AddressList"]:
            # Remove ip from list.
            payload["RuleObjDef"]["HostIPv4"]["hostIPv4AddressList"].remove(ip_address)
            # Get response.
            response = self.session.put(request_url, json=payload)
            # Validate response.
            self.response_validation(response)
        # Return positive output.
        return True

    def remove_rule_object_from_policy_rule(self, rule_object):
        """
        Remove rule object from policy rule member.
        :param rule_object: a dict which represent rule object object {dict}
        :return: is success {bool}
        """
        policy_id = self.get_policy_id_by_name(self.siemplify_policy_name)
        policy_object = self.get_firewall_policy_object(self.siemplify_policy_name)
        # Run on policy member rules.
        for rule in policy_object["MemberDetails"]["MemberRuleList"]:
            # Validate rule is created by Siemplify.
            if rule["Description"].lower().startswith(self.siemplify_rules_description.lower()):
                # Validate IP exists in rule object.
                for rule_obj in rule["SourceAddressObjectList"]:
                    if rule_obj["RuleObjectId"] == rule_object["ruleobjId"]:
                        # Remove rule object.
                        rule["SourceAddressObjectList"].remove(rule_obj)
                        rule["DestinationAddressObjectList"].remove(rule_obj)

        request_url = urllib.parse.urljoin(self.api_root, GET_UPDATE_POLICY_URL.format(policy_id))

        response = self.session.put(request_url, json=policy_object)

        self.response_validation(response)

        return True

    def delete_rule_object(self, rule_object):
        """
        Delete rule object from NSM.
        :param rule_object: rule object {dict}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, UPDATE_RULE_OBJECT_URL.format(rule_object["ruleobjId"])
        )
        response = self.session.delete(request_url, json=rule_object)
        self.response_validation(response)

        return True

    def update_sensor_config(self, sensor_id):
        """
        Update sensor config.
        :param sensor_id: NSM sensor id {string}
        :return: is success {bool}
        """
        request_url = urllib.parse.urljoin(
            self.api_root, UPDATE_SENSOR_CONFIG_URL.format(sensor_id)
        )
        response = self.session.put(request_url, json=UPDATE_SENSOR_CONFIG_PAYLOAD)
        self.response_validation(response)

        return True

    def get_sensor_id_by_name(self, sensor_name):
        """
        Get sensor id by it's name.
        :param sensor_name: sensor name {string}
        :return: sensor id {string}
        """
        sensors_descriptors = self.get_all_sensors_by_domain_id(self.domain_id)

        for sensor in sensors_descriptors:
            if sensor["name"] == sensor_name:
                return str(sensor["sensorId"])

    # Main Functions.
    def quarantine_ip(self, sensor_id, ip_address, duration):
        """
        Quarantine ip address in McAfee NSM.
        :param sensor_id: sensor's id {string}
        :param ip_address: IP address to quarantine {string}
        :param duration: for how much time to quarantine the address {string}
        :return: True if action succeed else exception will be thrown.
        """
        request_url = urllib.parse.urljoin(self.api_root, QUARANTINE_IP_URL.format(sensor_id))
        payload = copy.deepcopy(QUARANTINE_IP_PAYLOAD)
        payload["IPAddress"] = ip_address
        payload["Duration"] = duration
        response = self.session.post(request_url, json=payload)
        self.response_validation(response)

        return True

    def is_ip_blocked(self, ip_address):
        """
        Check if ip address is already blocked in NSM.
        :param ip_address: IP address to check if blocked {string}
        :return: is blocked result {bool}
        """
        # Get rule object for ip address.
        rule_object = self.get_rule_object_from_policy_by_ip_address(ip_address)

        # If object received, the address is blocked.
        if rule_object:
            return True
        return False

    def block_ip(self, ip_address):
        """
        Block an IP address at NSM.
        :param ip_address: IP address to block {string}
        :return: is block succeed {bool}
        """
        # Validate if already blocked.
        if not self.is_ip_blocked(ip_address):
            # Get available rule object(Not full).
            rule_object = self.get_available_rule_object()
            if rule_object:
                # Update existing available rule object.
                self.update_existing_rule_object(rule_object, ip_address)
            else:
                # Create new rule object.
                rule_object = self.create_new_rule_object(ip_address)
                # Update firewall policy.
                self.add_rule_object_to_firewall_policy(rule_object)

        return True

    def release_ip(self, ip_address):
        """
        Unblock blocked IP address.
        :param ip_address: ip address {string}
        :return: is success {bool}
        """
        rule_object = self.get_rule_object_from_policy_by_ip_address(ip_address)

        # if rule object contains one address delete it else delete the ip from it.
        if rule_object:
            if len(rule_object["HostIPv4"]["hostIPv4AddressList"]) > 1:
                self.remove_ip_from_rule_object(rule_object, ip_address)
            else:
                # If the rule object is empty remove it from policy and delete it.
                self.remove_rule_object_from_policy_rule(rule_object)
                self.delete_rule_object(rule_object)

        return True

    def deploy_changes(self):
        """
        Deploy all configuration changes for sensor.
        :return: return true if deploy changes succeed {bool}
        """
        # Get the names of the sensors that hash to be updated.
        sensors_to_update_list = self.sensors_names_string_list.split(",")
        # Update sensors.
        for sensor_name in sensors_to_update_list:
            # Get sensor ID.
            sensor_id = self.get_sensor_id_by_name(sensor_name)
            # Update sensor.
            self.update_sensor_config(sensor_id)

        return True

    def get_alert_info_by_id(self, alert_id, sensor_name):
        """
        Get alert info data by alert id.
        :param alert_id: alert's id {string}
        :param sensor_name: sensor name {string}
        :return: alert info data {dict}
        """
        sensor_id = self.get_sensor_id_by_name(sensor_name)
        request_url = urllib.parse.urljoin(
            self.api_root, GET_ALERTS_BY_ID_URL.format(alert_id, sensor_id)
        )
        response = self.session.get(request_url)
        self.response_validation(response)
        return response.json()

    def logout(self):
        """
        End session with NSM
        :return: {void}
        """
        request_url = urllib.parse.urljoin(self.api_root, GET_SESSION_URL)
        if self.session:
            response = self.session.delete(request_url)
            self.response_validation(response)
        else:
            raise NSMManagerException("Logout attempt refused. No active session")


#
