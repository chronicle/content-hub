from __future__ import annotations

import copy
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import add_prefix_to_dict, dict_to_flat, flat_dict_to_csv

from .constants import (
    API_VERSION_2_1,
    API_VERSION_2_2,
    API_VERSION_2_5,
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    RULE_GENERATOR,
    SEVERITY_MAP,
)
from .UtilsManager import get_alert_id

# Defining constants
ASSIGNMENT_ID = "Assignment ID"
PIPE = "   |   "


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Detection(BaseModel):
    """Detection model to store detection data"""

    def __init__(self, data):
        self.raw_data = data
        self.raw_data["detection_url"] = (
            self.raw_data.get("detection_url", "")
            .replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
        self.raw_data["url"] = (
            self.raw_data.get("url", "")
            .replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
        self.detection_id = data.get("id")
        self.state = data["state"]
        self.category = data["category"]
        self.detection_type = data["detection_type"]
        self.last_detection_timestamp = data["last_timestamp"]
        self.threat = data["threat"]
        self.entity_id = None
        self.entity_name = None
        self.detection_url = data.get("detection_url", "")
        self.detection_url = (
            self.detection_url.replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
        )
        if data["src_account"]:
            self.entity_id = data["src_account"]["id"]
            self.entity_name = data["src_account"]["name"]
            self.raw_data["src_account"]["url"] = (
                self.raw_data["src_account"]["url"]
                .replace(API_VERSION_2_5, "")
                .replace(API_VERSION_2_1, "")
                .replace(API_VERSION_2_2, "")
            )
        elif data["src_host"]:
            self.entity_id = data["src_host"]["id"]
            self.entity_name = data["src_host"]["name"]
            if self.raw_data["src_host"].get("url"):
                self.raw_data["src_host"]["url"] = (
                    self.raw_data["src_host"]["url"]
                    .replace(API_VERSION_2_5, "")
                    .replace(API_VERSION_2_1, "")
                    .replace(API_VERSION_2_2, "")
                )
        if data.get("src_linked_account"):
            self.raw_data["src_linked_account"]["url"] = (
                self.raw_data["src_linked_account"]["url"]
                .replace(API_VERSION_2_5, "")
                .replace(API_VERSION_2_1, "")
                .replace(API_VERSION_2_2, "")
            )

    def to_csv(self):
        return flat_dict_to_csv(
            {
                "ID": self.detection_id,
                "Detection Type": self.detection_type,
                "State": self.state,
                "Category": self.category,
                "Source Entity ID": self.entity_id,
                "Source Entity Name": self.entity_name,
            },
        )

    def get_subset(self):
        return {
            "ID": self.detection_id,
            "Detection URL": self.detection_url,
            "Detection Type": self.detection_type,
            "Category": self.category,
            "Last Timestamp": self.last_detection_timestamp,
        }


class Assignment(BaseModel):
    """Assignment model to store assignment data"""

    def __init__(
        self,
        raw_data,
        assignment_id,
        assigned_by,
        assigned_to,
        resolved_by,
        outcome,
        host_id,
        account_id,
        note_title,
    ):
        super(Assignment, self).__init__(raw_data)
        self.assignment_id = assignment_id
        self.assigned_by = {} if not assigned_by else assigned_by
        self.assigned_to = {} if not assigned_to else assigned_to
        self.resolved_by = {} if not resolved_by else resolved_by
        self.outcome = {} if not outcome else outcome
        self.host_id = host_id
        self.account_id = account_id
        self.note_title = None if note_title == "" else note_title

    def list_assignment_csv(self):
        result = {
            ASSIGNMENT_ID: self.assignment_id,
            "Assigned User ID": self.assigned_to.get("id"),
            "Assigned User": self.assigned_to.get("username"),
            "Resolved By User ID": self.resolved_by.get("id"),
            "Resolved By User": self.resolved_by.get("username"),
            "Outcome ID": self.outcome.get("id"),
            "Outcome Title": self.outcome.get("title"),
            "Entity ID": self.host_id or self.account_id,
            "Entity Type": "Host" if self.host_id else "Account",
        }

        if self.note_title:
            result["Note Title"] = self.note_title

        return result

    def update_assignment_csv(self, entity_type):
        return {
            ASSIGNMENT_ID: self.assignment_id,
            "Assigned User ID": self.assigned_to.get("id"),
            "Assigned User": self.assigned_to.get("username"),
            "Entity ID": self.host_id or self.account_id,
            "Entity Type": entity_type,
        }

    def create_assignment_csv(self):
        entity = "Host ID" if self.host_id else "Account ID"
        return flat_dict_to_csv(
            {
                ASSIGNMENT_ID: self.assignment_id,
                "User ID": self.assigned_to.get("id"),
                entity: self.host_id or self.account_id,
            },
        )


class User(BaseModel):
    """User model for store user details"""

    def __init__(self, raw_data, user_id, username, role, account_type, last_login):
        """Constructor for User model.

        Args:
            raw_data (dict): The raw JSON object from the API.
            user_id (str): The user ID.
            username (str): The username.
            role (str): The role of the user.
            account_type (str): The type of the account.
            last_login (str): The last time the user logged in.

        """
        super().__init__(raw_data)
        self.user_id = user_id
        self.username = username
        self.role = role
        self.account_type = account_type
        self.last_login = last_login

    def fetch_user_details(self):
        """Fetches the user details.

        Returns:
            dict: A dictionary containing the user details

        """
        return {
            "Last Login": self.last_login,
            "Account Type": self.account_type,
            "Role": self.role,
            "Username": self.username,
            "ID": self.user_id,
        }


class Group(BaseModel):
    """Group model for store group details"""

    def __init__(self, raw_data, group_id, group_name, group_type, description):
        """Constructor for Group class

        Args:
            raw_data (dict): The dict containing the group details
            group_id (str): The id of the group
            group_name (str): The name of the group
            group_type (str): The type of the group
            description (str): The description of the group

        """
        super(Group, self).__init__(raw_data)
        self.group_id = group_id
        self.group_name = group_name
        self.group_type = group_type
        self.description = description

    def fetch_group_details(self):
        """Fetches the details of a group

        Returns:
            dict: A dict containing the group details

        """
        return {
            "Description": self.description,
            "Type": self.group_type,
            "ID": self.group_id,
            "Name": self.group_name,
        }


class Outcome(BaseModel):
    """Outcome model for storing outcome details"""

    def __init__(self, raw_data, outcome_id, builtin, user_selectable, title, category):
        """Constructor for Outcome class

        Args:
            raw_data (dict): The dict containing the outcome details
            outcome_id (str): The id of the outcome
            builtin (bool): Whether the outcome is a built-in outcome
            user_selectable (bool): Whether the outcome is user-selectable
            title (str): The title of the outcome
            category (str): The category of the outcome

        """
        super(Outcome, self).__init__(raw_data)
        self.outcome_id = outcome_id
        self.builtin = builtin
        self.user_selectable = user_selectable
        self.title = title
        self.category = category

    def list_outcome_csv(self):
        """Returns a dict containing the outcome details in CSV format

        Returns:
            dict: A dict containing the outcome details in CSV format

        """
        return {
            "Outcome ID": self.outcome_id,
            "Built In": self.builtin,
            "User Selectable": self.user_selectable,
            "Title": self.title,
            "Category": self.category,
        }


class Note(BaseModel):
    """Note class for storing note details"""

    def __init__(self, raw_data, note_id, date_created, created_by, note):
        """Constructor for Note class

        Args:
            raw_data (dict): The dict containing the note details
            note_id (str): The id of the note
            date_created (str): The date the note was created
            created_by (dict): The user that created the note
            note (str): The note itself

        """
        self.raw_data = raw_data
        self.note_id = note_id
        self.date_created = date_created
        self.created_by = created_by
        self.note = note

    def to_csv(self):
        return flat_dict_to_csv(
            {
                "ID": self.note_id,
                "Note": self.note,
                "Date Created": self.date_created,
                "Created By": self.created_by,
            },
        )


class Entity(BaseModel):
    def __init__(
        self,
        raw_data,
        entity_id,
        name,
        state,
        threat,
        severity,
        last_timestamp,
        detection_set,
        tags,
        assignment,
        display_name,
    ):
        super(Entity, self).__init__(raw_data)
        self.raw_data = raw_data
        self.raw_data["detection_set"] = [
            url.replace(API_VERSION_2_5, "")
            .replace(API_VERSION_2_1, "")
            .replace(API_VERSION_2_2, "")
            for url in detection_set
        ]
        if self.raw_data.get("url"):
            self.raw_data["url"] = (
                self.raw_data["url"]
                .replace(API_VERSION_2_5, "")
                .replace(API_VERSION_2_1, "")
                .replace(API_VERSION_2_2, "")
            )
        if self.raw_data.get("host_url"):
            self.raw_data["host_url"] = (
                self.raw_data["host_url"]
                .replace(API_VERSION_2_5, "")
                .replace(API_VERSION_2_1, "")
                .replace(API_VERSION_2_2, "")
            )
        for detection in self.raw_data.get("detection_summaries", []):
            if detection.get("detection_url"):
                detection["detection_url"] = (
                    detection["detection_url"]
                    .replace(API_VERSION_2_5, "")
                    .replace(API_VERSION_2_1, "")
                    .replace(API_VERSION_2_2, "")
                )
        self.id = entity_id
        self.name = name
        self.state = state
        self.threat = threat
        self.severity = severity
        self.last_timestamp = last_timestamp
        self.assignment = assignment
        self.display_name = display_name
        if "ip" in raw_data:
            self.ip = raw_data.get("ip")
        self.detection_ids = [url.split("/")[-1] for url in detection_set]
        self.detection_set = " | ".join([url.split("/")[-1] for url in detection_set])
        self.tags = f"{' '.join([tag for tag in tags])}"
        self.uuid = str(uuid.uuid4())

    def to_csv(self):
        data = {
            "ID": self.id,
            "Name": self.name,
            "State": self.state,
            "Threat score": self.threat,
            "Tags": self.tags,
            "Detection Set": self.detection_set,
        }

        if hasattr(self, "ip"):
            data["IP"] = self.ip

        return flat_dict_to_csv(data)

    def get_alert_info(
        self,
        alert_info,
        detections,
        entity_type,
        environment_common,
        device_product_field,
    ):
        name = self.display_name or self.name
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = get_alert_id(self.id, self.last_timestamp, entity_type)
        alert_info.display_id = get_alert_id(self.id, self.last_timestamp, entity_type)
        alert_info.name = name
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = f"{RULE_GENERATOR}: {name}"
        alert_info.source_grouping_identifier = f"{entity_type}#{self.id}"
        alert_info.start_time = convert_string_to_unix_time(self.last_timestamp)
        alert_info.end_time = convert_string_to_unix_time(self.last_timestamp)
        alert_info.events = [
            dict_to_flat(self.create_event(detection.raw_data))
            for detection in detections
        ]
        alert_info.extensions = dict_to_flat(self.get_extensions(entity_type))
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEFAULT_DEVICE_PRODUCT
        )

        return alert_info

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.severity.lower(), -1)

    @staticmethod
    def create_event(detection):
        detection["name"] = detection["detection"]
        detection["StartTime"] = convert_string_to_unix_time(
            detection["first_timestamp"],
        )
        detection["EndTime"] = convert_string_to_unix_time(detection["last_timestamp"])
        detection["device_product"] = DEFAULT_DEVICE_PRODUCT

        return detection

    def get_extensions(self, entity_type):
        data = copy.deepcopy(self.raw_data)
        data["entity_type"] = entity_type
        data.pop("detection_summaries", None)

        return data
