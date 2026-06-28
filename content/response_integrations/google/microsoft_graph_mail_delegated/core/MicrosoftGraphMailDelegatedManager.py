from __future__ import annotations

from typing import Any

from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence, Sequence

from dataclasses import dataclass
from datetime import datetime, timedelta
from email import policy
from email.parser import BytesParser
import time
import json
import mimetypes

from bs4 import BeautifulSoup
import requests

from TIPCommon.base.interfaces import ScriptLogger
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.types import SingleJson
from . import EmailUtils
from . import MicrosoftGraphMailDelegatedParser as parser
from . import api_utils
from . import constants
from .datamodels import (
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
    MicrosoftGraphAttachment,
    SearchResultData,
    SmimeAuth,
    UserOOFSettings,
)
from . import exceptions


EXPAND_WITH_ATTACHMENTS_QUERY = "attachments($select=name,contentType)"


@dataclass(slots=True)
class OdataQueryParameters:
    """Class to create MicrosoftGraphMailDelegated API query."""

    filter_: str = None
    select_: MutableSequence[str] | None = None
    order_by_: str | None = None
    top_: int = constants.PER_REQUEST_ENTITIES_LIMIT
    expand_: str | None = None

    def build_query_dict(self) -> SingleJson:
        """Build the MicrosoftGraphMailDelegated API query dictionary.

        Returns:
            SingleJson: API query dictionary.
        """
        query_dict = {
            "$top": str(self.top_),
            "$select": ",".join(self.select_) if self.select_ else "*",
        }
        if self.filter_ is not None:
            query_dict["$filter"] = self.filter_
        if self.order_by_ is not None:
            query_dict["$order_by"] = self.order_by_
        if self.expand_ is not None:
            query_dict["$expand"] = self.expand_

        return query_dict


@dataclass(slots=True)
class ApiParameters:
    api_root: str
    client_id: str
    client_secret: str
    tenant: str
    mail_address: str


