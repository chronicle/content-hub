from __future__ import annotations

from TIPCommon.types import SingleJson

from google_cloud_policy_intelligence.core.datamodels import Activity


def build_activity_objects(raw_json: SingleJson) -> list[Activity]:
    """Builds multiple activity objects

    Args:
        raw_json: Raw json from the response having information
        for multiple activities

    Returns:
        A list of activity objects
    """
    activities = raw_json.get("activities", [])
    return [build_activity_object(activity) for activity in activities]


def build_activity_object(raw_data: SingleJson) -> Activity:
    """Builds a single activity object

    Args:
        raw_data: A dict object for a single activity
    Returns:
        Activity object
    """
    return Activity(raw_data=raw_data, resource_name=raw_data["fullResourceName"])
