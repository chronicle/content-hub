# ============================================================================#
# title           :TorManager.py
# description     :This Module contain all Tor operations functionality
# author          :avital@siemplify.co
# date            :17-06-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
import datetime

# ============================== CONSTS ===================================== #

TOR_EXIT_NODES_LIST = "https://check.torproject.org/exit-addresses"
EXIT_ADDRESS = "ExitAddress"

# ============================= CLASSES ===================================== #


class TorManagerError(Exception):
    """
    General Exception for Tor manager
    """

    pass


class TorManager:
    """
    Tor Manager
    """

    def __init__(self, use_ssl=False):
        self.session = requests.Session()
        self.session.verify = use_ssl

    def test_connectivity(self):
        """
        Test connectivity to Tor
        :return: {bool} True if connection successful, exception otherwise.
        """
        response = self.session.get(TOR_EXIT_NODES_LIST)
        self.validate_response(response, "Unable to connect to Tor")
        return True

    def get_todays_exit_nodes(self):
        """
        Get the list of today's exit nodes
        :return: {list} The list of exit nodes
        """
        response = self.session.get(TOR_EXIT_NODES_LIST)
        self.validate_response(response, "Unable to get exit nodes")

        # Return the Exit Nodes
        exit_nodes = set()
        decoded_content = response.content.decode("utf-8")
        for line in decoded_content.splitlines():
            # Get only address lines from today
            if EXIT_ADDRESS in line and datetime.date.today().isoformat() in line:
                try:
                    # Get the ip address
                    # A sample line is: 'ExitAddress 153.126.210.34 2018-06-17 02:09:01'
                    exit_nodes.add(line.split()[1])
                except:
                    # Line is corruped - skip
                    pass

        return list(exit_nodes)

    def is_exit_node(self, ip):
        """
        Check whether an ip is an exit node today
        :param ip: {str} The ip address to check
        :return: {bool} True if the ip is an exit node, False otherwise.
        """
        return ip in self.get_todays_exit_nodes()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise TorManagerError(f"{error_msg}: {error} {response.content}")


if __name__ == "__main__":
    tor_manager = TorManager()
    # a = tor_manager.is_exit_node('1.1.1.1')
    # b = tor_manager.is_exit_node('5.2.77.146')
    print("")
