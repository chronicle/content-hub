from __future__ import annotations
import requests
from defusedxml.ElementTree import fromstring
from xmljson import badgerfish as bf

# Consts
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


class SEPManagerException(Exception):
    pass


class SymantecEp12:

    def __init__(self, url, clientId, clientSecret, refreshToken, verify_ssl=False):
        """
        The method is used to init an object of SymantecEp class which provides the methods to make SOAP calls to
        SEP Manager.
        :param url: SEP Manager hostname/ ip address of server with its port (Example: 10.10.10.10:8446)
        :param clientId: You should receive this value at hostname:8446/sepm site
        :param clientSecret: You should receive this value at hostname:8446/sepm site
        :param refreshToken: It's required to update token. it has limit life time too, but it's very huge.
        :param verify_ssl: Whether to verify ssl or not
        """

        self.url = url
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.refreshToken = refreshToken
        self.verify_ssl = verify_ssl
        # Obtain Tokens
        self.refreshAccessToken()
        self.session = requests.session()
        self.session.verify = self.verify_ssl
        self.session.headers = self.get_soap_header()

    def getAuthorizeCode(self):
        """
        The method is used to provide a link to the end user who is going to set up an integration.
        It provides a link that user should visit to receive one time code. It's required to use it only once,
        after you've got a refresh token use "refreshAccesstoken" method.
        :return: :string: URL
        """

        codeString = f"https://{self.url}/sepm/oauth/authorize?response_type=code&client_id={self.clientId}&redirect_uri={self.redirectUrl}"
        return codeString

    def getAccessToken(self, code):
        """
        The method is used to get access
        :param code: One time code which user has got from "getAuthorizeCode" method
        :return: :tuple: token and refresh token values
                 :int: connection error code
        """
        headers = {"Content-Type": "application/json"}

        connectionString = (
            "https://{0}/sepm/oauth/token?grant_type=authorization_code&client_id={1}"
            "&client_secret={2}&redirect_uri={3}&code={4}".format(
                self.url, self.clientId, self.clientSecret, self.redirectUrl, code
            )
        )

        response = requests.get(
            connectionString, headers=headers, verify=self.verify_ssl
        )
        self.validate_response(response, "Unable to get access token")

        self.token = response.json()["value"]
        self.tokenExpiresIn = response.json()["expiresIn"]
        self.refreshToken = response.json()["refreshToken"]["value"]
        self.refreshTokenExpirationTime = response.json()["refreshToken"]["expiration"]

        return self.token, self.refreshToken

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate an http response
        :param response: {requests.Response} The response
        :param error_msg: {str} Error message to display on failure
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise SEPManagerException(
                f"{error_msg}: {error} - {error.response.content}"
            )

    def refreshAccessToken(self):
        """
        The method is used to update an access token if it is expired.
        It recommend use it every time if you already have refresh token because it's not required to user interact actions.
        :return: :string: token
                 :int: connection error code
        """

        headers = {"Content-Type": "application/json"}

        connectionString = (
            "https://{0}/sepm/oauth/token?grant_type=refresh_token&client_id={1}&client_secret={2}"
            "&refresh_token={3}".format(
                self.url, self.clientId, self.clientSecret, self.refreshToken
            )
        )

        response = requests.get(
            connectionString, headers=headers, verify=self.verify_ssl
        )

        self.validate_response(response, "Unable to refresh token")

        self.token = (
            response.json()["access_token"]
            if response.json().get("access_token")
            else response.json().get("value")
        )
        self.tokenExpiresIn = (
            response.json()["expires_in"]
            if response.json().get("expires_in")
            else response.json().get("expiresIn")
        )

        return self.token

    def get_soap_header(self):
        """
        The methods is used to provide a SOAP header for Client and Command SOAP calls.
        :return: :json: Header
        """
        headers = {"Authorization": "Bearer " + self.token, "Content-Type": "text/xml"}
        return headers

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

    def getComputerIdByIP(self, ip_address="*"):
        """
        SOAP Client
        The method is used to provide a computer Id in the SEPM Manager based on IP Address.
        :param ip_address: the SEP endpoint's IP Address
        :return: :string: Computer Id
                 :int: Connection Error Code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <cli:getComputersByIP>
                             <!--Zero or more repetitions:-->
                             <ipAddresses>{ip_address}</ipAddresses>
                          </cli:getComputersByIP>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/ClientService", data=body
        )

        self.validate_response(response, f"Unable to get computer id for {ip_address}")
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))

        computers = data["Envelope"]["Body"]["getComputersByIPResponse"][
            "ComputerResult"
        ].get("computers", [])

        if isinstance(computers, list) and computers:
            # Multiple computers - get the first
            return computers[0]["computerId"]["$"]

        elif isinstance(computers, dict):
            # Single computer
            return computers["computerId"]["$"]

    def getComputerIdByComputerName(self, computer_name="*"):
        """
        SOAP Client
        The method is used to provide computerId using computer name.
        :param computer_name: {str} The name of the computer to get
        :return: :string: Computer Id
                 :int: Connection Error Code
        """

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <cli:getComputersByHostName>
                             <!--Zero or more repetitions:-->
                             <computerHostNames>{computer_name}</computerHostNames>
                          </cli:getComputersByHostName>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/ClientService", data=body
        )
        self.validate_response(
            response, f"Unable to get computer id for {computer_name}"
        )

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))

        computers = data["Envelope"]["Body"]["getComputersByHostNameResponse"][
            "ComputerResult"
        ].get("computers", [])

        if isinstance(computers, list) and computers:
            # Multiple computers - get the first
            return computers[0]["computerId"]["$"]

        elif isinstance(computers, dict):
            # Single computer
            return computers["computerId"]["$"]

    def runScan(self, computer_id, scan_type="ScanNow_Full"):
        """
        Run scan on the SEP endpoint.
        SOAP Command
        :param computer_id:
        :param scan_type: You can use the following type of scans: ScanNow_Quick, ScanNow_Full, ScanNow_Custom
        :return: :string: Command Id
                 :int: Connection Error Code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <com:runClientCommandScan>
                         <!--Zero or more repetitions:-->
                         <computerGUIDList>{computer_id}</computerGUIDList>
                         <!--Optional:-->
                         <scanType>{scan_type}</scanType>
                      </com:runClientCommandScan>
                   </soapenv:Body>
                </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to run scan on computer {computer_id}"
        )

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandScanResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def commandStatusReport(self, command_id):
        """
        The methods provide a status of command.
        SOAP Command
        :param command_id: Unique command Id which you've got from scan/ quarantine jobs
        :return: JSON data
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <com:getCommandStatusDetails>
                         <!--Optional:-->
                         <commandID>{command_id}</commandID>
                      </com:getCommandStatusDetails>
                   </soapenv:Body>
                </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )
        self.validate_response(
            response, f"unable to get command status of {command_id}"
        )

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        jsonData = data["Envelope"]["Body"]["getCommandStatusDetailsResponse"][
            "CommandStatusDetailResult"
        ]["cmdStatusDetail"]
        data = dict({(x, y["$"]) for x, y in jsonData.items() if "$" in y})

        return data

    def setQuarantineStateSoap(self, computer_id, undo):
        """
        SOAP Command
        :param computer_id: The unique Id of computer at SEP Manager
        :param undo: If set true than endpoint will be unquarantine, in other way it will quarantine.
        :return: :string: commandId
                 :string: if operation is successful but it has some errors.
                 :int: if there is an error with server response, than status code.
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandQuarantine>
                             <!--Optional:-->
                             <command>
                                <!--Optional:-->
                                <commandType>{undo}</commandType>
                                <!--Zero or more repetitions:-->
                                <targetObjectIds>{computer_id}</targetObjectIds>
                                <!--Optional:-->
                                <targetObjectType>COMPUTER</targetObjectType>
                             </command>
                          </com:runClientCommandQuarantine>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to set quarantine state for computer {computer_id}"
        )

        # Check that result doesn't have an errors related with not assigned quarantine policies.
        if response.content.__contains__(
            "No quarantine policy defined for the given computer GUID"
        ):
            return "No quarantine policy defined for the given computer GUID. Quarantine cannot be created."

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        commandId = data["Envelope"]["Body"]["runClientCommandQuarantineResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

        return commandId

    def quarantineEndpointsSoap(self, computer_id):
        """
        The method is used to define independent call for quarantine of endpoint.
        It uses SOAP call instead and should be used with SEP 14 MP1 and below version.
        :param computer_id: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineStateSoap(computer_id, undo="Quarantine")

    def unQuarantineEndpointsSoap(self, computer_id):
        """
        The method is used to define independent call for quarantine of endpoint.
        It uses SOAP call instead and should be used with SEP 14 MP1 and below version.
        :param computer_id: The unique Id of computer at SEP Manager.
        :return: JSON data which contains GroupId and ComputerId
        """
        return self.setQuarantineStateSoap(computer_id, undo="Undo")

    def runClientCommandDisableNTP(self, computer_id, time_value):
        """SOAP Command
        The method is used to disable NTP (Network Threat Protection)
        :param computer_id: Unique value for client computer at SEP Manager.
        :param time_value: the parameter specifies the length of time after which Network Threat Protection is automatically
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
                             <computerGUIDList>{computer_id}</computerGUIDList>
                             <timelimit>{time_value}</timelimit>
                          </com:runClientCommandDisableNTP>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to disable NTP for computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandDisableNTPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandEnableNTP(self, computer_id):
        """
        SOAP Command
        The method is used to enable NTP (Network Threat Protection) on a specified client.
        :param computer_id: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandEnableNTP>
                             <!--Zero or more repetitions:-->
                             <computerGUIDList>{computer_id}</computerGUIDList>
                          </com:runClientCommandEnableNTP>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to enable NTP for computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandEnableNTPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandDisableDownloadInsight(self, computer_id, time_value):
        """
        SOAP Command
        The method is used to disable Download Insight on the specified client.
        :param computer_id: Unique value for client computer at SEP Manager.
        :param time_value: Parameter specifies the length of time after which Download Insight is automatically reset
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
                             <computerGUIDList>{computer_id}</computerGUIDList>
                             <timeLimit>{time_value}</timeLimit>
                          </com:runClientCommandDisableDownloadInsight>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )
        self.validate_response(
            response, f"Unable to disable Download Insight for computer {computer_id}"
        )

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"][
            "runClientCommandDisableDownloadInsightResponse"
        ]["CommandClientResult"]["commandId"]["$"]

    def runClientCommandEnableDownloadInsight(self, computer_id):
        """
        SOAP Command
        The method is used to enable Download Insight on the specified client.
        :param computer_id: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandEnableDownloadInsight>
                             <!--Zero or more repetitions:-->
                             <computerGUIDList>{computer_id}</computerGUIDList>
                          </com:runClientCommandEnableDownloadInsight>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to enable Download Insight for computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"][
            "runClientCommandEnableDownloadInsightResponse"
        ]["CommandClientResult"]["commandId"]["$"]

    def runClientCommandEnableAP(self, computer_id):
        """
        SOAP Command
        The method is used to enable Auto-Protect on the specified client.
        :param computer_id: Unique value for client computer at SEP Manager.
        :return: :string: Command Id
                 :int: Connection error code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandEnableAP>
                             <!--Zero or more repetitions:-->
                             <computerGUIDList>{computer_id}</computerGUIDList>
                          </com:runClientCommandEnableAP>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to enable AP for computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandEnableAPResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandUpdate(self, computer_id):
        """
        SOAP Command
        The method is used to run update on the endpoint.
        :param computer_id: Unique value of computer at SEP Manager console. It may be received by using getComputerIdbyIpAddress or ComputerName methods.
        :return: :string: Command Id
                 :int: Connection error code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandUpdateContent>
                             <!--Zero or more repetitions:-->
                             <computerGUIDList>{computer_id}</computerGUIDList>
                          </com:runClientCommandUpdateContent>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to run update on computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandUpdateContentResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def runClientCommandUpdateContentAndScan(
        self, computer_id, scan_type="Update_ScanNow_Full"
    ):
        """
        SOAP Command
        The method is used to run update content and scan commands at the endpoint.
        :param computer_id:
        :param scan_type: update content and scan type ( one of Update_ScanNow_Quick, Update_ScanNow_Full, Update_ScanNow_Custom )
        :return: :string: Command Id
                 :int: Connection error code
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:com="http://command.client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <com:runClientCommandUpdateContentAndScan>
                             <!--Zero or more repetitions:-->
                             <computerGUIDList>{computer_id}</computerGUIDList>
                             <!--Optional:-->
                             <scanType>{scan_type}</scanType>
                          </com:runClientCommandUpdateContentAndScan>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/CommandService", data=body
        )

        self.validate_response(
            response, f"Unable to update and scan computer {computer_id}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data["Envelope"]["Body"]["runClientCommandUpdateContentAndScanResponse"][
            "CommandClientResult"
        ]["commandId"]["$"]

    def getGroupsByName(self, group_name_path="*"):
        """
        SOAP Client
        The method is used to return a list of group IDs for Symantec Endpoint Protection Manager groups from the specified group name
        :param groupName:
        :return:
        """
        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cli="http://client.webservice.sepm.symantec.com/">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <cli:getGroupsByName>
                             <!--Optional:-->
                             <groupName>{group_name_path}</groupName>
                          </cli:getGroupsByName>
                       </soapenv:Body>
                    </soapenv:Envelope>"""

        response = self.session.post(
            f"https://{self.url}/sepm/ws/v1/ClientService", data=body
        )

        self.validate_response(
            response, f"Unable to get groups by name {group_name_path}"
        )
        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
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
            f"https://{self.url}/sepm/ws/v1/ClientService", data=body
        )
        self.validate_response(response, "Unable to get quarantined computers")

        response = self.clearXmlResponse(response.content)
        data = dict(bf.data(fromstring(response)))
        return data

    def getWsdlAndXsd(self):
        """
        This is a service method and it's used to get WSDL and XSD files to know another SOAP calls.
        :return: :Array: WSDL and XSD files from both SOAP SEP Manager services.
        """

        listUri = [
            "https://{0}/sepm/ws/v1/ClientService?wsdl",
            "https://{0}/sepm/ws/v1/ClientService?xsd=1",
            "https://{0}/sepm/ws/v1/CommandService?wsdl",
            "https://{0}/sepm/ws/v1/CommandService?xsd=1",
        ]

        wsdl = []

        for x in listUri:
            wsdl.append(self.session.get(x.format(self.url)))
        return wsdl
