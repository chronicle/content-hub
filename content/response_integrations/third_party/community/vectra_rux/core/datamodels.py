from __future__ import annotations

import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import add_prefix_to_dict, dict_to_flat, flat_dict_to_csv

from .constants import (
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    RULE_GENERATOR,
    SEVERITY_MAP,
    URL_API_VERSION,
)
from .UtilsManager import get_alert_id

ASSIGNMENT_ID = "Assignment ID"


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


class Assignment(BaseModel):
    def __init__(
        self,
        raw_data,
        assignment_id,
        assigned_by,
        assigned_to,
        resolved_by,
        outcome,
        account_id,
        host_id,
        note_title,
    ):
        super(Assignment, self).__init__(raw_data)
        self.assignment_id = assignment_id
        self.assigned_by = {} if not assigned_by else assigned_by
        self.assigned_to = {} if not assigned_to else assigned_to
        self.resolved_by = {} if not resolved_by else resolved_by
        self.outcome = {} if not outcome else outcome
        self.account_id = account_id
        self.host_id = host_id
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
        }

        if self.account_id:
            result["Account ID"] = self.account_id
        else:
            result["Host ID"] = self.host_id

        if self.note_title:
            result["Note Title"] = self.note_title

        return result

    def update_assignment_csv(self, entity_type):
        return {
            ASSIGNMENT_ID: self.assignment_id,
            "Assigned User ID": self.assigned_to.get("id"),
            "Assigned User": self.assigned_to.get("username"),
            "Entity Type": entity_type,
            "Entity ID": self.host_id or self.account_id,
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


class Detection(BaseModel):
    def __init__(
        self,
        raw_data,
        detection_id,
        state,
        category,
        detection_type,
        threat,
        last_detection_timestamp,
        detection_url,
    ):
        """Constructor for Detection class

        Args:
            raw_data (dict): The raw JSON response from the API
            detection_id (str): The ID of the detection
            state (str): The state of the detection
            category (str): The category of the detection
            detection_type (str): The type of the detection
            threat (str): The threat of the detection
            last_detection_timestamp (str): The timestamp of the last detection
            detection_url (str): The URL of the detection

        """
        raw_data["detection_url"] = raw_data.get("detection_url", "").replace(
            URL_API_VERSION,
            "",
        )
        raw_data["url"] = raw_data.get("url", "").replace(URL_API_VERSION, "")
        self.raw_data = raw_data
        self.detection_id = detection_id
        self.state = state
        self.category = category
        self.detection_type = detection_type
        self.threat = threat
        self.last_detection_timestamp = last_detection_timestamp
        self.entity_id = None
        self.entity_name = None
        self.detection_url = detection_url.replace(URL_API_VERSION, "")

        if raw_data["src_account"]:
            self.entity_id = raw_data["src_account"]["id"]
            self.entity_name = raw_data["src_account"]["name"]
            self.raw_data["src_account"]["url"] = raw_data["src_account"][
                "url"
            ].replace(URL_API_VERSION, "")
        elif raw_data["src_host"]:
            self.entity_id = raw_data["src_host"]["id"]
            self.entity_name = raw_data["src_host"]["name"]
            self.raw_data["src_host"]["url"] = raw_data["src_host"]["url"].replace(
                URL_API_VERSION,
                "",
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


class Entity(BaseModel):
    def __init__(
        self,
        raw_data,
        entity_id,
        name,
        entity_type,
        state,
        severity,
        last_detection_timestamp,
        last_modified_timestamp,
        urgency_score,
        attack_rating,
        ip,
        importance,
        tags,
        detection_ids,
    ):
        """Constructor for Entity class

        Args:
            raw_data (dict): The raw JSON response from the API
            entity_id (str): The ID of the entity
            name (str): The name of the entity
            entity_type (str): The type of the entity
            state (str): The state of the entity
            severity (str): The severity of the entity
            last_detection_timestamp (str): The timestamp of the last detection
            last_modified_timestamp (str): The timestamp of the last modification
            urgency_score (int): The urgency score of the entity
            attack_rating (int): The attack rating of the entity
            ip (str): The IP of the entity
            importance (str): The importance of the entity
            tags (list): The tags of the entity
            detection_ids (list): The IDs of the detections related to the entity

        """
        super().__init__(raw_data)
        raw_data["detection_set"] = [
            url.replace(URL_API_VERSION, "")
            for url in raw_data.get("detection_set", "")
        ]
        raw_data["url"] = raw_data.get("url", "").replace(URL_API_VERSION, "")
        self.raw_data = raw_data
        self.name = name
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.state = state
        self.severity = severity
        self.last_detection_timestamp = last_detection_timestamp
        self.last_modified_timestamp = last_modified_timestamp
        self.urgency_score = urgency_score
        self.attack_rating = attack_rating
        self.ip = ip
        self.importance = importance
        self.tags = " | ".join(tags)
        self.detection_ids = [url.split("/")[-1] for url in detection_ids]
        self.uuid = str(uuid.uuid4())

    def to_csv(self):
        """Creates a CSV representation of the entity for table view.
        :return: a string representing the entity in CSV format
        """
        table_view_data = {
            "ID": self.entity_id,
            "Name": self.name,
            "State": self.state,
            "Urgency Score": self.urgency_score,
            "Importance": self.importance,
            "Tags": self.tags,
            "Detection Set": "   |   ".join(self.detection_ids),
        }

        if self.ip:
            table_view_data["IP"] = self.ip

        return flat_dict_to_csv(table_view_data)

    def get_alert_info(
        self,
        alert_info,
        detections,
        entity_type,
        environment_common,
        device_product_field,
    ):
        self.raw_data["entity_type"] = entity_type
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = get_alert_id(
            self.entity_id,
            self.last_modified_timestamp,
            entity_type,
        )
        alert_info.display_id = get_alert_id(
            self.entity_id,
            self.last_modified_timestamp,
            entity_type,
        )
        alert_info.name = self.name
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = f"{RULE_GENERATOR}: {self.name}"
        alert_info.source_grouping_identifier = f"{entity_type}#{self.entity_id}"
        alert_info.start_time = convert_string_to_unix_time(
            self.last_modified_timestamp,
        )
        alert_info.end_time = convert_string_to_unix_time(self.last_modified_timestamp)
        alert_info.events = [
            dict_to_flat(self.create_event(detection.raw_data))
            for detection in detections
        ]
        alert_info.extensions = dict_to_flat(self.raw_data)
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


class User(BaseModel):
    """User model for store user details"""

    def __init__(self, raw_data, user_id, email, name, role, last_login_timestamp):
        """Constructor for User class

        Args:
            raw_data (dict): The dict containing the user details
            user_id (str): The id of the user
            email (str): The email of the user
            name (str): The name of the user
            role (str): The role of the user
            last_login_timestamp (str): The last login timestamp of the user

        """
        super().__init__(raw_data)
        self.user_id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.last_login_timestamp = last_login_timestamp

    def fetch_user_details(self):
        """Fetches the user details.

        Returns:
            dict: A dictionary containing the user details

        """
        return {
            "Last Login": self.last_login_timestamp,
            "Role": self.role,
            "Email": self.email,
            "Name": self.name,
            "ID": self.user_id,
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


class Group(BaseModel):
    """Group model for store group details"""

    def __init__(
        self,
        raw_data,
        group_id,
        group_name,
        group_type,
        description,
        importance,
    ):
        """Constructor for Group class

        Args:
            raw_data (dict): The dict containing the group details
            group_id (str): The id of the group
            group_name (str): The name of the group
            group_type (str): The type of the group
            description (str): The description of the group
            importance (str): The importance of the group

        """
        super(Group, self).__init__(raw_data)
        self.group_id = group_id
        self.group_name = group_name
        self.group_type = group_type
        self.description = description
        self.importance = importance

    def fetch_group_details(self):
        """Fetches the details of a group

        Returns:
            dict: A dict containing the group details

        """
        return {
            "Description": self.description,
            "Importance": self.importance,
            "Type": self.group_type,
            "ID": self.group_id,
            "Name": self.group_name,
        }


class Note(BaseModel):
    """Constructor for Outcome class

    Args:
        raw_data (dict): The dict containing the outcome details
        note_id (str): A unique identifier for the note.
        date_created (bool): Indicates the creation date of the note.
        created_by (bool): the creator of the note.
        note (str): The textual content or description of the note.
        entity_type (str): The type or category of the entity associated with the note.

    """

    def __init__(self, raw_data, note_id, date_created, created_by, note):
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
