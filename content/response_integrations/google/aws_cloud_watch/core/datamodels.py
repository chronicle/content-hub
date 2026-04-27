from __future__ import annotations
from .utils import from_timestamp_to_iso_8601


class LogGroup:
    """
    LogGroup data model.
    """

    def __init__(
        self,
        raw_data,
        log_group_name: str = None,
        creation_time: int = None,
        retention_in_days: int = None,
        metric_filter_count: int = None,
        arn: str = None,
        stored_bytes: int = None,
        kms_key_id: str = None,
    ):
        self.raw_data = raw_data
        self.log_group_name = log_group_name
        self.creation_time = creation_time
        self.retention_in_days = retention_in_days
        self.metric_filter_count = metric_filter_count
        self.arn = arn
        self.stored_bytes = stored_bytes
        self.kms_key_id = kms_key_id

    def as_json(self):
        return {
            "arn": self.arn,
            "creationTime": from_timestamp_to_iso_8601(self.creation_time) or "",
            "logGroupName": self.log_group_name,
            "metricFilterCount": self.metric_filter_count,
            "storedBytes": self.stored_bytes,
        }

    def as_csv(self):
        return {
            "Name": self.log_group_name,
            "Metric Filter Count": self.metric_filter_count,
            "Stored Bytes": self.stored_bytes,
            "Creation Time": from_timestamp_to_iso_8601(self.creation_time) or "",
        }


class LogStream:
    def __init__(
        self,
        raw_data,
        log_stream_name: str = None,
        creation_time: int = None,
        first_event_timestamp: int = None,
        last_event_timestamp: int = None,
        last_ingestion_time: int = None,
        upload_sequence_token: str = None,
        arn: str = None,
        stored_bytes: int = None,
    ):
        self.raw_data = raw_data
        self.log_stream_name = log_stream_name
        self.creation_time = creation_time
        self.first_event_timestamp = first_event_timestamp
        self.last_event_timestamp = last_event_timestamp
        self.last_ingestion_time = last_ingestion_time
        self.stored_bytes = stored_bytes
        self.upload_sequence_token = upload_sequence_token
        self.arn = arn

    def as_json(self):
        return {
            "arn": self.arn,
            "creationTime": (
                from_timestamp_to_iso_8601(self.creation_time)
                if self.creation_time
                else ""
            ),
            "firstEventTimestamp": (
                from_timestamp_to_iso_8601(self.first_event_timestamp)
                if self.first_event_timestamp
                else ""
            ),
            "lastEventTimestamp": (
                from_timestamp_to_iso_8601(self.last_event_timestamp)
                if self.last_event_timestamp
                else ""
            ),
            "lastIngestionTime": (
                from_timestamp_to_iso_8601(self.last_ingestion_time)
                if self.last_ingestion_time
                else ""
            ),
            "logStreamName": self.log_stream_name or "",
            "storedBytes": self.stored_bytes or "",
            "uploadSequenceToken": self.upload_sequence_token or "",
        }

    def as_csv(self):
        return {
            "Name": self.log_stream_name,
            "Stored Bytes": self.stored_bytes,
            "Creation Time": (
                from_timestamp_to_iso_8601(self.creation_time)
                if self.creation_time
                else ""
            ),
            "Last Event Timestamp": (
                from_timestamp_to_iso_8601(self.last_event_timestamp)
                if self.last_event_timestamp
                else ""
            ),
        }


class LogEvent:
    def __init__(
        self,
        raw_data,
        log_stream_name: str = None,
        timestamp: int = None,
        message: str = None,
        ingestion_time: int = None,
        event_id: str = None,
    ):
        self.raw_data = raw_data
        self.log_stream_name = log_stream_name
        self.timestamp = timestamp
        self.message = message
        self.ingestion_time = ingestion_time
        self.event_id = event_id

    def as_json(self):
        return {
            "eventId": self.event_id,
            "ingestionTime": from_timestamp_to_iso_8601(self.ingestion_time) or "",
            "logStreamName": self.log_stream_name,
            "message": self.message,
            "timestamp": from_timestamp_to_iso_8601(self.timestamp) or "",
        }

    def as_csv(self):
        return self.as_json()
