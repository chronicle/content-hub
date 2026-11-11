from __future__ import annotations

from TIPCommon.types import SingleJson
from mandiant_managed_defense.core import datamodels


def build_base_object(raw_data: SingleJson) -> datamodels.BaseObject:
    """Build BaseObject from JSON data

    Args:
        raw_data (SingleJson): raw JSON data

    Returns:
        datamodels.BaseObject: BaseObject
    """
    return datamodels.BaseObject.from_json(raw_data=raw_data)


def build_alert_objects(raw_data: dict) -> list[datamodels.Alert]:
    """Build list of Alert dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        list[datamodels.Alert]: list of Alert dataclasses
    """
    return [
        datamodels.Alert.from_json(raw_data=item)
        for item in raw_data.get("data", {}).get("objects", [])
    ]


def build_event_objects(raw_data: dict) -> list[datamodels.Event]:
    """Build list of Event dataclasses

    Args:
        raw_data: {dict} raw data dict

    Returns:
        list[datamodels.Event]: list of Event dataclasses
    """
    return [
        datamodels.Event.from_json(raw_data=item)
        for item in raw_data.get("data", {}).get("objects", [])
    ]