class ApiManager:

    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        logger: ScriptLogger,
        mail_field_source: bool = False,
    ) -> None:
        self.session = session
        self.api_root = api_parameters.api_root
        self.client_id = api_parameters.client_id
        self.client_secret = api_parameters.client_secret
        self.tenant = api_parameters.tenant
        self.mail_address = api_parameters.mail_address
        self.mail_field_source = mail_field_source
        self.logger = logger

    def _send_request(
        self,
        method: str,
        url: str,
        max_retries: int = constants.DEFAULT_MAX_RETRIES,
        **kwargs,
    ) -> requests.Response:
        """
        Send an API request with retry logic for transient errors.
        """
        for i in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == constants.SERVICE_UNAVAILABLE:
                    retry_after = int(
                        response.headers.get(
                            "Retry-After", constants.DEFAULT_RETRY_AFTER
                        )
                    )
                    self.logger.info(
                        f"Request to {url} returned 503. Retrying in "
                        f"{retry_after} seconds."
                    )
                    time.sleep(retry_after)
                    continue

                api_utils.validate_response(response)
                return response

            except requests.exceptions.ReadTimeout as e:
                self.logger.warn(f"Request to {url} timed out. Retrying. Error: {e}")

            if i < max_retries - constants.DECREMENT:
                sleep_time = constants.EXPONENTIAL_BACKOFF_BASE**i
                self.logger.info(f"Retrying in {sleep_time} seconds.")
                time.sleep(sleep_time)

        raise exceptions.TimeoutReachedException(
            f"Request to {url} failed after {max_retries} retries."
        )

    def test_connectivity(self) -> None:
        """Test the connectivity to the Microsoft Graph Delegated API."""
        mail_address = self.get_user_mailbox(self.mail_address)
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_folders",
            tenant=self.tenant,
            mail_address=mail_address,
        )
        response = self.session.get(url=url)
        api_utils.validate_response(response)

    def get_folder_by_name(
        self,
        folder_name: str,
        mail_address: str | None = None,
    ) -> MicrosoftGraphFolder:
        """Retrieves a folder by name, handling localized names and subfolders.

        Args:
            folder_name: The name or path of the folder to retrieve
            (subfolders separated by '/').
            mail_address: The email address to search within.Defaults to the instance's
            configured mail address.

        Raises:
            MicrosoftGraphMailManagerError: If the folder is not found.

        Returns:
            The MicrosoftGraphFolder object representing the found folder.
        """
        mail_address = mail_address or self.mail_address
        root_folder = folder_name.split(constants.SUBFOLDER_DELIMITER)[0]
        folder_localize_names = constants.LOCALE_TRANSLATIONS.get(root_folder, [])
        folder_localize_names.append(root_folder)
        folder_filter = " or ".join(
            f"displayName eq '{name}'" for name in folder_localize_names
        )
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_folders",
            tenant=self.tenant,
            mail_address=mail_address,
        )
        query_params = OdataQueryParameters(
            filter_=folder_filter,
            select_=["id", "displayName"],
        )

        response = self._send_request(
            method="GET",
            url=url,
            params=query_params.build_query_dict(),
        )
        api_utils.validate_response(response)
        results = response.json()["value"]
        if results and constants.SUBFOLDER_DELIMITER in folder_name:
            localize_root_folder = results[0]["displayName"]
            folder_name = folder_name.replace(root_folder, localize_root_folder)
            results = []

        return self._create_folder_from_results(results, folder_name, mail_address)

    def retrieve_mail_id_from_internet_message_id(
        self,
        internet_message_id: str,
        mail_address: str,
    ) -> MicrosoftGraphEmail:
        """Retrieve the mail ID using the internet message ID.

        Args:
            internet_message_id (str): The internet message ID of the email.
            mail_address (str): Mail address to search for the mail.

        Returns:
            MicrosoftGraphEmail: datamodels.MicrosoftGraphEmail object.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_emails_with_filter",
            mail_address=mail_address,
        )
        query_params = {
            "$filter": f"internetMessageId eq '{internet_message_id}'",
            "$expand": EXPAND_WITH_ATTACHMENTS_QUERY,
        }
        response = self.session.get(url=url, params=query_params)
        api_utils.validate_response(response)
        emails = response.json().get("value", [])
        if emails:
            return emails[0]

        raise exceptions.MicrosoftGraphMailManagerError(
            "An error occurred: Id is malformed."
        )

    def _create_folder_from_results(
        self,
        results: MutableSequence[SingleJson],
        folder_name: str,
        mail_address: str,
    ) -> MicrosoftGraphFolder:
        folder = results[0] if results else self._get_folder(folder_name, mail_address)
        if folder is None:
            raise exceptions.MicrosoftGraphMailManagerError(
                f"Mail folder \"{folder_name}\" does not exist"
            )

        return parser.build_mg_folder(folder, mailbox_name=mail_address)

    def _get_folder(
        self,
        folder_name: str,
        mail_address: str,
        parent_folder_id: str | None = None,
        batch_requests: MutableSequence[MutableMapping[str, str]] | None = None,
    ) -> Mapping[str, Any] | None:
        """Retrieves a folder by name, optionally within a parent folder.

        Searches for a folder with the given name within the specified mailbox.
        If a parent folder ID is provided, the search is restricted to its children.
        Uses batch requests if provided for efficiency.

        Args:
            folder_name(str): The name of the folder to search for.
            mail_address(str): The email address to search within.
            parent_folder_id(str | None): The ID of the parent folder (optional).
            batch_requests(SingleJson | None):  Batch requests to use for fetching
            folders (optional).

        Returns:
            Mapping[str, Any] | None: A dictionary containing the folder data if found,
            otherwise None.
        """
        if batch_requests is None:
            results = self._get_folders_without_batch_request(
                parent_folder_id=parent_folder_id,
                mail_address=mail_address,
            )
        else:
            results = self.get_folders_with_batch_request(batch_requests=batch_requests)

        return self._find_folder(
            folder_name=folder_name,
            folders=results,
            mail_address=mail_address,
        )

    def _get_folders_without_batch_request(
        self,
        parent_folder_id: str,
        mail_address: str,
    ) -> MutableSequence[SingleJson]:
        url_id = "get_folders"
        folder_data = {}
        if parent_folder_id is not None:
            url_id = "get_child_folders"
            folder_data = {"folder_id": parent_folder_id}

        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id=url_id,
            tenant=self.tenant,
            mail_address=mail_address,
            **folder_data,
        )
        query_params = OdataQueryParameters(
            top_=constants.MAX_RESULTS_LIMIT,
            select_=["id", "displayName", "childFolderCount"],
        ).build_query_dict()

        return self._paginate_results(url=url, params=query_params)

    def get_folders_with_batch_request(
        self,
        batch_requests: MutableSequence[MutableMapping[str, str]],
    ) -> MutableSequence[SingleJson]:
        """Make a batch request with multiple HTTP requests.

        Args:
            batch_requests MutableSequence[MutableMapping[str, str]],: List of
            dictionaries, each containing details of an individual request.

        Returns:
            MutableSequence[SingleJson]: List of responses corresponding
            to each request.
        """
        batch_url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="batch_request",
            tenant=self.tenant,
        )
        results = api_utils.requests_in_batches(
            request_func=self.session.post,
            batch_url=batch_url,
            batch_requests=batch_requests,
        )

        return self._parse_folder_batch_response(results)

    def _parse_folder_batch_response(
        self,
        results: MutableSequence[SingleJson],
    ) -> MutableSequence[SingleJson]:
        """Parse batch response for get folder API batch request.

        Args:
            results (MutableSequence[SingleJson]): list of batch folders response.

        Returns:
            MutableSequence[SingleJson]: list of folders.
        """
        folders = []
        for response in results:
            if response["status"] in constants.SUCCESS_STATUS_CODES:
                folders.extend(response["body"]["value"])

        return folders

    def _find_folder(
        self,
        folder_name: str,
        folders: MutableSequence[SingleJson],
        mail_address: str,
    ) -> SingleJson | None:
        folder_as_list = folder_name.split(constants.SUBFOLDER_DELIMITER)
        current_folder_name = folder_as_list[0]
        remaining_folder_name = constants.SUBFOLDER_DELIMITER.join(folder_as_list[1:])

        folder = self._find_current_folder(folders, current_folder_name)
        if folder:
            return self._handle_found_folder(
                folder=folder,
                remaining_folder_name=remaining_folder_name,
                mail_address=mail_address,
            )

        return self._search_in_child_folders(folders, folder_name, mail_address)

    def _find_current_folder(
        self,
        folders: Sequence[SingleJson],
        current_folder_name: str,
    ) -> SingleJson | None:
        for folder in folders:
            if folder["displayName"] == current_folder_name:
                return folder

        return None

    def _handle_found_folder(
        self,
        folder: SingleJson,
        remaining_folder_name: str,
        mail_address: str,
    ) -> SingleJson | None:
        if not remaining_folder_name:
            return folder

        if self._has_child_folder(folder):
            return self._get_folder(
                folder_name=remaining_folder_name,
                mail_address=mail_address,
                parent_folder_id=folder["id"],
            )
        return None

    def _search_in_child_folders(
        self,
        folders: Sequence[SingleJson],
        folder_name: str,
        mail_address: str,
    ) -> SingleJson | None:
        folder_ids_with_child = [
            folder["id"] for folder in folders if self._has_child_folder(folder)
        ]
        if folder_ids_with_child:
            batch_requests = self._get_folder_batch_request_payload(
                folder_ids=folder_ids_with_child, mail_address=mail_address
            )

            return self._get_folder(
                folder_name=folder_name,
                mail_address=mail_address,
                batch_requests=batch_requests,
            )

        return None

    def _has_child_folder(self, folder: SingleJson) -> bool:
        return folder[constants.SUB_FOLDER_KEY] > 0

    def _get_folder_batch_request_payload(
        self,
        folder_ids: Iterable[str],
        mail_address: str,
    ) -> MutableSequence[SingleJson]:
        """Get batch request payload data for child folder api calls.

        Args:
            folder_ids (Iterable[str]): list of folder id to search for child folders
            in it.
            mail_address (str): Mail address where to search child folder.

        Returns:
            MutableSequence[SingleJson]: Batch requests list for each folder to get
            child folders.
        """
        params = (
            f"$top={constants.MAX_RESULTS_LIMIT}&"
            "$select=id,displayName,childFolderCount"
        )
        batch_requests = []
        for idx, folder_id in enumerate(folder_ids):
            url = api_utils.get_full_url(
                api_root="",
                url_id="get_child_folders",
                tenant=self.tenant,
                mail_address=mail_address,
                folder_id=folder_id,
            )
            batch_url = f"{url}?{params}".replace(constants.API_VERSION, "")
            batch_request = {"id": str(idx), "method": "GET", "url": batch_url}
            batch_requests.append(batch_request)

        return batch_requests

    def parse_emails(
        self,
        raw_json: SingleJson,
        folder: MicrosoftGraphFolder,
    ) -> tuple[list, str]:
        """Get list of mail object and next link.

        Args:
            raw_json (SingleJson): email response json data.
            folder (str): MicrosoftGraphFolder object.

        Returns:
            tuple: list of mail object and next link.
        """
        new_emails = parser.build_mg_emails(
            raw_json["value"],
            mailbox_name=self.mail_address,
            folder_name=folder.display_name,
        )
        for email in new_emails:
            email.folder_id = folder.id

        next_link = raw_json.get("@odata.nextLink")

        return new_emails, next_link

    def get_emails_by_folder(
        self,
        folder: str,
        datetime_from: datetime,
        max_email_per_cycle: int,
        existing_ids: list[str],
        unread_only: bool = False,
        email_exclude_pattern: str | None = None,
    ) -> MutableSequence[MicrosoftGraphEmail]:
        """get list of email objects from folder.

        Args:
            folder (str): folder to search for the emails.
            datetime_from (datetime): datetime format.
            max_email_per_cycle (int): max email to return per alert cycle.
            existing_ids (list[str]): list of existing ids.
            unread_only (bool, optional): unread email flag. Defaults to False.
            email_exclude_pattern (str, optional): regex to exclude emails.
                Defaults to None.

        Returns:
            MutableSequence[MicrosoftGraphEmail]: list of email objects from folder.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_emails",
            tenant=self.tenant,
            mail_address=folder.mailbox_name,
            folder_id=folder.id,
        )
        filter_string = (
            f"receivedDateTime ge {datetime_from.strftime(constants.TIME_FORMAT)}"
        )
        if unread_only:
            filter_string += " and isRead eq false"
        query_params = OdataQueryParameters(
            filter_=filter_string,
            top_=(
                max_email_per_cycle
                if (max_email_per_cycle < constants.PER_REQUEST_ENTITIES_LIMIT)
                else constants.PER_REQUEST_ENTITIES_LIMIT
            ),
            expand_=EXPAND_WITH_ATTACHMENTS_QUERY,
        )
        response = self.session.get(url=url, params=query_params.build_query_dict())
        api_utils.validate_response(response)
        new_emails, next_link = self.parse_emails(response.json(), folder)
        new_emails, excluded = EmailUtils.filter_emails_with_regexes(
            new_emails, email_exclude_pattern
        )
        fetched_emails = [email for email in new_emails if email.id not in existing_ids]

        self.logger.info(
            f"Fetched {len(fetched_emails)} new emails out of " f"{max_email_per_cycle}"
        )

        while len(fetched_emails) < max_email_per_cycle:
            if next_link is None:
                break

            response = self.session.get(url=next_link)
            api_utils.validate_response(response)
            new_emails, next_link = self.parse_emails(response.json(), folder)
            new_emails, _excluded = EmailUtils.filter_emails_with_regexes(
                new_emails, email_exclude_pattern
            )
            excluded.extend(_excluded)
            fetched_emails.extend(
                email for email in new_emails if email.id not in existing_ids
            )

            self.logger.info(
                f"Fetched {len(fetched_emails)} new emails out of "
                f"{max_email_per_cycle}"
            )

        exclude_mails = "\n".join(f"{email.id} {email.subject}" for email in excluded)
        log_excluded = (
            "Excluded the following emails based on the provided "
            f"Email exclude pattern:\n{exclude_mails}"
        )
        self.logger.info(log_excluded)

        return fetched_emails[:max_email_per_cycle]

    def load_attachments_for_email(
        self,
        folder_id: str,
        email_id: str,
        mail_address: str | None = None,
    ) -> MutableSequence[MicrosoftGraphAttachment]:
        """get the attachment object

        Args:
            folder_id (str): folder id.
            email_id (str): email id to get the attachment.
            mail_address (str | None): mail address to look for the attachment.

        Returns:
            MutableSequence[MicrosoftGraphAttachment]: list of
            datamodels.MicrosoftGraphAttachment objects.
        """
        mail_address = mail_address or self.mail_address
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_attachments",
            tenant=self.tenant,
            mail_address=mail_address,
            folder_id=folder_id,
            email_id=email_id,
        )
        query_params = OdataQueryParameters(
            select_=["id", "size", "contentType", "name"]
        ).build_query_dict()

        response = self.session.get(url, params=query_params)
        api_utils.validate_response(response)

        return parser.build_mg_file_attachments(response.json()["value"])

    def load_attachment_content(
        self,
        folder_id: str,
        email_id: str,
        attachment_id: str,
        mail_address: str | None = None,
    ) -> bytes:
        """get the attachment content as string.

        Args:
            folder_id (str): folder id.
            email_id (str): email id for the attachment.
            attachment_id (str): attachment id to get the content.
            mail_address (str | None): mail address to look for the attachment content.
        Returns:
            bytes: content of attachment as bytes.
        """
        mail_address = mail_address or self.mail_address
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_attachments_content",
            tenant=self.tenant,
            mail_address=mail_address,
            folder_id=folder_id,
            email_id=email_id,
            attachment_id=attachment_id,
        )
        response = self.session.get(url)
        api_utils.validate_response(response)

        return response.content

    def get_emails(
        self,
        folder_name: str,
        datetime_from: datetime,
        max_email_per_cycle: int,
        existing_ids: list[str],
        unread_only: bool = False,
        email_exclude_pattern: str | None = None,
        connector_starting_time: int | None = None,
        script_timeout: int | None = None,
    ) -> MutableSequence[MicrosoftGraphEmail]:
        """Get list of MGM email objects.

        Args:
            folder_name (str): folder name for the emails.
            datetime_from (datetime): datetime to search mail from.
            max_email_per_cycle (int): max email per cycle run.
            existing_ids (list[str]): list of existing ids.
            unread_only (bool, optional): unread email flag. Defaults to False.
            email_exclude_pattern (str, optional): regex to exclude emails.
            Defaults to None.
            connector_starting_time (int, optional): connector starting time.
            Defaults to None.
            script_timeout (int, optional): connector script timeout.
            Defaults to None.

        Returns:
            MutableSequence[MicrosoftGraphEmail]: list of processed mails.
        """
        folder = self.get_folder_by_name(folder_name)
        emails = self.get_emails_by_folder(
            folder=folder,
            datetime_from=datetime_from,
            max_email_per_cycle=max_email_per_cycle,
            existing_ids=existing_ids,
            unread_only=unread_only,
            email_exclude_pattern=email_exclude_pattern,
        )
        processed_emails = []
        for email in emails:
            timeout_approaching = (
                script_timeout
                and connector_starting_time
                and is_approaching_timeout(
                    connector_starting_time=connector_starting_time,
                    python_process_timeout=script_timeout,
                    timeout_threshold=TIMEOUT_THRESHOLD - 0.1,
                )
            )
            if timeout_approaching:
                self.logger.info(
                    "Timeout is approaching. Connector will gracefully exit"
                )
                break

            if not email.has_attachments:
                processed_emails.append(email)
                continue

            self.logger.info(f"Loading attachments for email {email.id}")
            attachments = self.load_attachments_for_email(
                folder_id=folder.id, email_id=email.id
            )
            for attachment in attachments:
                if attachment.is_to_large:
                    self.logger.info(
                        f"Attachment {attachment.id} is to large and it's "
                        "content wouldn't be loaded"
                    )
                    continue
                can_load_content = (
                    attachment.is_file_attachment
                ) or attachment.is_item_attachment
                if can_load_content:
                    attachment.content = self.load_attachment_content(
                        folder_id=folder.id,
                        email_id=email.id,
                        attachment_id=attachment.id,
                    )

            email.set_attachments(attachments)
            processed_emails.append(email)

        return processed_emails

    def mark_emails_as_read(self, emails: MutableSequence[MicrosoftGraphEmail]) -> None:
        """Mark emails as read.

        Args:
            emails (MutableSequence[MicrosoftGraphEmail]): list of emails object to mark
            as read.
        """
        if not emails:
            return
        requests_json = []
        for index, email in enumerate(emails):
            url = api_utils.get_full_url(
                api_root="",
                url_id="relative_email_details",
                tenant=self.tenant,
                mail_address=self.mail_address,
                folder_id=email.folder_id,
                email_id=email.id,
            )
            requests_json.append(
                {
                    "id": index,
                    "method": "PATCH",
                    "url": url.replace(constants.API_VERSION, ""),
                    "body": {"isRead": True},
                    "headers": {"Content-Type": "application/json"},
                }
            )
        batch_uri = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="batch_request",
        )
        _ = api_utils.requests_in_batches(request_func= self.session.post,
                                batch_url= batch_uri,
                                batch_requests= requests_json)

    def get_mail_details(
        self,
        folder: MicrosoftGraphFolder,
        email_id: str,
    ) -> MicrosoftGraphEmail:
        """Get mail details for specific email_id.

        Args:
            folder (MicrosoftGraphFolder): Folder object
            email_id (str): Message id to retrieve mail data.

        Returns:
            MicrosoftGraphEmail: datamodels.MicrosoftGraphEmail object.
        """
        if EmailUtils.EmailUtils.is_graph_mail_id(mail_id=email_id):
            url = api_utils.get_full_url(
                api_root=self.api_root,
                url_id="relative_email_details",
                tenant=self.tenant,
                mail_address=folder.mailbox_name,
                folder_id=folder.id,
                email_id=email_id,
            )

            response = self.session.get(
                url,
                params={"$expand": EXPAND_WITH_ATTACHMENTS_QUERY},
            )
            api_utils.validate_response(response)
            email = response.json()

        else:
            email = self.retrieve_mail_id_from_internet_message_id(
                internet_message_id=email_id,
                mail_address=folder.mailbox_name,
            )
        return parser.build_mg_emails(
            alerts_data=[email],
            mailbox_name=folder.mailbox_name,
            folder_name=folder.display_name,
        )[0]

    def get_all_replies(
        self,
        email: MicrosoftGraphEmail,
        conversation_id: str | None = None,
        internet_message_id: str | None = None,
        filter_with_extended_property: bool = False,
    ) -> MutableSequence[MicrosoftGraphEmail]:
        """Get the object list of all mails in a folder.

        Args:
            email (MicrosoftGraphEmail): MicrosoftGraphEmail object to get it's replies.
            conversation_id (str): Conversation id from get_email_details
            response.
            internet_message_id (str | None): Internet message id to search
            for the thread mail.
            filter_with_extended_property (bool): if filter messages with
            singleValueExtendedProperties for internetMessageHeaders.

        Returns:
            MutableSequence[MicrosoftGraphEmail]: list of datamodels.MicrosoftGraphEmail
            objects.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_emails",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_id=email.reply_folder_id,
        )

        expand_query = EXPAND_WITH_ATTACHMENTS_QUERY
        filter_query = None
        if conversation_id:
            filter_query = f"conversationId eq '{conversation_id}'"

        if internet_message_id:
            filter_query = f"internetMessageId eq '{internet_message_id}'"

        if filter_with_extended_property:
            expand_query += (
                ",singleValueExtendedProperties"
                f"($filter=id eq '{constants.SINGLE_EXTENDED_PROPERTY_VALUE}')"
            )
            filter_query = (
                "singleValueExtendedProperties/any"
                f"(r:r/id eq '{constants.SINGLE_EXTENDED_PROPERTY_VALUE}' and "
                f"contains(r/value,'{internet_message_id}'))"
            )

        query_params = OdataQueryParameters(
            filter_=filter_query, select_="*", top_=50, expand_=expand_query
        )
        response = self.session.get(url, params=query_params.build_query_dict())
        api_utils.validate_response(response)

        return parser.build_mg_emails(
            alerts_data=response.json().get("value", []),
            mailbox_name=email.mailbox_name,
            folder_name=email.folder_name,
        )

    def get_attachments(
        self,
        email: MicrosoftGraphEmail,
    ) -> MutableSequence[MicrosoftGraphAttachment]:
        """Get the object list of attachments for a reply email.

        Args:
            email (MicrosoftGraphEmail): datamodels.MicrosoftGraphEmail object

        Returns:
            MutableSequence[MicrosoftGraphAttachment]: list of
            datamodels.MicrosoftGraphAttachment objects.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_attachments",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_id=email.folder_id,
            email_id=email.id,
        )
        response = self.session.get(url)
        api_utils.validate_response(response)

        return parser.build_mg_attachment(
            raw_data=response.json(),
            mailbox_name=email.mailbox_name,
            folder_name=email.folder_name,
            folder_id=email.folder_id,
            email_id=email.id,
        )

    def get_user_mailbox(self, mail_address: str) -> str:
        """Get user mailbox address using Microsoft Graph API
        Args:
            mail_address (str): The email address to search for.

        Returns
            str: user mailbox address.
        """
        if self.mail_field_source:
            return self.get_user_principal_name_from_mail(mail_address)

        return self.get_user_mailbox_from_user_principal_name(mail_address)

    def get_user_mailbox_from_user_principal_name(self, mail_address: str) -> str:
        """Get user mailbox address using Microsoft Graph API
        Args:
            mail_address (str): The email address to search for.

        Returns
            str: user mailbox address.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="list_user",
            tenant=self.tenant,
            mail_address=mail_address,
        )
        response = self.session.get(url)
        api_utils.validate_response(response)
        self.logger.info(
            f"userPrincipalName {response.json().get('userPrincipalName')}"
        )

        return response.json().get("userPrincipalName")

    def get_user_principal_name_from_mail(self, mail_address: str) -> str | None:
        """Get the user principal name from mailbox address using Microsoft Graph API

        Args:
            mail_address (str): The email address to search for.

        Returns
            str | None: The userPrincipalName corresponding to the email, or
            None if not found.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="list_users",
            tenant=self.tenant,
        )
        query_params = OdataQueryParameters(filter_=f"mail eq '{mail_address}'")
        results = self._paginate_results(url, params=query_params.build_query_dict())
        if results:
            return results[0]["userPrincipalName"]

        raise exceptions.MicrosoftGraphMailManagerError(
            constants.MAILBOX_NOT_FOUND_ERROR
        )

    def search_emails(
        self,
        folders: Iterable[MicrosoftGraphFolder],
    ) -> MutableSequence[MicrosoftGraphEmail]:
        """Search for Microsoft Graph email messages based on specified filters provided
            in list of MicrosoftGraphFolder objects.

        Args:
            folders (Iterable[MicrosoftGraphFolder]): list of MicrosoftGraphFolder
            objects.

        Returns:
            MutableSequence[MicrosoftGraphEmail]: list of datamodels.MicrosoftGraphEmail
            objects.
        """
        emails = []
        for folder in folders:
            url = api_utils.get_full_url(
                api_root=self.api_root,
                url_id="get_emails",
                tenant=self.tenant,
                mail_address=folder.mailbox_name,
                folder_id=folder.id,
            )

            filters, select = create_search_queries(folder)

            query_params = {
                "$top": constants.PER_REQUEST_ENTITIES_LIMIT,
                "$filter": filters,
                "$select": select,
                "$expand": EXPAND_WITH_ATTACHMENTS_QUERY,
            }

            result = self._paginate_results(
                url=url, params=query_params, limit=folder.limit
            )

            emails.extend(
                parser.build_mg_emails(
                    alerts_data=result,
                    mailbox_name=folder.mailbox_name,
                    folder_name=folder.display_name,
                )
            )

        return emails

    def delete_email(self, email: MicrosoftGraphEmail) -> None:
        """Delete a Microsoft Graph email.

        Args:
            email (MicrosoftGraphEmail): The MicrosoftGraphEmail object to be deleted.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="relative_email_details",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_id=email.folder_id,
            email_id=email.id,
        )
        response = self.session.delete(url)
        api_utils.validate_response(response)

    def _paginate_results(
        self,
        url: str,
        params: dict | None = None,
        limit: int | None = None,
    ) -> MutableSequence[SingleJson]:
        """Paginates through API results.

        Args:
            url (str): URL for the request.
            params (dict | None): Parameters for the request.
            limit (int | None): limit for the number of results to fetch.

        Returns:
            MutableSequence[SingleJson]: List of parsed results.
        """
        results = []
        while url:
            if limit and len(results) >= limit:
                break

            response = self.session.get(url, params=params)
            api_utils.validate_response(response)

            current_items = response.json().get("value", [])
            results.extend(current_items)

            url = response.json().get("@odata.nextLink")
            params = {}

        return results[:limit] if limit else results

    def send_email(
        self,
        send_from: str,
        subject: str,
        send_to: MutableSequence[str],
        mail_content: str,
        cc: MutableSequence[str] | None = None,
        bcc: MutableSequence[str] | None = None,
        attachments_data: MutableSequence[MutableMapping[str, str]] | None = None,
        mail_content_type: str | None = None,
        reply_to: MutableSequence[str] | None = None,
    ) -> MicrosoftGraphEmail:
        """Creates a draft email and send it using Microsoft Graph API.

        Args:
            send_from (str): The sender's email address.
            subject (str): The subject of the email.
            send_to (MutableSequence[str]): List of email addresses to send the email
            to.
            mail_content (str): The content of the email.
            cc (MutableSequence[str] | None): List of email addresses to be cc'd.
            bcc (MutableSequence[str] | None): List of email addresses to be bcc'd.
            attachments_data (MutableSequence[MutableMapping[str, str]] | None): List of
            file paths for email attachments.
            mail_content_type (str | None): The content type of the email body.
            reply_to (MutableSequence[str] | None): List of email addresses for
            reply-to.

        Returns:
            MicrosoftGraphEmail: MicrosoftGraphEmail object.
        """
        mail_address = send_from or self.mail_address
        payload = {
            "subject": subject,
            "body": {"content": mail_content, "contentType": mail_content_type},
            "toRecipients": [
                {"emailAddress": {"address": recipient}} for recipient in send_to
            ],
            "ccRecipients": [
                {"emailAddress": {"address": receiver}} for receiver in (cc or [])
            ],
            "bccRecipients": [
                {"emailAddress": {"address": receiver}} for receiver in (bcc or [])
            ],
            "replyTo": [
                {"emailAddress": {"address": receiver}} for receiver in (reply_to or [])
            ],
        }

        if attachments_data:
            payload["attachments"] = attachments_data

        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="create_draft",
            tenant=self.tenant,
            mail_address=send_from,
        )
        response = self.session.post(url, json=payload)
        api_utils.validate_response(response)
        email = parser.build_mg_emails(
            alerts_data=[response.json()], mailbox_name=mail_address, folder_name=None
        )[0]
        self.send_draft_email(send_from=mail_address, email_id=email.id)

        return email

    def send_vote_html_email(
        self,
        send_from: str,
        subject: str,
        send_to: MutableSequence[str],
        mail_content: str,
        cc: MutableSequence[str] | None = None,
        bcc: MutableSequence[str] | None = None,
        attachments_data: MutableSequence[MutableMapping[str, str]] | None = None,
        reply_to: MutableSequence[str] | None = None,
        voting_option: str | None = None,
    ) -> MicrosoftGraphEmail:
        """Creates a draft vote/html email and send it using Microsoft Graph API.

        Args:
            send_from (str): The sender's email address.
            subject (str): The subject of the email.
            send_to (MutableSequence[str]): List of email addresses to send the email
            to.
            mail_content (str): The content of the email.
            cc (MutableSequence[str]): List of email addresses to be cc'd.
            bcc (MutableSequence[str]): List of email addresses to be bcc'd.
            attachments_data (MutableSequence[MutableMapping[str, str]]): List of file
            paths for  email attachments.
            reply_to (MutableSequence[str]): List of email addresses for reply-to.
            voting_option(str): Structure of the vote to send to the recipients.

        Returns:
            MicrosoftGraphEmail: MicrosoftGraphEmail object.
        """
        mail_address = send_from or self.mail_address
        image_files = _extract_images_from_html(mail_content)
        mail_content = _clean_siemplify_html(mail_content)

        payload = {
            "subject": subject,
            "body": {"content": mail_content, "contentType": "Html"},
            "toRecipients": [
                {"emailAddress": {"address": recipient}} for recipient in send_to
            ],
            "ccRecipients": [
                {"emailAddress": {"address": receiver}} for receiver in (cc or [])
            ],
            "bccRecipients": [
                {"emailAddress": {"address": receiver}} for receiver in (bcc or [])
            ],
            "replyTo": [
                {"emailAddress": {"address": receiver}} for receiver in (reply_to or [])
            ],
        }
        if attachments_data or image_files:
            payload["attachments"] = (attachments_data or []) + (image_files or [])

        if voting_option:
            payload["singleValueExtendedProperties"] = [
                {
                    "id": constants.VOTING_OPTIONS_ID,
                    "value": constants.ENCODED_VOTING_OPTIONS.get(voting_option),
                }
            ]

        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="create_draft",
            tenant=self.tenant,
            mail_address=send_from,
        )
        response = self.session.post(url, json=payload)
        api_utils.validate_response(response)
        email = parser.build_mg_emails(
            alerts_data=[response.json()],
            mailbox_name=mail_address,
            folder_name=None,
        )[0]
        self.send_draft_email(send_from=mail_address, email_id=email.id)

        return email

    def send_draft_email(self, send_from: str, email_id: str) -> None:
        """Send email from the draft folder.

        Args:
            send_from (str): The sender's email address.
            email_id (str): email id for that email to be send.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="send_email",
            tenant=self.tenant,
            mail_address=send_from,
            email_id=email_id,
        )
        response = self.session.post(url)
        api_utils.validate_response(response)

    def send_thread_reply(
        self,
        email: MicrosoftGraphEmail,
        mail_content: str,
        send_from: str,
        attachments_data: MutableSequence[SingleJson] | None = None,
        reply_all: bool = False,
        reply_to: MutableSequence[str] | None = None,
    ) -> MicrosoftGraphEmail:
        """Reply to a message using the Microsoft Graph API.

        Args:
            email (MicrosoftGraphEmail): MicrosoftGraphEmail object.
            folder_name (str): The name of the folder containing the message.
            mail_content (str): The content of the reply email.
            send_from (str): The email address from which to send the reply.
            attachments_data (MutableSequence[SingleJson] | None): List of file paths
            for attachments.
            reply_all (bool): Whether to reply to all recipients.
            reply_to (MutableSequence[str] | None): The email address to reply to.
        """
        mail_address = send_from if send_from else self.mail_address
        reply_payload = {
            "comment": mail_content,
            "message": {
                "toRecipients": [
                    {"emailAddress": {"address": reply}} for reply in (reply_to or [])
                ],
                "attachments": attachments_data,
            },
        }
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="create_thread_draft",
            tenant=self.tenant,
            mail_address=mail_address,
            email_id=email.id,
        )
        if not reply_all and not reply_to:
            reply_payload["message"]["toRecipients"] = [
                {"emailAddress": {"address": email.sender}}
            ]

        if reply_all:
            url += constants.REPLY_ALL
            reply_payload["message"].pop("toRecipients")

        response = self.session.post(url, json=reply_payload)
        api_utils.validate_response(response)
        email = parser.build_mg_emails(
            alerts_data=[response.json()],
            mailbox_name=mail_address,
            folder_name=None,
        )[0]
        self.send_draft_email(send_from=mail_address, email_id=email.id)

        return email

    def move_email_to_folder(
        self,
        email: MicrosoftGraphEmail,
        destination_folder: str,
    ) -> MicrosoftGraphEmail:
        """Move email in mailbox from source folder to destination folder.

        Args:
            email (MicrosoftGraphEmail): MicrosoftGraphEmail object.
            destination_folder (str): destination folder to move email.

        Returns:
            MicrosoftGraphEmail: MicrosoftGraphEmail object.
        """
        dst_folder = self.get_folder_by_name(
            folder_name=destination_folder, mail_address=email.mailbox_name
        )
        payload = {"destinationId": dst_folder.id}
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="move_email_to_folder",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_id=email.folder_id,
            email_id=email.id,
        )
        response = self.session.post(url, json=payload)
        api_utils.validate_response(response)
        moved_email = self.get_mail_details(dst_folder, response.json()["id"])
        moved_email.destination_folder = destination_folder

        return moved_email

    def forward_email(
        self,
        send_from: str,
        email_id: str,
        subject: str,
        send_to: MutableSequence[str],
        mail_content: str,
        cc: MutableSequence[str] | None = None,
        bcc: MutableSequence[str] | None = None,
        attachments_data: MutableSequence[SingleJson] | None = None,
    ) -> MicrosoftGraphEmail:
        """Create forward email in draft folder.

        Args:
            send_from (str): The sender's email address.
            email_id (str): The ID of the message to reply to.
            subject (str): The subject of the email.
            send_to (MutableSequence[str]): List of email addresses to send the email
            to.
            mail_content (str): The content of the email.
            cc (MutableSequence[str] | None): List of email addresses to be cc'd.
            bcc (MutableSequence[str] | None): List of email addresses to be bcc'd.
            attachments_data (MutableSequence[SingleJson]): List of file paths for email
            attachments.

        Returns:
            MicrosoftGraphEmail: MicrosoftGraphEmail object.
        """
        mail_address = send_from or self.mail_address
        payload = {
            "comment": mail_content,
            "message": {
                "subject": subject,
                "toRecipients": [
                    {"emailAddress": {"address": recipient}} for recipient in send_to
                ],
                "ccRecipients": [
                    {"emailAddress": {"address": receiver}} for receiver in (cc or [])
                ],
                "bccRecipients": [
                    {"emailAddress": {"address": receiver}} for receiver in (bcc or [])
                ],
            },
        }

        if attachments_data:
            payload["message"]["attachments"] = attachments_data

        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="create_forward_draft",
            tenant=self.tenant,
            mail_address=mail_address,
            email_id=email_id,
        )

        response = self.session.post(url, json=payload)
        api_utils.validate_response(response)
        email = parser.build_mg_emails(
            alerts_data=[response.json()],
            mailbox_name=mail_address,
            folder_name=None,
        )[0]
        self.send_draft_email(send_from=mail_address, email_id=email.id)

        return email

    def load_email_content(self, email: MicrosoftGraphEmail) -> bytes:
        """Get the attachment content as string.
        Args:
            email (MicrosoftGraphEmail): email MicrosoftGraphEmail object.

        Returns:
            bytes: content of email as bytes.
        """
        full_url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_email_content",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            email_id=email.id,
        )
        response = self.session.get(full_url)
        api_utils.validate_response(response)

        return response.content

    def download_attachment_from_email(
        self,
        attachment: MicrosoftGraphAttachment,
        download_from_eml: bool,
        path: str,
        smime_auth: SmimeAuth,
    ) -> MutableSequence[SingleJson]:
        """Download attachments for Microsoft Graph email based on specified filters.

        Args:
            attachment (MicrosoftGraphAttachment): MicrosoftGraphAttachment
            path (str): Path on the server where to download the email attachments
            download_from_eml (bool): Specify whether to download attachments also from
            attached EML files.
            smime_auth(SmimeAuth): SmimeAuth object.

        Returns:
            MutableSequence[SingleJson]: List of attachment data dictionaries
        """
        attachment_content = self.load_attachment_content(
            folder_id=attachment.folder_id,
            email_id=attachment.email_id,
            attachment_id=attachment.id,
            mail_address=attachment.mailbox_name,
        )

        files_data = [
            {
                "attachment_name": self.get_attachment_name(attachment),
                "attachment_content": attachment_content,
                "path": path,
            }
        ]

        if download_from_eml and attachment.is_eml:
            attachment_content = EmailUtils.get_decrypted_mime_content(
                mime_content=attachment_content,
                smime_auth=smime_auth,
                logger=self.logger,
            )

        return files_data

    def get_attachment_name(self, attachment: MicrosoftGraphAttachment) -> str:
        """Gets name of attachments for Microsoft Graph email.

        Args:
            attachment(MicrosoftGraphAttachment): MicrosoftGraphAttachment

        Returns:
            str: Name of the attachments.
        """
        if attachment.is_item_attachment and not attachment.name:
            self.logger.warn(
                f"The name and subject for attachment {attachment.id} are empty, "
                "using randomly generated file name instead"
            )
            return "attachment.eml" if attachment.is_eml else "attachment"

        return (
            f"{attachment.name}.eml"
            if attachment.is_item_attachment and attachment.is_eml
            else attachment.name
        )

    def get_attachment_from_eml(
        self,
        attachment_content: MicrosoftGraphAttachment,
        path: str,
    ) -> MutableSequence[SingleJson]:
        """Extracts attachments from EML data.

        Extract attachments from an EML represented by MicrosoftGraphAttachment object.

        Args:
            attachment_content (MicrosoftGraphAttachment): The attachment data from
            Microsoft Graph.
            path (str): The base path to use for attachment saving.

        Returns:
            MutableSequence[SingleJson]: A list of extracted attachment data .
        """
        files_data = []

        msg = BytesParser(policy=policy.default).parsebytes(attachment_content)
        if msg.is_multipart():
            for part in msg.iter_attachments():
                attachment_data = self.parse_eml_attachment(part)

                if attachment_data["content_type"] in constants.EML_TYPES:
                    files_data.extend(
                        self.eml_types_attachments(part, attachment_data, path)
                    )
                else:
                    files_data.append(
                        self.handle_regular_attachments(
                            attachment_data["filename"],
                            attachment_data["content"],
                            path,
                        )
                    )

        return files_data

    def parse_eml_attachment(self, part: Any) -> SingleJson:
        """Extracts content type, filename, and content from the attachment.

        Args:
            part (Any): The part of the EML attachment.

        Returns:
            SingleJson: A dictionary containing content_type, filename, and content.
        """
        content_type = part.get_content_type()
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        return {
            "content_type": content_type,
            "filename": filename,
            "content": payload
        }

    def handle_regular_attachments(
        self,
        filename: str,
        content: bytes,
        path: str,
    ) -> SingleJson:
        """Extracts data for a regular attachment.

        Args:
            filename (str): The filename of the attachment.
            content (bytes): The content of the attachment.
            path (str): The base path to use for attachment saving.

        Returns:
            SingleJson: A dictionary containing attachment data for the regular
            attachment.
        """
        return {
            "attachment_name": filename,
            "attachment_content": content,
            "path": path,
        }

    def eml_types_attachments(
        self,
        part: Any,
        attachment_data: SingleJson,
        path:str,
    ) -> MutableSequence[SingleJson]:
        """Extracts data for EML Type attachments and potential nested EMLs within them.

        Args:
            part (Any): The EmailPart object representing the attachment.
            attachment_data (SingleJson): A dictionary containing filename, content.
            path (str): The base path for attachment saving.

        Returns:
            MutableSequence[SingleJson]: A list containing dictionaries with details of
            extracted attachments.
        """
        files_data = []
        filename = attachment_data["filename"]
        nested_eml = None
        try:
            nested_eml = part.get_payload(0)

        except TypeError as e:
            self.logger.info(f"Saving nested EML attachment: {e}")

        if nested_eml:
            nested_filename = f"{nested_eml.get('Subject', 'NestedEML')}.eml"
            nested_content = nested_eml.as_bytes()
            files_data.extend(
                self.extract_nested_attachment(nested_filename, nested_content, path)
            )

        elif filename:
            if not filename.lower().endswith(".eml"):
                filename += ".eml"
            files_data.extend(
                self.extract_nested_attachment(
                    filename, attachment_data["content"], path
                )
            )

        return files_data

    def extract_nested_attachment(
        self,
        filename: str,
        content: bytes,
        path: str,
    ) -> MutableSequence[SingleJson]:
        """Extracts details of nested attachments from EML content.

        Args:
            filename (str): The filename of the attachment.
            content (bytes): The content of the attachment.
            path (str): The base path to be passed for attachment saving.

        Returns:
            MutableSequence[SingleJson]: A list containing dictionaries with details of
            attachments.
        """
        details = []
        details.append(self.handle_regular_attachments(filename, content, path))
        details.extend(self.get_attachment_from_eml(content, path))

        return details

    def mark_email_as_junk(self, email: MicrosoftGraphEmail) -> None:
        """Marks the specified email as "Junk" for the given mailbox and folder.

        Args:
            email (MicrosoftGraphEmail): The MicrosoftGraphEmail to mark as "Junk".

        Returns:
            None
        """
        payload = {"moveToJunk": True}
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="mark_as_junk",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_name=email.folder_id,
            email_id=email.id,
        )
        response = self.session.post(url=url, json=payload)
        api_utils.validate_response(response)

    def mark_email_as_not_junk(self, email: MicrosoftGraphEmail) -> None:
        """Marks the specified email as "Not Junk" for the given mailbox and folder.

        Args:
            email (MicrosoftGraphEmail): The MicrosoftGraphEmail to mark as "Not Junk".

        Returns:
            None
        """
        payload = {"moveToInbox": True}
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="mark_as_not_junk",
            tenant=self.tenant,
            mail_address=email.mailbox_name,
            folder_name=email.folder_id,
            email_id=email.id,
        )
        response = self.session.post(url=url, json=payload)
        api_utils.validate_response(response)

    def get_user_id(self, mail_address: str) -> str:
        """Get user Id using Microsoft Graph API.

        Args:
            mail_address (str): Mail address for which the user id need to be fetched.

        Returns:
            str: Id of the address.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="list_user",
            tenant=self.tenant,
            mail_address=mail_address,
        )
        response = self.session.get(url)
        api_utils.validate_response(response)

        return response.json()["id"]

    def get_user_oof_settings(self, user_id: str) -> UserOOFSettings:
        """Get user out of facility settings using Microsoft Graph API.

        Args:
            user_id (str): Id of the mail address.

        Returns:
            UserOOFSettings: OOF settings for user.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_oof_settings",
            tenant=self.tenant,
            user_id=user_id,
        )
        response = self.session.get(url)
        api_utils.validate_response(response)

        return parser.build_mg_oof_settings_object(raw_data=response.json())

    def run_microsoft_search_query(
        self,
        entity_types_to_search: MutableSequence[str],
        fields_to_return: MutableSequence[str],
        search_query: str,
        max_rows_to_return: int,
        advanced_query: str | None = None,
    ) -> MutableSequence[SearchResultData]:
        """Run Microsoft search query.

        Args:
            entity_types_to_search (MutableSequence[str]): List of entities to search.
            fields_to_return (MutableSequence[str]): List of fields to return.
            search_query (str): Search query.
            max_rows_to_return (int): Max rows to return.
            advanced_query (str | None): Advance query. Defaults to None.

        Returns:
            MutableSequence[SearchResultData]: List of SearchResultData objects.
        """
        search_response: MutableSequence[SearchResultData] = []

        url = api_utils.get_full_url(api_root=self.api_root, url_id="search_query")
        if advanced_query:
            payload = json.loads(advanced_query)
            response = self.session.post(url, json=payload)
            api_utils.validate_response(response)
            response_json = response.json().get("value", [])[0]["hitsContainers"][0]
            if response_json["total"] == 0:
                return []

            response = response_json["hits"]
        else:
            payload = self._get_search_request_payload(
                entity_types=entity_types_to_search,
                fields_to_return=fields_to_return,
                search_query=search_query
            )
            response = self._paginate_search_query_results(
                url=url,
                json_data=payload,
                limit=max_rows_to_return,
            )

        if len(response) > 0:
            search_response.extend(
                parser.build_search_results(response_json=response)
            )
            return search_response

        return []

    def _paginate_search_query_results(
        self,
        url: str,
        json_data: SingleJson,
        limit: int | None = None,
    ) -> MutableSequence[SingleJson]:
        """Paginate through API results.

        Args:
            url (str): The URL for the request.
            json_data (SingleJson): The JSON body for the request.
            limit (int | None): The maximum number of results to fetch.

        Returns:
            MutableSequence[SingleJson]: A list of parsed results.
        """
        results = []
        offset = 0

        while url:
            if limit and len(results) >= limit:
                break

            if "requests" not in json_data or not json_data["requests"]:
                raise exceptions.MicrosoftGraphMailManagerError("invalid query start")

            json_data["requests"][0]["from"] = offset

            response = self.session.post(url, json=json_data)
            api_utils.validate_response(response)
            response = response.json().get("value", [])[0]["hitsContainers"][0]

            if response["total"] > 0:
                current_items = response["hits"]
                results.extend(current_items)

                more_results_available = response["moreResultsAvailable"]
                if not more_results_available:
                    break

                offset += len(current_items)
            else:
                return []

        return results[:limit] if limit else results

    def _get_search_request_payload(
        self,
        entity_types: MutableSequence[str],
        fields_to_return: MutableSequence[str],
        search_query: str,
    ) -> SingleJson:
        """Get search request payload.

        Args:
            entity_types (MutableSequence[str]): List of entities to search.
            fields_to_return (MutableSequence[str]): List of fields to return.
            search_query (str): Search query.

        Returns:
            SingleJson: Search request payload.
        """
        payload: SingleJson = {
            "requests": [
                {
                    "entityTypes": entity_types,
                    "query": {
                        "queryString": search_query,
                    },
                    "from": 0,
                    "size": constants.DEFAULT_SEARCH_SIZE,
                    **({"fields": fields_to_return} if fields_to_return else {}),
                }
            ]
        }

        return payload


