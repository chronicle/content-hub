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

from typing import Optional, Dict
import copy
from dataclasses import dataclass, field
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson

from ..core.constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAP,
    DEFAULT_RULE_GEN,
)


@dataclass(slots=True)
class IntegrationParameters:
    app_id: str
    api_root: str
    app_key: str
    access_key: str
    secret_key: str
    client_id: str
    client_secret: str
    verify_ssl: bool


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Message(BaseModel):
    def __init__(
        self,
        raw_data,
        tracking_id,
        status,
        received,
        route,
        info,
        subject=None,
        sender=None,
        to=None,
        message_details=None,
    ):
        super(Message, self).__init__(raw_data)
        self.uuid = str(uuid.uuid4())
        self.tracking_id = tracking_id
        self.status = status
        self.received = received
        self.route = route
        self.info = info
        self.message_details = message_details
        self.subject = subject
        self.sender = sender
        self.to = to

    # Added for filter_old_alerts to be able to retrieve id directly from Message object
    @property
    def message_id(self):
        if not self.message_details:
            raise Exception("Fetch message details first to get message id")
        return self.message_details.message_id

    def __hash__(self):
        return hash(self.message_id)

    def __eq__(self, other):
        return self.message_id == other.message_id

    def get_alert_info(
        self, alert_info, environment_common, device_product_field, hold_message
    ):
        """Builds AlertInfo object

        Args:
            alert_info (AlertInfo): The AlertInfo object to be populated.
            environment_common (EnvironmentCommon): The environment
                    common object for fetching the environment.
            device_product_field (str): The field name for the
                    device product in the raw data.
            hold_message (HoldMessage): The hold message object
                    associated with the alert.
        Returns:
            AlertInfo: The populated AlertInfo object.
        """
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.message_id
        alert_info.display_id = self.uuid
        alert_info.name = f"{self.status.capitalize()} Message"
        alert_info.reason = self.message_details.reason
        alert_info.description = self.message_details.queue_detail_status
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.message_details.reason or DEFAULT_RULE_GEN
        alert_info.end_time = alert_info.start_time = convert_string_to_unix_time(
            self.received
        )
        alert_info.events = self.message_details.to_events(
            received_time=self.received, hold_message=hold_message
        )

        return alert_info

    def get_severity(self):
        return SEVERITY_MAP.get(self.message_details.risk, -1)


class MessageDetails(BaseModel):
    def __init__(
        self,
        raw_data,
        message_id,
        tracking_id,
        reason,
        risk,
        queue_detail_status,
        transmission_components,
        components,
        sent,
    ):
        super(MessageDetails, self).__init__(raw_data)
        self.tracking_id = tracking_id
        self.message_id = message_id
        self.reason = reason
        self.risk = risk
        self.queue_detail_status = queue_detail_status
        self.transmission_components = transmission_components
        self.components = components
        self.sent = sent

    def to_events(self, received_time, hold_message):
        """Converts hold message components into a list of flattened event dictionaries.

        Args:
            received_time (str): The time the message was received.
            hold_message (dict): The hold message data.

        Returns:
            list: A list of flattened event dictionaries.
        """
        events = self.get_original_events(hold_message)
        for comp in self.transmission_components:
            comp["received_time"] = received_time
            comp["event_type"] = comp.get("fileType", "").replace(" ", "")
            events.append(dict_to_flat(comp))

        for comp in self.components:
            comp["received_time"] = received_time
            comp["event_type"] = comp.get("type", "").replace(" ", "")
            events.append(dict_to_flat(comp))

        if not events:
            events.append(dict_to_flat(self.to_json()))

        return events

    def get_original_events(self, hold_message=None):
        """Generates original event dictionaries from a hold message.

        Extracts and transforms delivered message data into a list of event
         dictionaries.

        Args:
            hold_message (object, optional): Hold message object with message_id.
            Defaults to None.

        Returns:
            list: A list of flattened event dictionaries.
        """
        original_event = copy.deepcopy(self.to_json())
        delivered_message = original_event.pop("deliveredMessage", None)
        merged_events = []
        hold_message_id = ""
        if hold_message:
            hold_message_id = hold_message.message_id
        if delivered_message:
            for key, value in delivered_message.items():
                event_data = copy.deepcopy(original_event)
                event_data["deliveredMessage"] = value
                event_data["deliveredMessage"]["recipient"] = key
                event_data["event_type"] = "Message"
                if hold_message_id:
                    event_data["holdMessageMetadataID"] = hold_message_id
                merged_events.append(dict_to_flat(event_data))

        return merged_events


