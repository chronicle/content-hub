# ============================================================================#
# title           :AWSCloudWatchManager.py
# description     :This Module contain all AWS CloudWatch operations functionality
# author          :amit.levizky@siemplify.co
# date            :01-03-2021
# python_version  :3.7
# libraries       :boto3
# requirements    :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import boto3
import botocore
from . import consts

from .exceptions import (
    AWSCloudWatchStatusCodeException,
    AWSCloudWatchResourceNotFoundException,
    AWSCloudWatchLogGroupNotFoundException,
    AWSCloudWatchLogStreamNotFoundException,
)
from .AWSCloudWatchParser import AWSCloudWatchParser
from .datamodels import LogGroup, LogStream, LogEvent
from .utils import remove_empty_kwargs

from typing import List


class AWSCloudWatchManager:
    """
    AWS CloudWatch Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(
        self, aws_access_key, aws_secret_key, aws_default_region, verify_ssl=False
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.client = session.client(
            "logs",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AWSCloudWatchParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate Cloud Watch response status code
        :param error_msg: {str} Error message to display in case of an error
        :param response: Cloud Watch response
        :return: raise AWSCloudWatchStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSCloudWatchManager.VALID_STATUS_CODES
        ):
            raise AWSCloudWatchStatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with AWS CloudWatch service
        :return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSCloudWatchStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.describe_log_groups(limit=1)
        self.validate_response(
            response,
            error_msg="Failed to test connectivity with AWS CloudWatch Service.",
        )

    def list_log_groups(self, max_groups_to_return: int = None) -> List[LogGroup]:
        """
        List available log groups in AWS CloudWatch.
        :param max_groups_to_return: {int} Max Log Groups to return
        :return: {List[LogGroup]}} Log Groups data models
        """
        paginator = self.client.get_paginator("describe_log_groups")
        page_iterator = paginator.paginate(
            PaginationConfig={
                "MaxItems": (
                    min(max_groups_to_return, consts.DEFAULT_MAX_RESULTS)
                    if max_groups_to_return is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            }
        )

        log_groups_list = []

        for page in page_iterator:
            if (
                max_groups_to_return is not None
                and len(log_groups_list) >= max_groups_to_return
            ):
                break

            self.validate_response(page, error_msg="Failed to get log groups page.")
            log_groups_list.extend(page.get("logGroups", []))

        if max_groups_to_return:
            return self.parser.build_log_group_objs(
                log_groups_list[:max_groups_to_return]
            )
        return self.parser.build_log_group_objs(log_groups_list)

    def list_log_streams(
        self,
        log_group_name: str,
        order_by: str = None,
        sort_order: str = None,
        max_streams_to_return: int = None,
    ) -> List[LogStream]:
        """
        List available log streams in AWS CloudWatch.
        :param log_group_name: {str} group name for which you want to retrieve log streams.
        :param order_by: {str} Specify how the log streams should be ordered.
        :param sort_order: {str} Specify the sort order for the log streams.
        :param max_streams_to_return: {int} Max Log Groups to return
        :return: {List[LogStream]}} Log Streams data models
        """
        paginator = self.client.get_paginator("describe_log_streams")
        page_iterator = paginator.paginate(
            logGroupName=log_group_name,
            orderBy=order_by,
            descending=sort_order,
            PaginationConfig={
                "MaxItems": (
                    min(max_streams_to_return, consts.DEFAULT_MAX_RESULTS)
                    if max_streams_to_return is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            },
        )

        log_streams_list = []

        try:
            for page in page_iterator:
                if (
                    max_streams_to_return is not None
                    and len(log_streams_list) >= max_streams_to_return
                ):
                    break

                self.validate_response(
                    page, error_msg="Failed to get log streams page."
                )
                log_streams_list.extend(page.get("logStreams", []))

            if max_streams_to_return:
                return self.parser.build_log_stream_objs(
                    log_streams_list[:max_streams_to_return]
                )
            return self.parser.build_log_stream_objs(log_streams_list)

        except botocore.errorfactory.ClientError as error:
            if (
                error.response.get("Error", {}).get("Code")
                == "ResourceNotFoundException"
            ):
                raise AWSCloudWatchResourceNotFoundException(
                    f"Unable to find log group with name {log_group_name}"
                ) from error
            raise error

    def create_log_group(self, log_group_name: str):
        """
        Create a log group in AWS CloudWatch.
        :param log_group_name: {str}  Name of the new log group.
        :return: True if log group was created
        """
        response = self.client.create_log_group(logGroupName=log_group_name)
        self.validate_response(response, "Unable to create new log group")

    def create_log_stream(self, log_group_name: str, log_stream_name: str):
        """
        Create a log stream for the log group in AWS CloudWatch.
        :param log_group_name: {str} Specify the name of the log group, where you want to create a log stream.
        :param log_stream_name: {str} Specify the name for the new log group.
        :return: True if log stream was created
        """
        response = self.client.create_log_stream(
            logGroupName=log_group_name, logStreamName=log_stream_name
        )
        self.validate_response(
            response, "Unable to create new log stream for the specified log group"
        )

    def delete_log_group(self, log_group_name: str):
        """
        Delete a log group in AWS CloudWatch.
        :param log_group_name: {str}  Name of the log group that needs to be deleted.
        :return: raise AWSGuardDutyResourceNotFoundException if the log group name not found in AWS CloudWatch
        """
        try:
            response = self.client.delete_log_group(logGroupName=log_group_name)
            self.validate_response(
                response, f"Unable to delete {log_group_name} log group"
            )

        except botocore.errorfactory.ClientError as error:
            if (
                error.response.get("Error", {}).get("Code")
                == "ResourceNotFoundException"
            ):
                raise AWSCloudWatchResourceNotFoundException(
                    f"Unable to find log group with name {log_group_name}"
                ) from error
            raise error

    def delete_log_stream(self, log_group_name: str, log_stream_name: str):
        """
        Delete a log stream in a log group in AWS CloudWatch.
        :param log_group_name: {str} Name of the log group that contains the log stream.
        :param log_stream_name: {str} Name of the log stream that needs to be deleted.
        :return: raise AWSGuardDutyResourceNotFoundException if the log group or log stream name not found in AWS CloudWatch
        """
        try:
            response = self.client.delete_log_stream(
                logGroupName=log_group_name, logStreamName=log_stream_name
            )
            self.validate_response(
                response,
                f"Unable to delete {log_stream_name} log stream from {log_group_name}",
            )

        except botocore.errorfactory.ClientError as error:
            if (
                error.response.get("Error", {}).get("Code")
                == "ResourceNotFoundException"
            ):
                if "log group" in error.response.get("Error", {}).get("Message"):
                    raise AWSCloudWatchLogGroupNotFoundException(
                        f"Unable to find log group with name {log_group_name}"
                    ) from error
                if "log stream" in error.response.get("Error", {}).get("Message"):
                    raise AWSCloudWatchLogStreamNotFoundException(
                        f"Unable to find log stream with name {log_stream_name}"
                    ) from error
            raise error

    def search_log_events(
        self,
        log_group: str,
        log_streams: List[str],
        start_time: int,
        end_time: int,
        custom_filter: str = None,
        max_events_to_return: int = None,
    ) -> List[LogEvent]:
        """
        Search log events in AWS CloudWatch.
        :param log_group: {str} Specify the name of the log group, where you want to search for events.
        :param log_streams: {List[str]} Specify a comma-separated list of log streams, where you want to search
         for events.
        :param start_time: {int} Specify the start time for the search.  Format: timestamp in milliseconds
        :param end_time: {int} Specify the end time for the search.  Format: timestamp in milliseconds,
        default is current time
        :param custom_filter: {str} Specify the custom filter for the search. For additional information please refer
        to the documentation portal.
        :param max_events_to_return: {int} Specify how many events to return.
        :return: {List[LogEvent]}} Log Events data models
        """
        paginator = self.client.get_paginator("filter_log_events")

        pagination_config = {
            "MaxItems": (
                min(max_events_to_return, consts.DEFAULT_MAX_RESULTS)
                if max_events_to_return is not None
                else None
            ),
            "PageSize": consts.PAGE_SIZE,
        }

        kwargs = {
            "logGroupName": log_group,
            "logStreamNames": log_streams,
            "startTime": start_time,
            "endTime": end_time,
            "filterPattern": custom_filter,
            "PaginationConfig": pagination_config,
        }

        page_iterator = paginator.paginate(**remove_empty_kwargs(**kwargs))

        log_events = []
        for page in page_iterator:
            if (
                max_events_to_return is not None
                and len(log_events) >= max_events_to_return
            ):
                break

            self.validate_response(
                page, "Failed to fetch log events from AWS CloudWatch service."
            )
            log_events.extend(self.parser.build_log_event_objs(page))

        return log_events[:max_events_to_return] if max_events_to_return else log_events

    def remove_retention_policy(self, log_group_name: str):
        """
        Remove the retention policy from the log group in AWS CloudWatch.
        :param log_group_name: {str} Specify the name of the log group from which you want to remove the retention
        policy.
        """
        response = self.client.delete_retention_policy(logGroupName=log_group_name)
        self.validate_response(
            response, "Failed to delete retention policy from AWS CloudWatch service"
        )

    def set_retention_policy(self, log_group_name: str, retention_in_days: int):
        """
        Set the retention policy for log groups in AWS CloudWatch.
        :param log_group_name: {str} Name of the log group for which you want to set the retention policy.
        :param retention_in_days: {int} The days the data should be retained in the log group.
        """
        response = self.client.put_retention_policy(
            logGroupName=log_group_name, retentionInDays=retention_in_days
        )
        self.validate_response(
            response,
            "Failed to set retention policy for log groups AWS CloudWatch service",
        )
