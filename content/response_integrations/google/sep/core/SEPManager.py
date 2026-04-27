# ============================================================================#
# title           :SCCMManager.py
# description     :This Module contain all SCCM operations functionality
# author          :avital@siemplify.co
# date            :28-01-2018
# python_version  :2.7
# libreries       :xmljson, urllib3
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import requests
import json
from defusedxml.ElementTree import fromstring
from xmljson import badgerfish as bf  # https://pypi.python.org/pypi/xmljson
from functools import reduce


# ============================= CLASSES ===================================== #

DEFAULT_DOMAIN = "Default"
STATUS = "status"
COMPLETED = ["2", "3"]
COMMAND = "command_id"
EMPTY_DOMAIN = " "

VALID_SCAN_TYPES = ["ScanNow_Quick", "ScanNow_Full", "ScanNow_Custom"]

VALID_UPDATE_SCAN_TYPES = [
    "Update_ScanNow_Quick",
    "Update_ScanNow_Full",
    "Update_ScanNow_Custom",
]

# Examples of usage are placed below
# the following methods were tested on Symantec Endpoint Protection Manager 14 MP2 build 2415


class SEPManagerException(Exception):
    pass


class SEP14Manager:

    def __init__(
        self,
        server_address,
        userName,
        password,
        domain=DEFAULT_DOMAIN,
        verify_ssl=False,
    ):
        """
        Initial method for SymantecEpConnect
        :param url: IP Address/ Hostname of SEP Manager Server and its port (Example: 18.194.154.150:8446)
        :param userName: Username and nothing else (It haven't tested with Active Directory account)
        :param password: Password and nothing else
        :param domain: Internal SEP Manager domain nature which is used to divide a zone of responsible
         between some of administrators, it's not Active Directory domain.
        """
        self.server_address = server_address
        self.userName = userName
        self.password = password
        if domain == EMPTY_DOMAIN:
            self.domain = DEFAULT_DOMAIN
        else:
            self.domain = domain

        self.session = requests.Session()
        self.session.verify = verify_ssl

        self.connect()
        self.domain_id = self.get_domain_id_by_name(domain)

    def connect(self):
        """
        REST API
        The method is used to connect SEP Manager and to receive access token.
        :return: :tuple: Access Token, Refresh Access Token
                 :int: Connection Error Code
        """
        data = {
            "username": self.userName,
            "password": self.password,
            "domain": self.domain,
        }

        headers = {"Content-Type": "application/json"}

        response = self.session.post(
            f"{self.server_address}/api/v1/identity/authenticate",
            json=data,
            headers=headers,
        )

        self.validate_response(response, "Unable to authenticate")

        responseData = response.json()
        self.token = responseData["token"]
        self.refreshToken = responseData["refreshToken"]

        self.json_headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        }

        self.soap_headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "text/xml",
        }

        return self.token, self.refreshToken

    def get_domain_id_by_name(self, domain_name):
        """
        Get domain ID by it's name.
        :param domain_name: {string} Domain ID.
        :return: {string} Domain ID
        """
        domains = self.getDomainList()
        for domain in domains:
            if domain.get("name") == domain_name and domain.get("id"):
                return domain.get("id")
        raise SEPManagerException("Failed fetching ID, domain not found.")

    def getComputerInfo(self, computer_name):
        """
        REST API
        The method allows to get data about endpoints based on its computer name.
        :param computer_name: computer name as it is in the SEP Manager
        :return: JSON data
        """
        endpoints = self.getEndpointList(computer_name)
        if endpoints:
            return endpoints[0]
        raise SEPManagerException(f'Failed fetching system info for "{computer_name}"')

    def getEndpointList(self, computer_name=None):
        """
        The method is used to get a list of endpoints which SEP Manager have.
        It's a wrap for getComputerInfo method with the pre-defined parameter "computerName" is equal wildcard.
        :param computer_name: computer name as it is in the SEP Manager
        :return: JSON data
        """
        if computer_name:
            url = f"{self.server_address}/api/v1/computers?computerName={computer_name}&domain={self.domain_id}"
        else:
            url = f"{self.server_address}/api/v1/computers?domain={self.domain_id}"

        response = self.session.get(url, headers=self.json_headers)

        self.validate_response(response, "Unable to get computers")

        if json.loads(response.text).get("content"):
            return response.json().get("content")

        if computer_name:
            raise SEPManagerException(
                f'Failed fetching endpoints for "computer_name" - {computer_name}'
            )
        else:
            raise SEPManagerException("Failed fetching endpoints.")

    def getGroupList(self):
        """
        REST API
        The method is used to get a list of group which SEP Manager have.
        :param domain: (optional)
        :return: JSON data
        """

        response = self.session.get(
            f"{self.server_address}/api/v1/groups?domains={self.domain}",
            headers=self.json_headers,
        )

        self.validate_response(response)
        totalResults = response.json()["totalElements"]

        response = self.session.get(
            f"{self.server_address}/api/v1/groups?domains={self.domain}&pageSize={totalResults}",
            headers=self.json_headers,
        )

        self.validate_response(response, "Unable to get group list")
        return response.json()["content"]

    def setQuarantineState(self, groupId, computerId, undo=True):
        """
        The method is used to quarantine/ unquarantine the SEP endpoint. It's internal method, use another ones to call it.
        :param groupId: The unique Id of group where SEP endpoint is placed.
        :param computerId: The unique Id of computer at SEP Manager.
        :param undo: If set true than endpoint will be unquarantine, in other way it will quarantine.
        :return: JSON data which contains GroupId and ComputerId
        """

        response = self.session.post(
            f"{self.server_address}/api/v1/command-queue/quarantine?group_ids={groupId}&computer_ids={computerId}&undo={undo}",
            headers=self.json_headers,
        )

        self.validate_response(response, f"Unable to quarantine {computerId}")
        return response.json()

    def quarantineEndpoints(self, groupId, computerId):
        """
        The method is used to define independent call for quarantine of endpoint.
        :param groupId: The unique Id of group where SEP endpoint is placed.
        :param computerId: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineState(groupId, computerId, False)

    def unQuarantineEndpoints(self, groupId, computerId):
        """
        The method is used to define independent call for quarantine of endpoint.
        :param groupId: The unique Id of group where SEP endpoint is placed.
        :param computerId: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineState(groupId, computerId, True)

    def clearXmlResponse(self, string):
        """
        The method is to clear a response from useless information which interrupts conversion to JSON.
        :param string: Response String
        :return: :string: Cleared string
        """

        list = [
            ' xmlns:S="http://schemas.xmlsoap.org/soap/envelope/"',
            ' xmlns:ns2="http://client.webservice.sepm.symantec.com/"',
            "S:",
            "ns2:",
        ]

        for x in list:
            string = string.replace(x, "")
        return string

    def getComputerIdByIP(self, ipAddress="*"):
        """
        SOAP Client
        The method is used to provide a computer Id in the SEPM Manager based on IP Address.
        :param ipAddress: the SEP endpoint's IP Address
        :return: :string: Computer Id
                 :int: Connection Error Code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <cli:getComputersByIP>
							 <!--Zero or more repetitions:-->
							 <ipAddresses>{ipAddress}</ipAddresses>
						  </cli:getComputersByIP>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/ClientService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(response, f"Unable to get computer by ip {ipAddress}")

        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))

        computers = data["Envelope"]["Body"]["getComputersByIPResponse"][
            "ComputerResult"
        ]["computers"]

        if isinstance(computers, list) and computers:
            # Multiple computers - get the first
            return computers[0]["computerId"]["$"]

        elif isinstance(computers, dict):
            # Single computer
            return computers["computerId"]["$"]

    def getComputerIdByComputerName(self, computerName="*"):
        """
        SOAP Client
        The method is used to provide computerId using computer name.
        :param computerName:
        :return: :string: Computer Id
                 :int: Connection Error Code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <cli:getComputersByHostName>
							 <!--Zero or more repetitions:-->
							 <computerHostNames>{computerName}</computerHostNames>
						  </cli:getComputersByHostName>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/ClientService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to get computer id by name {computerName}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))

        computers = data["Envelope"]["Body"]["getComputersByHostNameResponse"][
            "ComputerResult"
        ]["computers"]

        if isinstance(computers, list) and computers:
            # Multiple computers - get the first
            return computers[0]["computerId"]["$"]

        elif isinstance(computers, dict):
            # Single computer
            return computers["computerId"]["$"]

    def runScan(self, computerId, scanType="ScanNow_Full"):
        """
        Run scan on the SEP endpoint.
        SOAP Command
        :param computerId:
        :param scanType: You can use the following type of scans:
            ScanNow_Quick,
            ScanNow_Full,
            ScanNow_Custom
        :return: :string: Command Id
                 :int: Connection Error Code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
				   <soapenv:Header/>
				   <soapenv:Body>
					  <com:runClientCommandScan>
						 <!--Zero or more repetitions:-->
						 <computerGUIDList>{computerId}</computerGUIDList>
						 <!--Optional:-->
						 <scanType>{scanType}</scanType>
					  </com:runClientCommandScan>
				   </soapenv:Body>
				</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(response, "Unable to run scan")
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandScanResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def commandStatusReport(self, commandId):
        """
        The methods provide a status of command.
        SOAP Command
        :param commandId: Unique command Id which you've got from scan/ quarantine jobs
        :return: JSON data
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
				   <soapenv:Header/>
				   <soapenv:Body>
					  <com:getCommandStatusDetails>
						 <!--Optional:-->
						 <commandID>{commandId}</commandID>
					  </com:getCommandStatusDetails>
				   </soapenv:Body>
				</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(response, f"Unable to get command {commandId} status")
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        jsonData = data["Envelope"]["Body"]["getCommandStatusDetailsResponse"][
            "CommandStatusDetailResult"
        ]["cmdStatusDetail"]
        data = dict({(x, y["$"]) for x, y in jsonData.items() if "$" in y})

        return data

    def setQuarantineStateSoap(self, computerId, undo):
        """
        SOAP Command
        :param computerId: The unique Id of computer at SEP Manager
        :param undo: If set true than endpoint will be unquarantine, in other way it will quarantine.
        :return: :string: commandId
                 :string: if operation is successful but it has some errors.
                 :int: if there is an error with server response, than status code.
        """
        if undo:
            action = "Undo"
        else:
            action = "Quarantine"

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandQuarantine>
							 <!--Optional:-->
							 <command>
								<!--Optional:-->
								<commandType>{action}</commandType>
								<!--Zero or more repetitions:-->
								<targetObjectIds>{computerId}</targetObjectIds>
								<!--Optional:-->
								<targetObjectType>COMPUTER</targetObjectType>
							 </command>
						  </com:runClientCommandQuarantine>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to set quarantine state of computer {computerId}"
        )

        # Check that result doesn't have an errors related with not assigned quarantine policies.
        if "No quarantine policy defined for the given computer GUID" in response.text:
            raise SEPManagerException(
                "No quarantine policy defined for the given computer GUID. Quarantine cannot be created."
            )

        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        commandId = data["Envelope"]["Body"]["runClientCommandQuarantineResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]
        return commandId

    def quarantineEndpointsSoap(self, computerId):
        """
        The method is used to define independent call for quarantine of endpoint.
        It uses SOAP call instead and should be used with SEP 14 MP1 and below version.
        :param computerId: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineStateSoap(computerId, undo=False)

    def unQuarantineEndpointsSoap(self, computerId):
        """
        The method is used to define independent call for quarantine of endpoint.
        It uses SOAP call instead and should be used with SEP 14 MP1 and below version.
        :param computerId: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineStateSoap(computerId, undo=True)

    def runClientCommandDisableNTP(self, computerId, timeValue):
        """
        SOAP Command
        The method is used to disable NTP (Network Threat Protection)
        :param computerId: Unique value for client computer at SEP Manager.
        :param timeValue: the parameter specifies the length of time after which Network Threat Protection is automatically
        reset to the state that is specified by the policy that is applied to the client. The minimum timeLimit that
        can be set is one minute, and the maximum is 720 minutes (12 hours).
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandDisableNTP>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
							 <timelimit>{timeValue}</timelimit>
						  </com:runClientCommandDisableNTP>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to disable NTP on computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandDisableNTPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandEnableNTP(self, computerId):
        """
        SOAP Command
        The method is used to enable NTP (Network Threat Protection) on a specified client.
        :param computerID: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandEnableNTP>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
						  </com:runClientCommandEnableNTP>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to enable NTP on computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandEnableNTPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandDisableDownloadInsight(self, computerId, timeValue):
        """
        SOAP Command
        The method is used to disable Download Insight on the specified client.
        :param computerId: Unique value for client computer at SEP Manager.
        :param timeValue: Parameter specifies the length of time after which Download Insight is automatically reset
        to the state that is specified by the policy that is applied to the client. The minimum timeLimit that can be
        set is one minute, and the maximum is 720 minutes (12 hours). If a timeLimit greater than the maximum is
        specified, the maximum timeLimit is used
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandDisableDownloadInsight>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
							 <timeLimit>{timeValue}</timeLimit>
						  </com:runClientCommandDisableDownloadInsight>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to disable download insight for computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"][
            "runClientCommandDisableDownloadInsightResponse"
        ]["CommandClientResult"]["commandId"]["$"]

    def runClientCommandEnableDownloadInsight(self, computerId):
        """
        SOAP Command
        The method is used to enable Download Insight on the specified client.
        :param computerId: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandEnableDownloadInsight>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
						  </com:runClientCommandEnableDownloadInsight>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to enable download insight for computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"][
            "runClientCommandEnableDownloadInsightResponse"
        ]["CommandClientResult"]["commandId"]["$"]

    def runClientCommandEnableAP(self, computerId):
        """
        SOAP Command
        The method is used to enable Auto-Protect on the specified client.
        :param computerId: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandEnableAP>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
						  </com:runClientCommandEnableAP>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to enable AP for computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandEnableAPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandUpdate(self, computerId):
        """
        SOAP Command
        The method is used to run update on the endpoint.
        :param computerId: Unique value of computer at SEP Manager console. It may be received by using getComputerIdbyIpAddress or ComputerName methods.
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandUpdateContent>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
						  </com:runClientCommandUpdateContent>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to run update on computer {computerId}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandUpdateContentResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandUpdateContentAndScan(
        self, computerId, scanType="Update_ScanNow_Full"
    ):
        """
        SOAP Command
        The method is used to run update content and scan commands at the endpoint.
        :param computerId:
        :param scanType: update content and scan type ( one of Update_ScanNow_Quick, Update_ScanNow_Full, Update_ScanNow_Custom )
        :return: :string: Command Id
                 :int: Connection error code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <com:runClientCommandUpdateContentAndScan>
							 <!--Zero or more repetitions:-->
							 <computerGUIDList>{computerId}</computerGUIDList>
							 <!--Optional:-->
							 <scanType>{scanType}</scanType>
						  </com:runClientCommandUpdateContentAndScan>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/CommandService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to run update and scan on computer {computerId}"
        )

        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandUpdateContentAndScanResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def getGroupsByName(self, groupNamePath="*"):
        """
        SOAP Client
        The method is used to return a list of group IDs for Symantec Endpoint Protection Manager groups from the specified group name
        :param groupName: The full path of gorupName or wildcard.
        :return: JSON
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <cli:getGroupsByName>
							 <!--Optional:-->
							 <groupName>{groupNamePath}</groupName>
						  </cli:getGroupsByName>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/ClientService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(
            response, f"Unable to get groups by name {groupNamePath}"
        )
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        print(json.dumps(data, indent=4))
        return data

    def getQuarantinedComputers(self):

        body = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
					   <soapenv:Header/>
					   <soapenv:Body>
						  <cli:getQuarantinedComputers>
						  </cli:getQuarantinedComputers>
					   </soapenv:Body>
					</soapenv:Envelope>"""

        response = self.session.post(
            f"{self.server_address}/ws/v1/ClientService",
            data=body,
            headers=self.soap_headers,
        )

        self.validate_response(response, "Unable to get quarantined computers")
        response = self.clearXmlResponse(response.text)
        data = dict(bf.data(fromstring(response)))
        return data

    def getWsdlAndXsd(self):
        """
        This is a service method and it's used to get WSDL and XSD files to know another SOAP calls.
        :return: :Array: WSDL and XSD files from both SOAP SEP Manager services.
        """

        listUri = [
            "{0}/ws/v1/ClientService?wsdl",
            "{0}/ws/v1/ClientService?xsd=1",
            "{0}/ws/v1/CommandService?wsdl",
            "{0}/ws/v1/CommandService?xsd=1",
        ]

        wsdl = []

        for x in listUri:
            wsdl.append(
                self.session.get(
                    x.format(self.server_address), headers=self.soap_headers
                )
            )
        return wsdl

    def getDomainList(self):
        """
        The method is used to provide list of Symnatec Endpoint Domains.
        :return: JSON / status_code
        """

        response = self.session.get(
            f"{self.server_address}/api/v1/domains", headers=self.json_headers
        )

        self.validate_response(response, "Unable to get wsdl and xsd files")
        return response.json()

    def _blackListBody(self, hashType, hashValue):
        """
        The private method is used to create body for POST request running in setBlackList
        :param hashType: 'MD5' or 'SHA256'. SEP14 doesn't support SHA256 at this time.
        :param hashValue: list of hashes
        :return: BODY
        """

        domainList = self.getDomainList()
        domainId = ""

        if len(domainList) == 1:
            domainId = domainList[0]["id"]
        else:
            for d in domainList:
                if d["name"] == self.domain:
                    domainId = d["id"]

        if not domainId:
            raise ValueError(
                "Symantec Endpoint Protection domain wasn't found. Please check or fill up SEP domain name."
            )

        return {
            "name": f"Siemplify Blacklist {hashType}",
            "domainId": domainId,
            "hashType": hashType,
            "description": "Updated blacklist by the Siemplify solution.",
            "data": hashValue,
        }

    def setBlackList(self, hashType, hashValue):
        """
        The method is used to create/ update fingerprint list at Symantec Endpoint Protection.
        :param hashType: 'MD5' or 'SHA256'. SEP14 doesn't support SHA256 at this time.
        :param hashValue: list of hashes
        :return:
        """

        # if hashType not in ['MD5', 'SHA256']:
        #     raise ValueError("There is a mistake in hash type. There are 'MD5' or 'SHA256' allowed only.")

        if hashType not in ["MD5"]:
            raise ValueError("There is a mistake in hash type. There is 'MD5' only.")

        body = self._blackListBody(hashType, hashValue)

        response = self.session.post(
            f"{self.server_address}/api/v1/policy-objects/fingerprints",
            json=body,
            headers=self.json_headers,
        )

        if response.status_code == 200:
            # Blacklisted successfully
            return response.json()
        elif response.status_code == 400:
            raise ValueError("Invalid MD5 hash values.")
        elif response.status_code == 409 or response.status_code == 404:
            finger_list_id = response.json()["id"]
            response = self.session.post(
                f"{self.server_address}"
                f"/api/v1/policy-objects/fingerprints/{finger_list_id}",
                json=body,
                headers=self.json_headers,
            )
            self.validate_response(response, f"Unable to add {hashValue} to blacklist")
            return 0
        else:
            self.validate_response(response, f"Unable to add {hashValue} to blacklist")

    def getBlackList(self, name):
        """
        The method provides a list of hashes and other addtional info about a fingerprint list.
        :param name: name
        :return: JSON/ status_code
        """

        response = self.session.get(
            f"{self.server_address}/api/v1/policy-objects/fingerprints?name={name}",
            headers=self.json_headers,
        )

        self.validate_response(response, "Unable to get blacklist")
        return response.json()

    def construct_csv(self, results):
        """
        Constructs a csv from resutls
        :param results: SEP results
        :return: {str} csv formatted string
        """
        csv_output = []
        headers = reduce(set.union, list(map(set, list(map(dict.keys, results)))))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            if "domain" in list(result.keys()):
                result["domain"] = result["domain"].get("name")

            if "group" in list(result.keys()):
                result["group"] = result["group"].get("name")

            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in map(str, [result.get(h, None) for h in headers])
                    ]
                )
            )

        return csv_output

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()["errorMessage"]
            except:
                # Not a JSON - return content
                raise SEPManagerException(
                    f"{error_msg}: {error} - {error.response.text}"
                )

            raise SEPManagerException(
                f"{error_msg}: {error} {response.json().get('errorMessage', '')}"
            )
