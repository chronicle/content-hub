# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import dataclasses
from urllib.parse import urljoin
import requests
import base64
import hashlib
import hmac
import uuid
import datetime

from TIPCommon.filters import filter_old_alerts

from mimecast.core.constants import *
from mimecast.core.datamodels import (
    Attachment,
    BlockSenderPolicy,
    BlockSenderPolicyActionParams,
    HoldMessage,
    Message,
    MessageDetails,
)
from mimecast.core.MimecastExceptions import MimecastException
from mimecast.core.MimecastParser import MimecastParser
from mimecast.core.UtilsManager import validate_response, lazy_chunk_iterable, filter_message


@dataclasses.dataclass
class EmailSearchCriteria:
    start_timestamp: datetime.datetime
    domains: list[str]
    statuses: list[str]
    routes: list[str]
    queue_reason_filter: list[str]


class MimecastManager:
    def __init__(
        self,
        api_root,
        app_id,
        app_key,
        access_key,
        secret_key,
        client_id,
        client_secret,
        verify_ssl=False,
        siemplify=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Mimecast instance.
        :param app_id: {str} Application ID of the Mimecast instance.
        :param app_key: {str} Application Key of the Mimecast instance.
        :param access_key: {str} Access Key of the Mimecast instance.
        :param secret_key: {str} Secret Key of the Mimecast instance.
        :param client_id: {str} Client ID of the Mimecast instance.
        :param client_secret: {str} Client Secret of the Mimecast instance.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the server is valid.
        :param siemplify: Siemplify Connector Executor
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.app_id = app_id
        self.app_key = app_key
        self.access_key = access_key
        self.secret_key = secret_key
        self.client_id = client_id
        self.client_secret = client_secret
        self.siemplify = siemplify
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = MimecastParser()
        self.is_old_auth = None

        self.validate_auth()

    def validate_auth(self):
        """
        Validates authentication parameters and sets the authentication type.

        - If any old-type auth parameters (app_id, app_key, access_key, secret_key)
          are provided but not all, raises an error. Otherwise,
          sets 'self.is_old_auth' to True.
        - If old-type auth is not used and any new-type auth parameters
          (client_id, client_secret) are provided but not all, raises an error.
          Otherwise, sets 'self.is_old_auth' to False.
        - If no authentication parameters are provided, raises an error.

        Raises:
            ValueError: If required parameters are missing or none are provided.
        """
        old_auth_params = {
            "Application ID": self.app_id,
            "Application Key": self.app_key,
            "Access Key": self.access_key,
            "Secret Key": self.secret_key,
        }
        new_auth_params = {
            "Client ID": self.client_id,
            "Client Secret": self.client_secret,
        }

        # Check old authentication (priority)
        if any(old_auth_params.values()):
            missing = [k for k, v in old_auth_params.items() if not v]
            if missing:
                raise ValueError(
                    f'You need to provide {", ".join(missing)}.'
                )
            self.session.headers = HEADERS
            self.is_old_auth = True
            return

        # Check new authentication if old is not used
        if any(new_auth_params.values()):
            missing = [k for k, v in new_auth_params.items() if not v]
            if missing:
                raise ValueError(
                    f'You need to provide {", ".join(missing)}.'
                )
            token = self.get_oauth_token(self.client_id, self.client_secret)
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.is_old_auth = False
            return

        # If no authentication parameters were provided at all
        raise ValueError(
            "No authentication parameters provided."
        )

    def get_oauth_token(self, client_id, client_secret):
        """
        Request access token.

        Args:
            client_id (str): Client ID of the Mimecast instance.
            client_secret (str): Client Secret of the Mimecast instance.

        Returns:
            str: bearer token
        """
        request_url = self._get_full_url("get_token")
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }

        response = self.session.post(request_url, data=payload)
        validate_response(response)
        return response.json().get("access_token")

    def _generate_request_headers(self, uri):
        """
        Request access token
        :param uri: {str} Request endpoint.
        :return: {dict} Request headers
        """
        # Generate request header values
        request_id = str(uuid.uuid4())
        hdr_date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") + " UTC"

        # DataToSign is used in hmac_sha1
        data_to_sign = ":".join([hdr_date, request_id, uri, self.app_key])

        # Create the HMAC SHA1 of the Base64 decoded secret key for the Authorization header
        hmac_sha1 = hmac.new(
            base64.b64decode(self.secret_key),
            data_to_sign.encode(),
            digestmod=hashlib.sha1,
        ).digest()

        # Use the HMAC SHA1 value to sign the hdrDate + ":" requestId + ":" + URI + ":" + appkey
        sig = base64.b64encode(hmac_sha1).rstrip()

        # Create request headers
        headers = {
            "Authorization": "MC " + self.access_key + ":" + sig.decode(),
            "x-mc-app-id": self.app_id,
            "x-mc-date": hdr_date,
            "x-mc-req-id": request_id,
            "Content-Type": "application/json",
        }

        return headers

    def _update_headers(self, uri: str) -> None:
        """Helper method to update headers for old authentication."""
        if self.is_old_auth:
            self.session.headers.update(self._generate_request_headers(uri=uri))

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["ping"])
            )
        response = self.session.post(request_url)
        validate_response(response)

    def create_block_sender_policy(
        self,
        action_params: BlockSenderPolicyActionParams,
    ) -> BlockSenderPolicy:
        """
        Create a Block Sender policy in Mimecast.

        Args:
            action_params (BlockSenderPolicyActionParams): Parameters for creating
                the policy.
        """
        request_url = self._get_full_url("create_block_sender_policy")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(
                    uri=ENDPOINTS["create_block_sender_policy"]
                )
            )

        payload = action_params.create_block_sender_policy_payload()

        result = self.session.post(request_url, json=payload)
        validate_response(result)
        return self.parser.build_block_sender_policy(result.json().get("data")[0])

    def search_emails(
        self,
        criteria: EmailSearchCriteria,
        existing_ids: list[str],
        limit: int
    ) -> list[Message]:
        """Search for emails matching specified criteria, then filter and return the
        results.

        Args:
            criteria (EmailSearchCriteria): Encapsulates all filtering options
            existing_ids (list[str]): Message IDs that should be excluded
            limit (int): Maximum number of results to return

        Returns:
            list[Message]: Filtered and limited list of email message.
        """
        messages: list[Message] = self._search_raw_emails(criteria)

        sorted_emails = sorted(messages, key=lambda m: m.received)

        filtered_emails = self._filter_emails(
            emails=sorted_emails,
            limit=limit,
            existing_ids=existing_ids,
            queue_reason_filter=criteria.queue_reason_filter,
        )

        return filtered_emails[:limit]

    def _search_raw_emails(self, criteria: EmailSearchCriteria) -> list[Message]:
        """Searches for emails in Mimecast based on the provided criteria.

        This method constructs and sends requests to the Mimecast API to search for
        emails that match the specified criteria. It iterates through each domain and
        field combination, sending a separate request for each. The responses are then
        parsed to extract the email messages.

        Args:
            criteria (EmailSearchCriteria): An object containing the search criteria,
                including the start timestamp, domains, statuses, routes, and
                queue reason filter.

        Returns:
            list[Message]: A list of Message objects representing the emails found
                that match the search criteria.
        """
        messages = []
        url = self._get_full_url("email_search")
        payload = {
            "data": [{
                "start": criteria.start_timestamp.strftime(FILTER_TIME_FORMAT),
                "status": criteria.statuses,
                "route": criteria.routes,
                "advancedTrackAndTraceOptions": {}
            }]
        }

        for domain in criteria.domains:
            for field in ADVANCE_TRACKING_FIELDS:
                payload["data"][0]["advancedTrackAndTraceOptions"] = {field: domain}
                self._update_headers(uri=ENDPOINTS["email_search"])
                response = self.session.post(url, json=payload)
                validate_response(response)
                messages.extend(self.parser.build_messages_list(response.json()))

        return messages

    def _filter_emails(
        self,
        emails: list[Message],
        limit: int,
        existing_ids: list[str],
        queue_reason_filter: list[str],
    ) -> list[Message]:
        """Filters a list of emails based on various criteria.

        This method filters a list of emails, applying a queue reason filter,
        checking for existing IDs, and enforcing a limit on the number of
        emails returned. It uses lazy chunking to process the emails in
        smaller batches.

        Args:
            emails (list[Message]): The list of emails to filter.
            limit (int): The maximum number of emails to return.
            existing_ids (list[str]): A list of IDs to exclude from the results.
            queue_reason_filter (list[str]): A list of queue reasons to filter by.

        Returns:
            list[Message]: A filtered list of emails.
        """
        filtered_emails = []

        for chunk in lazy_chunk_iterable(emails, limit):
            enriched = self._filter_by_queue_reason(chunk, queue_reason_filter)

            if enriched:
                new_alerts = filter_old_alerts(
                    siemplify=self.siemplify,
                    alerts=enriched,
                    existing_ids=existing_ids,
                    id_key=ALERT_ID_KEY,
                )
                if new_alerts:
                    filtered_emails.extend(new_alerts)

            if len(filtered_emails) >= limit:
                break

        return filtered_emails

    def _filter_by_queue_reason(
        self,
        chunk: list[Message],
        queue_reason_filter: list[str]
    ) -> list[Message]:
        """Filters a chunk of emails based on their queue reason.

        This method iterates through a chunk of emails, retrieves the message
        details for each email, and then filters the emails based on whether
        their queue reason (if present) matches any of the reasons in the
        queue_reason_filter.

        Args:
            chunk (list[Message]): A list of Message objects representing a
                chunk of emails to filter.
            queue_reason_filter (list[str]): A list of queue reasons to filter by.
                If this list is empty, no filtering by queue reason is performed.

        Returns:
            list[Message]: A list of Message objects that have been filtered
                based on their queue reason.
        """
        filtered = []
        for email in chunk:
            email.message_details = self.get_message_details(email.tracking_id)
            if queue_reason_filter:
                reason = email.message_details.reason
                if not isinstance(reason, str):
                    self.siemplify.LOGGER.warning(
                        f"Unexpected reason type: {type(reason)} "
                        f"for message {email.tracking_id}"
                    )
                    continue
                if reason.lower() in queue_reason_filter:
                    filtered.append(email)
            else:
                filtered.append(email)

        return filtered

    def get_message_details(self, message_id: str) -> MessageDetails:
        """Retrieves detailed information about a specific message from Mimecast.

        Makes a POST request to Mimecast's API to fetch complete message details
        including content and metadata for a given message ID.

        Args:
            message_id (str): Unique identifier of the message to retrieve details for

        Returns:
            MessageDetails: Object containing complete message information.

        Raises:
            MimecastException: If the API request fails or returns an error
            ValueError: If message_id is empty or invalid
        """
        url = self._get_full_url("get_email_details")
        payload = {
            "data": [
                {
                    "id": message_id,
                    "loadContent": "true"
                }
            ]
        }
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["get_email_details"])
            )
        response = self.session.post(url, json=payload)
        validate_response(response)

        return self.parser.build_message_details_object(response.json())

    def manage_sender(self, sender, recipient, action):
        """
        Function that manages senders, either block them or permits them
        :param sender: Sender who should be either permitted or blocked
        :param recipient: Recipient who should be either permitted or blocked
        :param action: Action - Permit/Block
        """

        request_url = self._get_full_url("manage_sender")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["manage_sender"])
            )
        payload = {"data": [{"action": action, "to": recipient, "sender": sender}]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)

    def reject_message(self, message_id, note, reason, notify_sender):
        """
        Function that rejects the message in Mimecast
        :param message_id: Message ID
        :param note: Rejection Note
        :param reason: Reason for rejection
        :param notify_sender: Value that indicates if the sender should be notified
        """

        if self.is_old_auth:
            request_url = self._get_full_url("reject_message")
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["reject_message"])
            )
            data_payload = {"id": message_id, "notify": notify_sender}
        else:
            request_url = self._get_full_url("hold_reject")
            data_payload = {"ids": [message_id], "notify": notify_sender}

        reason = REJECTION_REASONS.get(reason)

        if note is not None:
            data_payload["notes"] = note

        if reason != SELECT_ONE_REASON:
            data_payload["reason"] = reason

        payload = {"data": [data_payload]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)
        if not self.is_old_auth:
            if not result.json().get("data", [{}])[0].get("reject"):
                raise MimecastException("Failed to reject held email.")

    def report_message(self, message_id, comment, report_as):
        """
        Function that reports the message in Mimecast
        :param message_id: Message ID
        :param comment: Comment to add to the report
        :param report_as: Type of the report Spam/Malware/Phising
        """
        request_url = self._get_full_url("report_message")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["report_message"])
            )
        report_type = REPORT_TYPES.get(report_as)

        data_payload = {"id": message_id, "type": report_type}

        if comment is not None:
            data_payload["comment"] = comment

        payload = {"data": [data_payload]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)

    def release_message(self, message_id):
        """
        Function that releases the message in Mimecast
        :param message_id: Message ID
        """

        if self.is_old_auth:
            request_url = self._get_full_url("release_message")
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["release_message"])
            )
        else:
            request_url = self._get_full_url("hold_release")

        payload = {"data": [{"id": message_id}]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)
        if not self.is_old_auth:
            if not result.json().get("data", [{}])[0].get("release"):
                raise MimecastException("Failed to release held email.")

    def release_message_to_sandbox(self, message_id):
        """
        Function that releases the message to Sandbox in Mimecast
        :param message_id: Message ID
        """
        if self.is_old_auth:
            request_url = self._get_full_url("release_message_sandbox")
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["release_message_sandbox"])
            )
        else:
            request_url = self._get_full_url("hold_release")

        payload = {"data": [{"id": message_id}]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)
        if not self.is_old_auth:
            if not result.json().get("data", [{}])[0].get("release"):
                raise MimecastException("Failed to release held email.")

    def execute_query(self, xml_query):
        """
        Function that exexutes the query in XML in Mimecast
        :param xml_query: XML Query
        :return: {BaseModel} Base Model object containing query results
        """
        request_url = self._get_full_url("execute_query")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["execute_query"])
            )

        payload = {"meta": {}, "data": [{"admin": True, "query": xml_query}]}

        result = self.session.post(request_url, json=payload)
        validate_response(result)
        return self.parser.build_base_model(result.json())

    def execute_query_with_pagination(self, xml_query, limit):
        """
        Archive search with pagination
        :param xml_query: {str} Search query
        :param limit: {int} Number of emails to return
        :return: {BaseModel} Base Model object containing query results
        """
        request_url = self._get_full_url("execute_query")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["execute_query"])
            )

        payload = {"meta": {}, "data": [{"admin": True, "query": xml_query}]}

        search_results = self.parser.build_list_of_base_objects(
            self._paginate_results(method="POST", url=request_url, body=payload)
        )
        return search_results[:limit]

    def _paginate_results(
        self, method, url, params=None, body=None, err_msg="Unable to get results"
    ):
        """
        Paginate the results of a request
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if params is None:
            params = {}

        if body is None:
            body = {}

        response = self.session.request(method, url, params=params, json=body)

        validate_response(response, err_msg)
        data = response.json().get("data")
        results = data[0].get("items", []) if data else []
        next_page_token = (
            response.json().get("meta", {}).get("pagination", {}).get("next")
        )

        while next_page_token:
            body.update({"meta": {"pagination": {"pageToken": next_page_token}}})

            response = self.session.request(method, url, params=params, json=body)
            validate_response(response, err_msg)
            data = response.json().get("data")
            next_page_token = (
                response.json().get("meta", {}).get("pagination", {}).get("next")
            )
            results.extend(data[0].get("items", []) if data else [])

        return results

    def build_query(
        self,
        fields,
        mailboxes,
        from_addresses,
        to_addresses,
        subject,
        start_time,
        end_time,
    ):
        """
        Prepare the search query
        :param fields: {list} List of fields to return
        :param mailboxes: {list} List of mailboxes
        :param from_addresses: {list} List of email addresses from which the emails were sent
        :param to_addresses: {list} List of email addresses to which the emails were sent
        :param subject: {str} Subject that needs to be searched
        :param start_time: {str} Start time for search
        :param end_time: {str} End time for search
        """

        query = (
            '<?xml version="1.0"?><xmlquery trace="iql,muse"><metadata query-type="emailarchive" '
            'archive="true" active="false" page-size="100" startrow="0">'
        )
        if mailboxes:
            query += "<mailboxes>"
            query += f" ".join(
                [
                    f"<mailbox include-aliases='true'>{mailbox}</mailbox>"
                    for mailbox in mailboxes
                ]
            )
            query += "</mailboxes>"

        query += f"<smartfolders/><return-fields>"
        query += f" ".join(
            [f"<return-field>{field}</return-field>" for field in fields]
        )
        query += f"</return-fields></metadata><muse>"

        if from_addresses:
            query += "<text>"
            query += f" or ".join([f"from:{address}" for address in from_addresses])
            query += "</text>"

        if to_addresses:
            query += "<text>"
            query += f" or ".join([f"to:{address}" for address in to_addresses])
            query += "</text>"

        if subject:
            query += f"<text>subject:{subject}</text>"

        query += f'<date select="between" from="{start_time}" to="{end_time}"/>'
        query += '<docs select="optional"></docs><route/></muse></xmlquery>'

        return query

    def _get_hold_messages_raw(
        self,
        recipient: str,
        start_time: str,
        end_time: str,
    ) -> list[HoldMessage]:
        """Retrieves a raw list of hold messages from Mimecast.

        Args:
            recipient: Recipient email address.
            start_time: Start of the time range.
            end_time: End of the time range.

        Returns:
            list[HoldMessage]: List of HoldMessage objects.
        """
        self._update_headers(uri=ENDPOINTS["hold_message_list"])
        dt = datetime.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S%z")
        dt += datetime.timedelta(seconds=2)
        end_time = dt.strftime("%Y-%m-%dT%H:%M:%S%z")

        payload = {
            "data": [
                {
                    "admin": True,
                    "end": end_time,
                    "searchBy": {"fieldName": "recipient", "value": recipient},
                    "start": start_time,
                }
            ]
        }
        request_url = self._get_full_url("hold_message_list")
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_list_of_hold_messages(response.json())

    def _get_attachment_download_url(self, attachment: Attachment) -> str:
        return self.get_download_url_for_attachment(attachment.attachment_id)

    def _download_attachment_content(self, attachment: Attachment) -> None:
        download_url = self._get_attachment_download_url(attachment)
        file_content = self.download_attachment(download_url)
        attachment.file_content = file_content

    def _enrich_hold_message_with_attachments(self, message: HoldMessage) -> None:
        """Enriches a HoldMessage object with its attachments.

        Args:
            message (HoldMessage): The HoldMessage object to enrich.
        """
        attachments = self.get_message_attachments(message.message_id)
        if attachments:
            for attachment in attachments:
                self._download_attachment_content(attachment)
                message.attachments.append(attachment)

    def get_hold_message_details(
        self,
        subject: str,
        sender: str,
        recipient: str,
        start_time: str,
        end_time: str,
    ) -> HoldMessage | None:
        """Retrieves a held message from Mimecast by searching with given criteria.

        Args:
            subject: Subject line of the email to search for.
            sender: Email address of the sender.
            recipient: Email address of the recipient.
            start_time: Start of time range.
            end_time: End of time range.

        Returns:
            HoldMessage | None: HoldMessage object containing message details and
                attachments if found, None if no matching message is found.

        Raises:
            MimecastException: If API request fails or returns an error.
        """
        messages = self._get_hold_messages_raw(recipient, start_time, end_time)
        message = filter_message(messages, subject, sender)

        if not message:
            return None

        self._enrich_hold_message_with_attachments(message)

        return message

    def get_message_attachments(self, held_message_id: str) -> list[Attachment]:
        """Retrieves attachments for a held message from Mimecast.

        Makes a POST request to Mimecast's API to get attachment details for
        a specific held message identified by its ID.

        Args:
            held_message_id (str): Unique secure identifier of the held message.

        Returns:
            list[Attachment]: List of Attachment objects.

        Raises:
            MimecastException: If the API request fails or returns an error.
        """
        request_url = self._get_full_url("get_message_details")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(
                    uri=ENDPOINTS["get_message_details"]
                )
            )

        payload = {
            "data":[
                {
                    "id": held_message_id
                }
            ]
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)
        attachments = self.parser.build_list_of_attachments(response.json())

        return attachments

    def get_download_url_for_attachment(self, attachment_id: str) -> str:
        """Retrieves the download URL for a specific attachment from Mimecast.

        Makes a POST request to Mimecast's API to get a temporary download URL
        for an attachment identified by its ID.

        Args:
            attachment_id (str): Unique identifier of the attachment to download.

        Returns:
            str: Temporary download URL for the attachment.

        Raises:
            MimecastException: If the API request fails or returns an error.
        """
        request_url = self._get_full_url("get_file")
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["get_file"])
            )

        payload = {
            "data":[
                {
                    "id": attachment_id
                }
            ]
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)
        url = self.parser.parse_url_for_attachment(response.json())

        return url

    def download_attachment(self, url: str) -> bytes:
        """Downloads an attachment from the given URL.

        Args:
            url (str): The URL of the attachment to download.

        Returns:
            bytes: The content of the downloaded attachment.
        """
        if self.is_old_auth:
            self.session.headers.update(
                self._generate_request_headers(uri=ENDPOINTS["download_attachment"])
            )
        response = self.session.get(url=url)
        validate_response(response)

        return response.content
