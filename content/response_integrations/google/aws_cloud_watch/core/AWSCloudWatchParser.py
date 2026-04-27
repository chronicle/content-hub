from __future__ import annotations
from .datamodels import LogGroup, LogStream, LogEvent
from typing import List, Dict


class AWSCloudWatchParser:
    """
    AWS CloudWatch Transformation Layer.
    """

    @staticmethod
    def build_log_group_objs(log_groups_list: List[Dict]) -> List[LogGroup]:
        """
        Return list of LogGroup objects
        :param log_groups_list: {List[Dict]} raw data of log_groups
        :return: [datamodels.LogGroup] objects
        """
        return (
            [
                AWSCloudWatchParser.build_log_group_obj(log_group)
                for log_group in log_groups_list
            ]
            if log_groups_list
            else []
        )

    @staticmethod
    def build_log_group_obj(log_group: Dict) -> LogGroup:
        """
        Return LogGroup data model object
        :param log_group: {Dict} raw data of log group from AWS CloudWatch
        :return: {LogGroup} LogGroup data model object
        """
        return LogGroup(
            raw_data=log_group,
            log_group_name=log_group.get("logGroupName", ""),
            creation_time=log_group.get("creationTime", ""),
            retention_in_days=log_group.get("retentionInDays", ""),
            metric_filter_count=log_group.get("metricFilterCount", ""),
            arn=log_group.get("arn", ""),
            stored_bytes=log_group.get("storedBytes", ""),
            kms_key_id=log_group.get("kmsKeyId", ""),
        )

    @staticmethod
    def build_log_stream_objs(log_streams_list: List[Dict]) -> List[LogStream]:
        """
        Return list of LogGroup objects
        :param log_streams_list: {List[Dict]} raw data of log streams
        :return: [datamodels.LogStream] objects
        """
        return (
            [
                AWSCloudWatchParser.build_log_stream_obj(log_stream)
                for log_stream in log_streams_list
            ]
            if log_streams_list
            else []
        )

    @staticmethod
    def build_log_stream_obj(log_stream: Dict) -> LogStream:
        """
        Return LogStream data model object
        :param log_stream: {Dict} raw data of log stream from AWS CloudWatch
        :return: {LogStream} LogStream data model object
        """
        return LogStream(
            raw_data=log_stream,
            log_stream_name=log_stream.get("logStreamName", ""),
            creation_time=log_stream.get("creationTime", ""),
            first_event_timestamp=log_stream.get("firstEventTimestamp", ""),
            last_event_timestamp=log_stream.get("lastEventTimestamp", ""),
            last_ingestion_time=log_stream.get("lastIngestionTime", ""),
            upload_sequence_token=log_stream.get("uploadSequenceToken", ""),
            arn=log_stream.get("arn", ""),
            stored_bytes=log_stream.get("storedBytes", ""),
        )

    @staticmethod
    def build_log_event_objs(log_events: Dict) -> List[LogEvent]:
        log_events_dicts = log_events.get("events", [])
        return (
            [
                AWSCloudWatchParser.build_log_event_obj(log_event)
                for log_event in log_events_dicts
            ]
            if log_events_dicts
            else []
        )

    @staticmethod
    def build_log_event_obj(log_event: Dict) -> LogEvent:
        return LogEvent(
            raw_data=log_event,
            log_stream_name=log_event.get("logStreamName", ""),
            timestamp=log_event.get("timestamp", ""),
            message=log_event.get("message", ""),
            ingestion_time=log_event.get("ingestionTime", ""),
            event_id=log_event.get("eventId", ""),
        )
