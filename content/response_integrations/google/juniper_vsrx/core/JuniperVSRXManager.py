# ==============================================================================
# title           :JuniperVSRXManager.py
# description     :Juniper VSRX integration logic.
# author          :victor@siemplify.co
# date            :28-10-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
from jnpr.junos import Device
from jnpr.junos.utils.config import Config


# =====================================
#               CONSTS                #
# =====================================
# General
ADDRESS_RECORD_NAME_PATTERN = "siemplify-address-record-{0}"  # {0] - Target IP address.
DEFAULT_ADDRESS_MASK = "32"

# Formats and modes.
CONFIG_MODE = "exclusive"
CONFIG_FORMAT = {"format": "json"}
CONFIG_FILTER = "security/address-book"
COMMAND_FORMAT = "set"

# Commands
CREATE_ADDRESS_RECORD_COMMAND = (
    "set security address-book" " global address {0} {1}/32"
)  # {0} - Address record name, {1} - IP address.

CREATE_ADDRESS_RECORD_WITH_ZONE_COMMAND = (
    "set security zones" " security-zone {0}" " address-book address {1} {2}/32"
)  #  {0} -  Zone name, {1} - Address record name, {2} - IP address.

ADD_ADDRESS_RECORD_TO_AN_ADDRESS_SET_COMMAND = (
    "set security address-book global address-set" "  {0}  address {1}"
)  # {0} - Address set name, {1} - Address record name.
ADD_ADDRESS_RECORD_TO_AN_ADDRESS_SET_WITH_ZONE_COMMAND = (
    "set security"
    " zones security-zone {0}"
    " address-book address-set {1} address {2}"
)  #  {0} -  Zone name, {1} -  Address set name, {2} - Address record name.

DELETE_ADDRESS_RECORD_COMMAND = (
    "delete security address-book" " global address {0} {1}/32"
)  # {0} - Address record name, {1} - IP address.
DELETE_ADDRESS_RECORD_WITH_ZONE_COMMAND = (
    "delete security" " zones security-zone  {0}" " address-book address {1} {2}/32"
)  # {0} -  Zone name, {1} - Address record name, {2} - IP address.
DELETE_RECORD_FROM_SET_COMMAND = "delete security address-book global address-set {0} address {1}"  # {0} - Address set name, {1} - Address record name.
DELETE_RECORD_FROM_SET_WITH_ZONE_COMMAND = (
    "delete security zones security-zone"
    " {0} address-book address-set"
    " {1} address {2}"
)  # {0} -  Zone name, {1} - Address record name, {2} - IP address.


# =====================================
#              CLASSES                #
# =====================================
class JuniperVSRXManagerError(Exception):
    pass


class JuniperVSRXManager:
    def __init__(self, address, port, username, password):
        """
        :param address: {string} Host address or name.
        :param port: {string} API port.
        :param username: {string} Local username.
        :param password: {string} Local username password.
        """
        self.device = Device(host=address, user=username, passwd=password, port=port)
        self.config = Config(self.device, mode=CONFIG_MODE)

    def ping(self):
        """
        Check if connectivity with JuniperVSRX established.
        :return: {bool} True if connection is valid else False.
        """
        if self.device.probe():
            return True
        return False

    def add_ip_to_address_set(self, ip_address, address_set_name, zone=None):
        """
        Add an ip address to an address set
        :param ip_address: {string} Target IP address.
        :param address_set_name: {string} Target group name.
        :param zone: {string} Target security zone.
        :return: {Bool} True if succeed.
        """
        address_record_name = ADDRESS_RECORD_NAME_PATTERN.format(ip_address)
        if zone:
            self.config.load(
                CREATE_ADDRESS_RECORD_WITH_ZONE_COMMAND.format(
                    zone, address_record_name, ip_address
                ),
                format=COMMAND_FORMAT,
            )

            self.config.load(
                ADD_ADDRESS_RECORD_TO_AN_ADDRESS_SET_WITH_ZONE_COMMAND.format(
                    zone, address_set_name, address_record_name
                ),
                format=COMMAND_FORMAT,
            )
        else:
            self.config.load(
                CREATE_ADDRESS_RECORD_COMMAND.format(address_record_name, ip_address),
                format=COMMAND_FORMAT,
            )

            self.config.load(
                ADD_ADDRESS_RECORD_TO_AN_ADDRESS_SET_COMMAND.format(
                    address_set_name, address_record_name
                ),
                format=COMMAND_FORMAT,
            )
        return True

    def remove_ip_from_address_set(self, ip_address, address_set_name, zone=None):
        """
        Add an ip address to an address set
        :param ip_address: {string} Target IP address.
        :param address_set_name: {string} Target group name.
        :param zone: {string} Target security zone.
        :return: {Bool} True if succeed.
        """
        address_record_name = self.get_ip_record_name_by_ip(ip_address)
        if zone:
            self.config.load(
                DELETE_ADDRESS_RECORD_WITH_ZONE_COMMAND.format(
                    zone, address_record_name, ip_address
                ),
                format=COMMAND_FORMAT,
            )

            self.config.load(
                DELETE_RECORD_FROM_SET_WITH_ZONE_COMMAND.format(
                    zone, address_set_name, address_record_name
                ),
                format=COMMAND_FORMAT,
            )
        else:
            self.config.load(
                DELETE_ADDRESS_RECORD_COMMAND.format(address_record_name, ip_address),
                format=COMMAND_FORMAT,
            )

            self.config.load(
                DELETE_RECORD_FROM_SET_COMMAND.format(
                    address_set_name, address_record_name
                ),
                format=COMMAND_FORMAT,
            )
        return True

    def get_ip_record_name_by_ip(self, ip_address):
        """
        Get IP record name by ip address.
        :param ip_address: {string} IP address.
        :return: {string} IP record name.
        """
        result_data = self.device.rpc.get_config(
            filter_xml=CONFIG_FILTER, options=CONFIG_FORMAT
        )
        address_book = (
            result_data.get("configuration", {}).get("security", {}).get("address-book")
        )
        if address_book:
            addresses = address_book[0]
            address_with_mask = f"{ip_address}'\'{DEFAULT_ADDRESS_MASK}"
            for address_pair in addresses:
                if address_with_mask == address_pair.get("ip-prefix"):
                    return address_pair.get("name")
            raise JuniperVSRXManagerError(
                f'Error, not found name for IP "{ip_address}"'
            )
        raise JuniperVSRXManagerError(
            f'Error, not found addresses for IP "{ip_address}"'
        )

    def commit_config_changes(self):
        """
        Commit all changes made at the config.
        :return: {Bool} True if success.
        """
        self.config.commit()
        return True

    def close_session(self):
        """
        Close connection session.
        :return: {Bool} True if succeed.
        """
        self.device.close()
        return True