def _extract_images_from_html(
    html_body: str,
) -> MutableSequence[MicrosoftGraphAttachment]:
    """Run over siemplify html template and retrieve all <cstImage> tags elements
    in order to create embedded image in mail.

    Args
        html_body{str}: Siemplify html convention template

    Return:
        MutableSequence[MicrosoftGraphAttachment]: Attachments object.
    """
    images = []
    soup = BeautifulSoup(html_body)
    for cst_tag in soup.findAll(constants.HTML_IMAGE_TAG):
        image_name = cst_tag[constants.HTML_IMAGE_TAG_NAME_ATTR]
        image_content = cst_tag[constants.HTML_IMAGE_TAG_BASE64_ATTR]
        content_type, _ = mimetypes.guess_type(image_name)
        images.append(
            {
                "@odata.type": constants.FILE_ATTACHMENT_ODATA_TYPE,
                "name": image_name,
                "contentType": content_type,
                "contentBytes": image_content,
            }
        )

    return images


def _clean_siemplify_html(html_body: str) -> str:
    """Remove <cstImage> tags elements from siemplify html convention template

    Args:
        html_body{str}: Siemplify html convention template

    Return:
        str: the new html body
    """
    soup = BeautifulSoup(html_body)
    for cst_tag in soup.findAll(constants.HTML_IMAGE_TAG):
        cst_tag.extract()

    return soup.prettify()


