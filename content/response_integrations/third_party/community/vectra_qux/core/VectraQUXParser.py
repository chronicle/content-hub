from __future__ import annotations

from .datamodels import Assignment, Detection, Entity, Group, Note, Outcome, User


class VectraQUXParser:
    def __init__(self):
        """Initializes the object."""

    def build_detection_object(self, detection_json):
        """Builds a Detection object from a JSON object
        representing a detection.

        Args:
            detection_json (dict): A JSON object representing a detection.

        Returns:
            Detection: A Detection object representing the detection.

        """
        return Detection(detection_json)

    def build_entity_object(self, data, entity_type):
        """Builds an entity object based on the given json and type.

        Args:
            data (dict): The json dictionary of the entity
            entity_type: Type of entity

        Returns:
            Account or Host: The entity object.

        """
        return Entity(
            raw_data=data,
            entity_id=data.get("id"),
            name=data.get("name"),
            state=data.get("state"),
            threat=data.get("threat"),
            severity=data.get("severity"),
            last_timestamp=(
                data.get("last_detection_timestamp")
                if entity_type == "account"
                else data.get("last_modified")
            ),
            detection_set=data.get("detection_set", []),
            tags=data.get("tags", []),
            assignment=data.get("assignment", {}),
            display_name=data.get("display_name"),
        )

    def build_assignment_object(self, assignment_json, note_title=""):
        """Builds an Assignment object from a JSON object
        representing a assignment.

        Args:
            assignment_json (dict): A JSON object representing a assignment.
            note_title (str): The title of the note. Defaults to " ".

        Returns:
            Assignment: A Assignment object representing the assignment.

        """
        return Assignment(
            raw_data=assignment_json,
            assignment_id=assignment_json.get("id"),
            assigned_by=assignment_json.get("assigned_by", {}),
            assigned_to=assignment_json.get("assigned_to", {}),
            resolved_by=assignment_json.get("resolved_by", {}),
            outcome=assignment_json.get("outcome", {}),
            host_id=assignment_json.get("host_id"),
            account_id=assignment_json.get("account_id"),
            note_title=note_title,
        )

    def build_user_object(self, user_obj):
        """Builds a User object from a dictionary of user data.

        Args:
            user_obj (dict): Dictionary containing user data.

        Returns:
            User: A User object.

        """
        return User(
            raw_data=user_obj,
            user_id=user_obj.get("id"),
            username=user_obj.get("username"),
            role=user_obj.get("role"),
            account_type=user_obj.get("account_type"),
            last_login=user_obj.get("last_login"),
        )

    def build_group_object(self, group_obj):
        """Builds a Group object from the given group_obj.

        Args:
            group_obj (dict): A dictionary representing a group from the VectraQUX API.

        Returns:
            Group: A Group object created from the given group_obj.

        """
        return Group(
            raw_data=group_obj,
            group_id=group_obj.get("id"),
            group_name=group_obj.get("name"),
            group_type=group_obj.get("type"),
            description=group_obj.get("description"),
        )

    def build_outcome_object(self, outcome_json):
        """Builds an Outcome object from a JSON object representing a outcome.

        Args:
            outcome_json (dict): A JSON object representing a outcome.

        Returns:
            Outcome: An Outcome object representing the outcome.

        """
        return Outcome(
            raw_data=outcome_json,
            outcome_id=outcome_json.get("id"),
            builtin=outcome_json.get("builtin"),
            user_selectable=outcome_json.get("user_selectable"),
            title=outcome_json.get("title"),
            category=outcome_json.get("category"),
        )

    def build_note_object(self, entity_json):
        """Builds a note object based on the given json and type.

        Args:
            entity_json (dict): The json dictionary of the note.

        Returns:
            Note: The note object.

        """
        return Note(
            raw_data=entity_json,
            note_id=entity_json.get("id"),
            date_created=entity_json.get("date_created"),
            created_by=entity_json.get("created_by"),
            note=entity_json.get("note"),
        )
