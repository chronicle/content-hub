from __future__ import annotations
import json

from .datamodels import InsightEvent


class AWSCloudTrailParser:
    """
    AWS Cloud Trail Transformation Layer.
    """

    @staticmethod
    def build_insight_event_obj(raw_data):
        try:
            cloud_trail_event = json.loads(raw_data.get("CloudTrailEvent"))
        except:
            cloud_trail_event = raw_data.get("CloudTrailEvent")

        return InsightEvent(
            raw_data=raw_data,
            event_id=raw_data.get("EventId"),
            event_name=raw_data.get("EventName"),
            event_time=raw_data.get("EventTime"),
            event_source=raw_data.get("EventSource"),
            username=raw_data.get("Username"),
            cloud_trail_event=cloud_trail_event,
        )
