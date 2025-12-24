from __future__ import annotations

from .datamodels import Assignment, Detection, Entity, Group, Note, Outcome, User


class VectraRUXParser:
    def __init__(self):
        """Initializes the object."""

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
            account_id=assignment_json.get("account_id"),
            host_id=assignment_json.get("host_id"),
            note_title=note_title,
        )

    def build_detection_object(self, detection_json):
        """Builds a Detection object from a JSON object
        representing a detection.

        Args:
            detection_json (dict): A JSON object representing a detection.

        Returns:
            Detection: A Detection object representing the detection.

        """
        return Detection(
            raw_data=detection_json,
            detection_id=detection_json.get("id"),
            state=detection_json.get("state"),
            category=detection_json.get("detection_category"),
            detection_type=detection_json.get("detection_type"),
            threat=detection_json.get("threat"),
            last_detection_timestamp=detection_json.get("last_timestamp"),
            detection_url=detection_json.get("detection_url", ""),
        )

    def build_entity_object(self, entity_json):
        """Builds an entity object based on the given json and type.

        Args:
            entity_json (dict): The json dictionary of the entity.

        Returns:
            Account or Host: The entity object.

        """
        return Entity(
            raw_data=entity_json,
            entity_id=entity_json.get("id"),
            name=entity_json.get("name"),
            entity_type=entity_json.get("type"),
            state=entity_json.get("state"),
            severity=entity_json.get("severity"),
            last_detection_timestamp=entity_json.get("last_detection_timestamp"),
            last_modified_timestamp=entity_json.get("last_modified_timestamp"),
            urgency_score=entity_json.get("urgency_score"),
            attack_rating=entity_json.get("attack_rating"),
            ip=entity_json.get("ip"),
            importance=entity_json.get("importance"),
            tags=entity_json.get("tags"),
            detection_ids=entity_json.get("detection_set"),
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
            email=user_obj.get("email"),
            name=user_obj.get("name"),
            role=user_obj.get("role"),
            last_login_timestamp=user_obj.get("last_login_timestamp"),
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

    def build_group_object(self, group_obj):
        """Builds a Group object from a dictionary of group data.

        Args:
            group_obj (dict): Dictionary containing group data.

        Returns:
            Group: A Group object.

        """
        return Group(
            raw_data=group_obj,
            group_id=group_obj.get("id"),
            group_name=group_obj.get("name"),
            group_type=group_obj.get("type"),
            description=group_obj.get("description"),
            importance=group_obj.get("importance"),
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