def create_time_filter(time_filter: int) -> str:
    """Create time filter for provided time filter.

    Args:
        time_filter (int): time filter in minutes.

    Returns:
        str: datetime time filter string.
    """
    time_frame_minutes = time_filter
    utc_now = datetime.utcnow()
    filter_time_frame = utc_now - timedelta(minutes=time_frame_minutes)

    return filter_time_frame.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def create_search_queries(folder: MicrosoftGraphFolder) -> tuple[str, str]:
    """Create filter and select queries for search emails.

    Args:
        folder (MicrosoftGraphFolder): MicrosoftGraphFolder object.

    Returns:
        tuple[str, str]: tuple of filter and select queries as string.
    """

    filters = []
    select_fields = []

    if folder.subject_filter:
        subject_filter = folder.subject_filter.replace("'", "''")
        filters.append(f"contains(subject, '{subject_filter}')")

    if folder.sender_filter:
        filters.append(f"sender/emailAddress/address eq '{folder.sender_filter}'")

    if folder.time_filter:
        filter_time_frame_str = create_time_filter(folder.time_filter)
        filters.append(f"receivedDateTime ge {filter_time_frame_str}")

    if folder.only_unread:
        filters.append("isRead eq false")

    if folder.is_all_field:
        select_fields.append("*")

    filter_query = " and ".join(filters)
    select_field = ",".join(select_fields)

    return filter_query, select_field