class HoldMessage(BaseModel):
    def __init__(
        self,
        raw_data,
        message_id,
        subject,
        sender,
        to,
    ):
        super().__init__(raw_data)
        self.message_id: str = message_id
        self.subject: str = subject
        self.sender: str = sender
        self.to: str = to
        self.attachments: list[Attachment] = []


@dataclass(slots=True)
class BlockSenderPolicyActionParams:
    """
    Data class for Block Sender Policy action parameters.
    """

    response: str
    description: str
    extracted_data: str
    sender: str
    sender_type: str
    recipient: str
    recipient_type: str
    comment: str
    bidirectional: bool
    enforced: bool
    start_time: str | None = None
    end_time: str | None = None

    def create_block_sender_policy_payload(self) -> SingleJson:
        """
        Create the payload for the create block sender policy API call.

        Returns:
            SingleJson: The payload for the API call.
        """
        from_part_mapping = {
            "Both": "both",
            "From Envelope": "envelope_from",
            "From Headers": "header_from",
        }
        payload = {
            "data": [
                {
                    "option": (
                        "block_sender"
                        if self.response == "Block Sender"
                        else "no_action"
                    ),
                    "policy": {
                        "from": _create_sender_recipient_data(
                            self.sender, self.sender_type
                        ),
                        "to": _create_sender_recipient_data(
                            self.recipient, self.recipient_type
                        ),
                        "description": self.description,
                        "enabled": True,
                        "fromPart": from_part_mapping.get(
                            self.extracted_data, "both"
                        ),
                        "bidirectional": self.bidirectional,
                        "comment": self.comment,
                        "enforced": self.enforced,
                    },
                }
            ]
        }

        if self.start_time:
            payload["data"][0]["policy"]["fromDate"] = self.start_time
            payload["data"][0]["policy"]["fromEternal"] = False
        else:
            payload["data"][0]["policy"]["fromEternal"] = True

        if self.end_time:
            payload["data"][0]["policy"]["toDate"] = self.end_time
            payload["data"][0]["policy"]["toEternal"] = False
        else:
            payload["data"][0]["policy"]["toEternal"] = True

        return payload


