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

import datetime
from typing import Any, TYPE_CHECKING

from .api_utils import validate_response
from .constants import QUARANTINE_ENDPOINT, TIME_FORMAT
from .data_parser import parse_quarantine_records
from .exceptions import ProofPointPSHTTPError

if TYPE_CHECKING:
    import requests

    from .data_models import QuarantineRecord


class SearchResults(list):
    """Custom list subclass that holds search results and metadata such as query_id."""
    query_id: str | None

    def __init__(self, records: list[Any], query_id: str | None = None) -> None:
        super().__init__(records)
        self.query_id = query_id


class ProofPointPSApiClient:
    """API client for ProofPointPS."""

    def __init__(
        self,
        server_address: str,
        authenticated_session: requests.Session,
    ) -> None:
        self.server_address = server_address
        self.session = authenticated_session

    def test_connectivity(self) -> bool:
        """Test connectivity to ProofPoint PS.

        Returns:
            True if successful, exception otherwise.

        """
        self.search(sender="*")
        return True

    def search(
        self,
        sender: str | None = None,
        recipient: str | None = None,
        subject: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        folder: str | None = None,
        dlpviolation: str | None = None,
        messagestatus: str | None = None,
        limit: int | None = None,
        guid: str | None = None,
        msgid: str | None = None,
    ) -> list[QuarantineRecord]:
        """Search for quarantine messages with the specified parameters.

        Args:
            sender: The sender of the message.
            recipient: The recipient of the message.
            subject: The subject of the message.
            start_date: The UTC start date of the range.
            end_date: The UTC end date of the range.
            folder: The quarantine folder name.
            dlpviolation: "t" or "details" to fetch DLP data.
            messagestatus: "t" to fetch message status and comments.
            limit: The maximum number of records to return.
            guid: Optional message GUID filter.
            msgid: Optional message-id filter.

        Returns:
            A list of found records.

        """
        url = f"{self.server_address.rstrip('/')}{QUARANTINE_ENDPOINT}"

        data = {
            "from": sender,
            "rcpt": recipient,
            "subject": subject,
            "startdate": start_date,
            "enddate": end_date,
            "folder": folder,
            "dlpviolation": dlpviolation,
            "messagestatus": messagestatus,
            "limit": limit,
            "guid": guid,
            "msgid": msgid,
        }

        data = {key: value for key, value in data.items() if value is not None}
        response = self.session.get(url, params=data)

        validate_response(response, "Unable to search emails")
        try:
            response_json = response.json()
        except ValueError as error:
            msg = (
                "Unable to search emails: The server returned an invalid or "
                f"empty JSON response. Status Code: {response.status_code}. "
                f"Content Preview: {response.text[:200]}"
            )
            raise ProofPointPSHTTPError(msg) from error

        records_list = parse_quarantine_records(response_json)

        meta = response_json.get("meta", {})
        query_id_meta = meta.get("queryid") or meta.get("query_id")

        return SearchResults(records_list, query_id=query_id_meta)

    def execute_quarantine_action(
        self,
        action: str,
        folder: str,
        localguid: list[str] | str,
        deletedfolder: str | None = None,
        targetfolder: str | None = None,
        scan: str | None = None,
        brandtemplate: str | None = None,
        securitypolicy: str | None = None,
        subject: str | None = None,
        appendoldsubject: str | None = None,
        from_address: str | None = None,
        headerfrom: str | None = None,
        to_address: str | None = None,
        comment: str | None = None,
    ) -> bool:
        """Execute a quarantine action (release, resubmit, forward, move, delete).

        Args:
            action: Action name ("release", "resubmit", "forward",
                "move", "delete").
            folder: Folder name where the message is stored.
            localguid: Message GUID(s) to process.
            deletedfolder: Optional folder to move deleted/released/
                forwarded messages to.
            targetfolder: Folder name to move the message to.
            scan: Rescan message with DLP ("t").
            brandtemplate: Encryption branding template.
            securitypolicy: Encryption response profile.
            subject: New subject for forward action.
            appendoldsubject: "t" to append old subject on forward.
            from_address: Envelope from for forward action.
            headerfrom: Header from for forward action.
            to_address: Recipient email address(es) for forward.
            comment: New message body for forward action.

        Returns:
            True if successful, exception otherwise.

        """
        url = f"{self.server_address.rstrip('/')}{QUARANTINE_ENDPOINT}"

        if isinstance(localguid, list):
            localguid = ",".join(localguid)

        payload = {
            "action": action,
            "folder": folder,
            "localguid": localguid,
            "deletedfolder": deletedfolder,
            "targetfolder": targetfolder,
            "scan": scan,
            "brandtemplate": brandtemplate,
            "securitypolicy": securitypolicy,
            "subject": subject,
            "appendoldsubject": appendoldsubject,
            "from": from_address,
            "headerfrom": headerfrom,
            "to": to_address,
            "comment": comment,
        }

        payload = {key: value for key, value in payload.items() if value is not None}
        response = self.session.post(url, json=payload)

        validate_response(response, f"Unable to {action} email(s)")
        return True

    def get_record_by_guid(
        self,
        guid: str,
        folder: str | None = None,
        sender: str | None = "*",
    ) -> QuarantineRecord | None:
        """Retrieve a quarantined message record by GUID and optional folder constraint.

        Args:
            guid: The Message GUID to search for.
            folder: Optional folder name to search in.
            sender: Optional sender email address to search by.

        Returns:
            The QuarantineRecord if found, None otherwise.

        """
        start_date = (
            datetime.datetime.utcnow() - datetime.timedelta(days=30)
        ).strftime(TIME_FORMAT)
        end_date = datetime.datetime.utcnow().strftime(TIME_FORMAT)

        records = self.search(
            sender=sender or "*",
            folder=folder,
            start_date=start_date,
            end_date=end_date,
        )
        for r in records:
            if r.guid == guid or r.localguid == guid:
                return r

        return None

    def download_message(self, guid: str) -> bytes:
        """Retrieve raw quarantined message bytes by GUID.

        Args:
            guid: The Message GUID.

        Returns:
            Raw email bytes.

        """
        url = f"{self.server_address.rstrip('/')}{QUARANTINE_ENDPOINT}"
        params = {"guid": guid}
        response = self.session.get(url, params=params)

        validate_response(response, "Unable to download email")
        return response.content
