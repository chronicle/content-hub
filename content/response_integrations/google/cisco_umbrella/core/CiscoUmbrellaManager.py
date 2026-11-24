# ==============================================================================
# title           :DomainToolsManagers.py
# description     :This Module contain all Cisco Umbrella operations functionality.
# author          :nikolay.ryagin@gmail.com
# date            :12-14-17
# python_version  :2.7
# libraries       : -
# requirements    :
# product_version : 1.1
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================

from __future__ import annotations
from urllib.parse import urljoin
from urllib.parse import urlparse

from requests import Session
from cisco_umbrella.core import utils
from cisco_umbrella.core.exceptions import CiscoUmbrellaManagerError
from soar_sdk.SiemplifyDataModel import EntityTypes


class CiscoUmbrellaManager:
    """
    The Class provides the general interface to make requests on Cisco Umbrella Investigate.
    """

    def __init__(self, token, url, session=None):
        """
        It defines a session.
        :param url: 'https://investigate.api.umbrella.com'
        :param token: access token, it should be configure from your account settings.
        :param session: none
        """

        self.url = url

        if token:
            self.headers = self._getHeader(token)
        else:
            self.headers = self._getSimpleHeader()

        if session is None:
            session = Session()

        self._session = session
        self._token = None

    def _request(self, name, **kwargs):
        """
        Make GET/ POST requests to the service.
        :param name: request type
        :param kwargs: additional params
        :return: JSON
        """

        url = urljoin(self.url, f"{name}")

        if kwargs.get("data") or kwargs.get("json") or kwargs.get("files"):
            r = self._session.post(url, headers=self.headers, verify=False, **kwargs)
        elif kwargs.get("delete"):
            kwargs = {}
            r = self._session.delete(url, headers=self.headers, verify=False, **kwargs)
        else:
            r = self._session.get(url, headers=self.headers, verify=False, **kwargs)

        # In case no results were found
        if r.status_code == 404:
            return None

        # 'Additional information can be found at https://docs.umbrella.com/developer/investigate-api/error-handling-1/'
        try:
            r.raise_for_status()
        except Exception as e:
            raise CiscoUmbrellaManagerError(f"{e}, {e.response.content}")

        try:
            return r.json()
        except Exception as e:
            return None

    def _getHeader(self, token):
        """
        Make header with an access token.
        :param token: access token
        :return: header
        """

        return {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    def _getSimpleHeader(self):
        """

        :return:
        """

        return {"Content-Type": "application/json"}

    def __call__(self, name, **kwargs):
        """
        Make API call by calling the instance.
        :param name: request type
        :param kwargs: additional params
        :return: JSON
        """
        return self._request(name, **kwargs)


class CiscoUmbrellaIvestigate:
    """
    Responsible for all Cisco Umbrella Investigate operations functionality.
    https://docs.umbrella.com/developer/investigate-api/
    """

    def __init__(self, token):
        """
        Create an instance to define a client.
        :param url: 'https://investigate.api.umbrella.com'
        :param token: access token, it should be configure from your account settings.
        """
        self.url = "https://investigate.api.umbrella.com"
        self._client = CiscoUmbrellaManager(token, self.url)

    def client(self, url, **kwargs):
        """
        Use to make REST API calls.
        :param url: 'https://investigate.api.umbrella.com'
        :param kwargs: additional params
        :return: client session.
        """

        return self._client(url, **kwargs)

    def ping(self):
        """
        Integration connectivity test.
        :return:
        """
        response = self.client(f"/links/name/{'google.com'}.json")
        if response:
            return True
        else:
            return False

    def get_associated_domain(self, domain):
        """
        Show a list of domain names that have been frequently seen requested around the same time
        (up to 60 seconds before or after) as the given domain name, but that are not frequently associated with other domain names.
        :param domain: {string}
        :return: {list of strings} results
        """
        response = self.client(f"/links/name/{domain}.json")
        if response:
            list_output = []
            for x in response["tb1"]:
                list_output.append(x[0])
            return list_output
        raise CiscoUmbrellaManagerError("Unable to connect to the Cisco Umbrella API.")

    def get_associated_domain_csv(self, domain):
        """
        Transforms raw response to CSV list output.
        :param domain:
        :return: csv list output.
        """
        csv_output = ["Domains"]
        response = self.get_associated_domain(domain)
        if response:
            csv_output += response
            return csv_output
        else:
            return None

    def get_domain_security_info(self, domain):
        """
        Retrieve domain security information from OpenDNS, such as popularity, geodiversity, associated attacks etc.
        :return: {dict} results
        """
        response = self.client(f"/security/name/{domain}")
        if response:
            return response
        raise CiscoUmbrellaManagerError("Unable to connect to the Cisco Umbrella API.")

    def get_domain_status(self, entity):
        """
        Show whether a domain is malicious or not (1=malicious, -1=not malicious, 0=unknown), and its category
        :param domain: {string}
        :return: {boolean}
        """

        entity_identifier = str(utils.get_entity_original_identifier(entity)).lower()

        if entity.entity_type == EntityTypes.URL:
            parsed_url = urlparse(entity_identifier)
            entity_identifier = parsed_url.netloc or entity_identifier

        response = self.client(
            f"/domains/categorization/{entity_identifier}?showLabels"
        )

        if response:
            return response[entity_identifier]

    def get_domain_status_csv(self, domain):
        """
        :param domain:
        :return: CSV format string list.
        """
        csv_output = ["Key, Value"]
        response = self.get_domain_status(domain)
        if response:
            for key, val in response.items():
                if type(val) == list:
                    if val:
                        csv_output.append(f"{key}, {' | '.join(val)}")
                    else:
                        pass
                else:
                    csv_output.append(f"{key}, {str(val)}")
            return csv_output
        raise CiscoUmbrellaManagerError("Unable to connect to the Cisco Umbrella API.")

    def get_domain_status_dict(self, domain):
        """
        :param domain:
        :return: Dictionary format output.
        """
        dict_output = {}
        response = self.get_domain_status(domain)
        if response:
            for key, val in response.items():
                if type(val) == list:
                    dict_output[str(key)] = str(" , ".join(val))
                else:
                    dict_output[str(key)] = str(val)
            return dict_output
        raise CiscoUmbrellaManagerError("Unable to connect to the Cisco Umbrella API.")

    def get_malicious_domains(self, ip_address):
        """
        Show malicious domains associated to an IP address
        :param ip_address: {string}
        :return: {list of strings}
        """
        response = self.client(f"ips/{ip_address}/latest_domains")
        list_output = []
        if response:
            for x in response:
                list_output.append(x["name"])
            return list_output
        else:
            return None

    def get_malicious_domain_csv(self, ip_address):
        """
        :param ip_address:
        :return: CSV format string.
        """
        csv_output = ["Malicious Domains"]
        raw_response = self.get_malicious_domains(ip_address)

        if raw_response:
            csv_output += raw_response
            return csv_output
        raise CiscoUmbrellaManagerError("Unable to connect to the Cisco Umbrella API.")

    def get_whois(self, domain):
        """
        Run a whois query on OpenDNS for the given domain
        :param domain: {string}
        :return: {dict} query results
        """
        return self.client(f"/whois/{domain}?showLabels")

    def get_whois_csv(self, domain):
        """
        :param domain: entity identifier.
        :return: CSV format string list.
        """
        csv_output = ["key, Value"]
        response = self.get_whois(domain)
        if response:
            for key, val in response.items():
                if type(val) == list:
                    if val:
                        csv_output.append(f"{key}, {' | '.join(val)}")
                else:
                    csv_output.append(f"{key}, {str(val).replace(',', '|')}")
            return csv_output
        else:
            return None

    def get_whois_dict(self, domain):
        """
        :param domain: entity identifier.
        :return: key, value dictionary.
        """
        dict_output = self.get_whois(domain)
        if dict_output:
            return dict_output
        else:
            return None


class CiscoUmbrellaEnforcment:
    """
    Responsible for all Cisco Umbrella Enforcement operations functionality:
        - Add a domain to a customer list.
        - Delete a domain from a customer list.
        - Provide domains from a customer list.
    https://docs.umbrella.com/developer/enforcement-api/generic-event-format-field-descriptions2/
    """

    def __init__(self, token):
        """

        :param token:
        :param host:
        """
        self.token = f"?customerKey={token}"
        token = ""
        self.url = "https://s-platform.api.opendns.com"
        self._client = CiscoUmbrellaManager(token, self.url)

    def client(self, url, **kwargs):
        """

        :param url:
        :param kwargs:
        :return:
        """
        return self._client(url, **kwargs)

    def _isoTime(self, time):
        """

        :param time:
        :return:
        """
        return time.strftime("%Y-%m-%dT%H:%M:%S.0Z")

    def buildEvent(self, domain, time, **kwargs):
        """
        Methods builds Event according Cisco Umbrella requirements.
        :param domain: domain which should be added to a customer list.
        :param time: General time
        :param kwargs: https://docs.umbrella.com/developer/enforcement-api/generic-event-format-field-descriptions2/
        :return: {dict} Generic Event
        """

        if len(domain) == 0:
            raise CiscoUmbrellaManagerError("The domain parameter cannot be empty.")
        else:
            dstDomain = domain

        if "deviceId" in kwargs:
            deviceId = kwargs.get("deviceId")
        else:
            deviceId = "ba6a59f4-e692-4724-ba36-c28132c761de"

        if "deviceVersion" in kwargs:
            deviceVersion = kwargs.get("deviceVersion")
        else:
            deviceVersion = "13.7a"

        if "eventTime" in kwargs:
            eventTime = kwargs.get("eventTime")
        else:
            eventTime = self._isoTime(time)

        if "alertTime" in kwargs:
            alertTime = kwargs.get("alertTime")
        else:
            alertTime = self._isoTime(time)

        if "dstUrl" in kwargs:
            dstURL = kwargs.get("dstUrl")
        else:
            dstURL = domain

        event = {
            "deviceId": deviceId,
            "deviceVersion": deviceVersion,
            "eventTime": eventTime,
            "alertTime": alertTime,
            "dstDomain": dstDomain,
            "dstUrl": dstURL,
            "protocolVersion": "1.0a",
            "providerName": "Security Platform",
        }

        if "dstIp" in kwargs:
            event["dstIp"] = kwargs.get("dstIp")
        if "disableDstSafeguards" in kwargs:
            event["disableDstSafeguards"] = kwargs.get("disableDstSafeguards")
        if "eventSeverity" in kwargs:
            event["eventSeverity"] = kwargs.get("eventSeverity")
        if "eventType" in kwargs:
            event["eventType"] = kwargs.get("eventType")
        if "eventDescription" in kwargs:
            event["eventDescription"] = kwargs.get("eventDescription")
        if "eventHash" in kwargs:
            event["eventHash"] = kwargs.get("eventHash")
        if "fileName" in kwargs:
            event["fileName"] = kwargs.get("fileName")
        if "fileHash" in kwargs:
            event["fileHash"] = kwargs.get("fileHash")
        if "externalURL" in kwargs:
            event["externalURL"] = kwargs.get("externalURL")
        if "src" in kwargs:
            event["src"] = kwargs.get("src")

        return event

    def addDomain(self, data):
        """
        Add domain to organizational domain list
        :param data: {dict} Use Build Event functions to build data according Cisco Umbrella requirements.
        :return: {boolean} is_success
        """

        response = self.client(f"/1.0/events{self.token}", json=data)
        if not response:
            raise CiscoUmbrellaManagerError("Destination server is unavailable.")

    def getAllDomains(self):
        """
        Methods provides domains included to the customer list. Max values is restricted to 200.
        :return:
        """

        response = self.client(f"/1.0/domains{self.token}")
        if response:
            return response["data"]

    def deleteDomain(self, domain):
        """
        Delete domain from organizational domain list
        :param domain: {string}
        :return: {boolean} is_success
        """
        # API endpoint for deleting domains is different from the others and it does not return the status of the action
        try:
            self.client(f"/1.0/domains/{domain}{self.token}", delete="delete")
        except Exception as e:
            raise CiscoUmbrellaManagerError("Destination server is unavailable.")