@dataclass(slots=True)
class BlockSenderPolicy:
    """
    Data model for a Block Sender Policy.
    """

    option: str
    policy_id: str
    description: str
    from_part: str
    from_obj: dict
    to_obj: dict
    from_type: str
    from_value: str
    to_type: str
    to_value: str
    from_eternal: bool
    to_eternal: bool
    override: bool
    bidirectional: bool
    enabled: bool
    enforced: bool
    create_time: str
    last_updated: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    conditions: Dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, block_sender_policy_json: SingleJson):
        """
        Create a BlockSenderPolicy object from raw data.

        Args:
            block_sender_policy_json (SingleJson): Raw data dictionary.

        Returns:
            BlockSenderPolicy: BlockSenderPolicy object.
        """
        return cls(
            option=block_sender_policy_json.get("option"),
            policy_id=block_sender_policy_json.get("id"),
            description=block_sender_policy_json.get("policy", {}).get("description"),
            from_part=block_sender_policy_json.get("policy", {}).get("fromPart"),
            from_obj=block_sender_policy_json.get("policy", {}).get("from"),
            to_obj=block_sender_policy_json.get("policy", {}).get("to"),
            from_type=block_sender_policy_json.get("policy", {}).get("fromType"),
            from_value=block_sender_policy_json.get("policy", {}).get("fromValue"),
            to_type=block_sender_policy_json.get("policy", {}).get("toType"),
            to_value=block_sender_policy_json.get("policy", {}).get("toValue"),
            from_eternal=block_sender_policy_json.get("policy", {}).get("fromEternal"),
            to_eternal=block_sender_policy_json.get("policy", {}).get("toEternal"),
            override=block_sender_policy_json.get("policy", {}).get("override"),
            bidirectional=block_sender_policy_json.get("policy", {}).get(
                "bidirectional"
            ),
            enabled=block_sender_policy_json.get("policy", {}).get("enabled"),
            enforced=block_sender_policy_json.get("policy", {}).get("enforced"),
            create_time=block_sender_policy_json.get("policy", {}).get("createTime"),
            last_updated=block_sender_policy_json.get("policy", {}).get("lastUpdated"),
            from_date=block_sender_policy_json.get("policy", {}).get("fromDate"),
            to_date=block_sender_policy_json.get("policy", {}).get("toDate"),
            conditions=block_sender_policy_json.get("policy", {}).get("conditions", {}),
        )

    def to_json(self):
        """
        Convert the BlockSenderPolicy object to a JSON-compatible dictionary.

        Returns:
            dict: A dictionary representing the BlockSenderPolicy object.
        """
        return {
            "option": self.option,
            "id": self.policy_id,
            "policy": {
                "description": self.description,
                "fromPart": self.from_part,
                "from": self.from_obj,
                "to": self.to_obj,
                "fromType": self.from_type,
                "fromValue": self.from_value,
                "toType": self.to_type,
                "toValue": self.to_value,
                "fromEternal": self.from_eternal,
                "toEternal": self.to_eternal,
                "fromDate": self.from_date,
                "toDate": self.to_date,
                "override": self.override,
                "bidirectional": self.bidirectional,
                "conditions": self.conditions,
                "enabled": self.enabled,
                "enforced": self.enforced,
                "createTime": self.create_time,
                "lastUpdated": self.last_updated,
            },
        }


@dataclass(slots=True)
class Attachment:
    """Represents an email attachment with its metadata.

    Attributes:
        attachment_id: Unique identifier for the attachment
        filename: Original name of the file
        size: Size of the file in bytes
        extension: File extension (e.g. '.pdf')
        content_type: MIME of the file
        content_id: Content ID used in email
        sha256: SHA256 hash of the file
        body_type: Type of the email body
        _file_content: Storage for file content bytes, defaults to None
    """

    raw_data: SingleJson
    attachment_id: str
    filename: str
    size: int
    extension: str
    content_type: str
    content_id: str
    sha256: str
    body_type: str
    file_content: bytes | None = None

    @classmethod
    def from_json(cls, attachment_json: SingleJson) -> Attachment:
        """
        Create an Attachment object from raw data.

        Args:
            attachment_json (SingleJson): Raw data dictionary.

        Returns:
            Attachment: Attachment object.
        """
        return cls(
            raw_data=attachment_json,
            attachment_id=attachment_json["id"],
            filename=attachment_json["filename"],
            size=attachment_json["size"],
            extension=attachment_json["extension"],
            content_type=attachment_json["contentType"],
            content_id=attachment_json["contentId"],
            sha256=attachment_json["sha256"],
            body_type=attachment_json["bodyType"],
            file_content=None,
        )

    def to_json(self):
        return self.raw_data


def _create_sender_recipient_data(value: str, sender_recipient_type: str) -> SingleJson:
    """
    Create the sender or recipient object for the payload.

    Args:
        value (str): The value of the sender or recipient.
        sender_recipient_type (str): The type of the sender or recipient.

    Returns:
        SingleJson: The sender or recipient object.
    """
    sender_recipient_type_mapping = {
        "Email Address": {"emailAddress": value, "type": "individual_email_address"},
        "Email Domain": {"emailDomain": value, "type": "email_domain"},
        "Header Display Name": {
            "headerDisplayName": value,
            "type": "header_display_name",
        },
        "Internal Addresses": {"type": "internal_addresses"},
        "External Addresses": {"type": "external_addresses"},
        "Everyone": {"type": "everyone"},
    }

    sender_data = sender_recipient_type_mapping.get(sender_recipient_type)

    if sender_data is None:
        raise ValueError(f"Invalid sender/recipient type: {sender_recipient_type}")

    return sender_data
