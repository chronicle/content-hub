# coding=utf-8
from __future__ import annotations
import base64
import datetime
from typing import List, Generator, Type
from urllib.parse import urljoin

import requests

from .IronportConstants import (
    API_TIME_FORMAT,
    API_TIME_HOURS_FORMAT,
    MESSAGES_LIMIT,
    DEVICE_TYPE,
    QUERY_TYPE,
    CA_CERTIFICATE_FILE_PATH,
)
from .IronportDatamodels import Message, DynamicReport
from .IronportEndpoints import IronportEndpoints
from .IronportExceptions import (
    IronportManagerException,
    IronportAsyncOSConnectionException,
    IronportAsyncOSMessagesException,
    IronportAsyncOSReportException,
)
from .IronportParser import IronportParser
from .IronportRequestData import IronportRequestData


class IronportManagerAPI:
    """
    Responsible for all Ironport API operations functionality
    """

    def __init__(
        self,
        server_address: str,
        port: int,
        username: str,
        password: str,
        ca_certificate: str,
        use_ssl: bool = True,
        verify_ssl: bool = False,
    ) -> None or IronportManagerException:
        """
        Setup API
        @param server_address: Ironport server IP
        @param port: Ironport server port
        @param username: Username for Ironport account
        @param password: Password for Ironport account
        @param ca_certificate: CA Certificate File - parsed into Base64 String
        @param use_ssl: Use https if true and http if false
        @param verify_ssl: Verify certificate or not
        """
        self.api_root = urljoin(
            f'{"https" if use_ssl else "http"}://{server_address}:{port}',
            IronportEndpoints.api_host_format,
        )
        self.session = requests.Session()

        self.session.verify = False
        if use_ssl:
            self.session.verify = self.get_verify_value(ca_certificate, verify_ssl)

        self.session.headers = IronportEndpoints.headers
        self.session.headers.update(
            {"jwttoken": self.get_jwt_token(username, password)}
        )

    def get_verify_value(self, ca_certificate, verify_ssl):
        """
        Get value for verify ssl
        :param ca_certificate: {str} CA Certificate File - parsed into Base64 String
        :param verify_ssl: {bool} Verify certificate or not
        :return: Certificate path or bool
        """
        if verify_ssl and ca_certificate:
            file_content = base64.b64decode(ca_certificate)

            with open(CA_CERTIFICATE_FILE_PATH, "w+") as f:
                f.write(file_content.decode("utf-8"))

            verify = CA_CERTIFICATE_FILE_PATH
        elif verify_ssl and not ca_certificate:
            verify = True
        else:
            verify = False

        return verify

    def get_jwt_token(
        self, username: str, password: str
    ) -> str or IronportAsyncOSConnectionException:
        """
        Returns JWT Token to access API with
        @param username: Username for the Ironport ATP
        @param password: Password for the Ironport ATP
        @return: JWT Token
        """
        url = IronportEndpoints.get_login(self.api_root)
        payload, params = IronportRequestData.get_token_request_data(
            # Base64 encode username and password because API requires base64 format for both
            username=base64.b64encode(username.encode("utf-8")).decode("utf-8"),
            password=base64.b64encode(password.encode("utf-8")).decode("utf-8"),
        )

        try:
            response = self.session.post(url, json=payload, params=params)
        except requests.ConnectionError as e:
            raise IronportAsyncOSConnectionException(e)

        self.validate_response(
            response, IronportAsyncOSConnectionException, "Error getting jwt token"
        )

        return response.json().get("data", {}).get("jwtToken")

    def get_recipients(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime = datetime.datetime.utcnow(),
        subjects: List[str] = None,
        senders: List[str] = None,
        limit: int = None,
    ) -> List[str] or IronportAsyncOSMessagesException:
        """
        Get messages recipients from Ironport by AsyncOS REST API
        @param start_date: From which datetime fetch messages
        @param end_date: To which datetime fetch messages
        @param subjects: List of subjects to filter messages by
        @param senders: List of senders to filter messages by
        @param limit: Limit of the recipients
        @return: List of recipients emails
        """
        recipients = set()
        messages_offset = 0
        messages_limit = MESSAGES_LIMIT
        has_data = True

        while has_data:
            if limit and len(recipients) >= limit:
                break

            for has_data, message in self.get_messages(
                start_date=start_date,
                end_date=end_date,
                subjects=subjects,
                senders=senders,
                offset=messages_offset,
                limit=messages_limit,
            ):
                if not message:
                    continue

                recipients.update(message.recipients)

            messages_offset += messages_limit

        return list(recipients)

    def get_messages(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime = datetime.datetime.utcnow(),
        subjects: List[str] = None,
        senders: List[str] = None,
        offset: int = 0,
        limit: int = None,
    ) -> Generator[Message, None, None] or IronportAsyncOSMessagesException:
        """
        Get messages from Ironport by AsyncOS REST API
        @param start_date: From which datetime fetch messages
        @param end_date: To which datetime fetch messages
        @param subjects: List of subjects to filter messages by
        @param senders: List of senders to filter messages by
        @param offset: Offset means how many messages to skip
        @param limit: Limit to fetch
        """
        url = IronportEndpoints.get_messages(self.api_root)
        payload, params = IronportRequestData.get_messages_request_data(
            start_date=start_date.strftime(API_TIME_FORMAT),
            end_date=end_date.strftime(API_TIME_FORMAT),
            offset=offset,
            limit=limit,
        )

        if senders:
            params.update({"envelopeSenderfilterOperator": "contains"})
            params.update({"envelopeSenderfilterValue": senders[0]})

        # Converting params to string to prevent % encoding (API does not accept it) and pass with url directly
        params = "?" + "&".join(
            (f"{param_key}={param_val}" for param_key, param_val in params.items())
        )
        url = urljoin(url, params)

        response = self.session.get(url, json=payload)
        self.validate_response(
            response, IronportAsyncOSMessagesException, "Error getting messages"
        )

        has_data = response.json().get("meta", {}).get("totalCount", 0) > 0
        messages_data = response.json().get("data", [])

        for message_data in messages_data:
            message = IronportParser.build_message(message_data)
            if subjects and not any(subject in message.subject for subject in subjects):
                continue

            if senders and not any(sender in message.sender for sender in senders):
                continue

            yield has_data, message
        else:
            yield has_data, None

    def get_messages_page(
        self,
        start_date: str,
        end_date: str,
        subjects: List[str] = None,
        senders: List[str] = None,
        offset: int = 0,
        limit: int = None,
    ) -> Generator[Message, None, None] or IronportAsyncOSMessagesException:
        """
        Get messages from Ironport by AsyncOS REST API
        @param start_date: {str} Start date formatted datetime as string from which to fetch messages
        @param end_date: {str} End date to which datetime fetch messages
        @param subjects: List of subjects to filter messages by
        @param senders: List of senders to filter messages by
        @param offset: Offset means how many messages to skip
        @param limit: Limit to fetch
        """
        url = IronportEndpoints.get_messages(self.api_root)
        payload, params = IronportRequestData.get_messages_request_data(
            start_date=start_date, end_date=end_date, offset=offset, limit=limit
        )

        if senders:
            params.update({"envelopeSenderfilterOperator": "contains"})
            params.update({"envelopeSenderfilterValue": senders[0]})

        # Converting params to string to prevent % encoding (API does not accept it) and pass with url directly
        params = "?" + "&".join(
            (f"{param_key}={param_val}" for param_key, param_val in params.items())
        )
        url = urljoin(url, params)

        response = self.session.get(url, json=payload)
        self.validate_response(
            response, IronportAsyncOSMessagesException, "Error getting messages"
        )

        has_data = response.json().get("meta", {}).get("totalCount", 0) > 0
        messages_data = response.json().get("data", [])

        results = []
        for message_data in messages_data:
            message = IronportParser.build_message(message_data)
            if subjects and not any(subject in message.subject for subject in subjects):
                continue

            if senders and not any(sender in message.sender for sender in senders):
                continue

            results.append(message)

        return has_data, results

    def get_reports(
        self,
        report_type: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime = datetime.datetime.utcnow(),
        device_type: str = DEVICE_TYPE,
        query_type: str = QUERY_TYPE,
        limit: int = None,
    ) -> List[DynamicReport]:
        """

        @param report_type: Report type to request
        @param start_date: From which datetime fetch reports
        @param end_date: To which datetime fetch reports
        @param device_type: Device type esa
        @param query_type: Query type could be empty or export
        @param limit: Limit to fetch
        @return: List of reports
        """
        url = IronportEndpoints.get_reports(self.api_root, report_type)
        payload, params = IronportRequestData.get_reports_request_data(
            start_date=start_date.strftime(API_TIME_HOURS_FORMAT),
            end_date=end_date.strftime(API_TIME_HOURS_FORMAT),
            device_type=device_type,
            query_type=query_type,
        )

        # Converting params to string to prevent % encoding (API does not accept it) and pass with url directly
        params = "?" + "&".join(
            (f"{param_key}={param_val}" for param_key, param_val in params.items())
        )
        url = urljoin(url, params)

        response = self.session.get(url, json=payload)
        self.validate_response(
            response, IronportAsyncOSReportException, "Error getting reports"
        )

        response_data = response.json().get("data", {})
        result_set = response_data.get("resultSet", {})
        reports_data = result_set.get("time_intervals", [])
        counter_names = result_set.get("counter_names", [])
        report_type = response_data.get("type")

        # Make list reversed because it's sorted by time ASC and we need to get find first appeared user/ip/hostname
        reports = list(
            reversed(
                [
                    dynamic_report
                    for report_data in reports_data
                    for dynamic_report in IronportParser.build_dynamic_report(
                        report_data, counter_names, report_type
                    )
                ]
            )
        )

        if limit:
            reports = reports[:limit]

        return reports

    @staticmethod
    def validate_response(
        response: requests.Response,
        custom_exception: Type[IronportManagerException] = IronportManagerException,
        error_msg: str = "An error occurred",
    ) -> None or IronportManagerException:
        """
        Validate function for response
        @param response: Response object
        @param custom_exception: Custom exception to raise
        @param error_msg: Message to raise with
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise custom_exception(
                f"{error_msg}: {error} {error.response.content}"
            ) from error
