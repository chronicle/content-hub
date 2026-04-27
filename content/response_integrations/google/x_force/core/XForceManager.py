# ==============================================================================
# title           : XForceManager.py
# description     : This Module contain all XForce cloud operations functionality
# author          : Ziv Hazan (zivh@siemplify.co)
# date            : 01-05-18
# python_version  : 2.7
# libraries       :
# requirements    : None
# product_version : 1.0
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================

from __future__ import annotations
import base64
import requests

# =====================================
#             CONSTANTS               #
# =====================================
ADDRESS = "https://api.xforce.ibmcloud.com"

NOT_FOUND_STATUS_CODE = 404
ACCESS_DENIED_ERROR = 403


# =====================================
#              CLASSES                #
# =====================================
class XForceManagerError(Exception):
    """
    General Exception for XForce manager
    """

    pass


class XForceNotFoundError(Exception):
    """
    General Exception for XForce not found (status code - 404)
    """

    pass


class XForceAccessDeniedError(Exception):
    """
    General Exception for XForce access was denied (status code - 403)
    """

    pass


class XForceManager:
    """
    Responsible for all XForce system operations functionality
    """

    def __init__(self, key, password, address=ADDRESS, verify_ssl=False):
        """
        The methods provide an instance of the XForceManager class and generates a token.
        :param key: {string} https://api.xforce.ibmcloud.com/doc/?#auth
        :param password: {string} https://api.xforce.ibmcloud.com/doc/?#auth
        :param address: {string} URL of IBM X-Force Manager
        :param verify_ssl: {boolean} False/tRUE
        """
        self.address = address
        self.token = base64.b64encode(f"{key}:{password}".encode("utf-8"))
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Basic {self.token}", "Accept": "application/json"}
        )
        self.session.verify = verify_ssl

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        res = self.get_ip_info("8.8.8.8")
        return True

    def get_ip_info(self, ip_address):
        """
        Get domain reputation from XForce
        :param ip_address: {string} The ip address
        :return: {dict} The ip address info
        """
        url = f'{self.address}/{"ipr"}/{ip_address}'
        response = self.session.get(url)
        self.validate_response(response)
        return response.json()

    def get_malware_for_ip(self, ip_address):
        """
        Returns the malware associated with the entered IP.
        :param ip_address: {string} The ip address
        :return: {dict} malware for ip
        """
        url = f'{self.address}/{"ipr/malware"}/{ip_address}'
        response = self.session.get(url)
        self.validate_response(response)
        return response.json()

    def get_ip_by_category(self, category):
        """
        Returns a list of IPs according to the category and date range.
        :param category: {string} categories for IPs:
        Spam, Anonymisation Services, Scanning IPs, Dynamic IPs, Malware, Bots, Botnet Command and Control Server
        :return: {dict} The attribute rows contains list of IPs that are in the specified category
        """
        url = f'{self.address}/{"ipr"}'
        response = self.session.get(url, params={"category": category})
        self.validate_response(response)
        return response.json()["rows"]

    def get_hash_info(self, file_hash):
        """
        Get domain reputation from XForce
        :param file_hash: {string} The file hash of the malware
        :return: {dict}  a malware report for the given file hash
        """
        url = f'{self.address}/{"malware"}/{file_hash}'
        response = self.session.get(url)
        self.validate_response(response)
        return response.json()

    def get_url_info(self, url):
        """
        Get url reputation from XForce
        :param url: {string} url For example, ibm.com, www.ibm.com/smarterplanet
        :return: {dict} URL report for the entered URL
        """
        url = f'{self.address}/{"url"}/{url}'
        response = self.session.get(url)
        self.validate_response(response)
        return response.json()

    def get_malicious_ips(self):
        """
        Get malicious ips in the last hour
        :return: {list} malicious ips in the last hour in specific category
        """
        url = f'{self.address}/{"statHistory/botnetcommandandcontrolserver"}'
        response = self.session.get(url)
        self.validate_response(response)
        return response.json()["ips"]

    @staticmethod
    def construct_malware_data(malware_details, entity_csv, entity):
        """
        construct each malware details
        :param malware_details: {dict} malware details
        :param entity_csv: {list} csv of specific entity with his malware details.
        :param entity: {entity object}
        :return: {list of dicts}
        """
        families_list = malware_details.get("family") or []
        families = "| ".join(str(family) for family in families_list)

        entity_csv.append(
            {
                "IP": entity.identifier,
                "MD5": malware_details.get("md5"),
                "Domain": malware_details.get("domain"),
                "First Seen": malware_details.get("firstseen"),
                "Last Seen": malware_details.get("lastseen"),
                "Count": malware_details.get("count"),
                "Schema": malware_details.get("schema"),
                "File Path": malware_details.get("filepath"),
                "URI": malware_details.get("uri"),
                "Origin": malware_details.get("origin"),
                "Families": families,
            }
        )
        return entity_csv

    @staticmethod
    def validate_response(response):
        """
        Check if request response is ok
        """
        try:
            if response.status_code == ACCESS_DENIED_ERROR:
                raise XForceAccessDeniedError("Error: Access denied.")

            if response.status_code == NOT_FOUND_STATUS_CODE:
                raise XForceNotFoundError("Error: Not found")

            response.raise_for_status()
        except requests.HTTPError as e:
            raise XForceManagerError(f"{e}. {response.content}")
