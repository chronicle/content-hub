# ============================================================================#
# title           :AWSCloudTrail.py
# description     :This Module contain all AWS Cloud Trail operations functionality
# author          :gabriel.munits@siemplify.co
# date            :23-02-2020
# python_version  :3.7
# libraries       :boto3
# product_version :1.0
# ============================================================================#

from __future__ import annotations
import datetime
from typing import List, Optional

# ============================= IMPORTS ===================================== #
import boto3

from TIPCommon import filter_old_alerts

from .AWSCloudTrailParser import AWSCloudTrailParser
from .consts import INTEGRATION_DISPLAY_NAME, PAGE_SIZE
from .datamodels import InsightEvent
from .exceptions import AWSCloudTrailStatusCodeException
from .consts import INSIGHT_ID_FIELD


class AWSCloudTrailManager:
    """
    AWS Cloud Trail Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(
        self,
        aws_access_key,
        aws_secret_key,
        aws_default_region,
        verify_ssl=False,
        siemplify=None,
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.client = session.client(
            "cloudtrail",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AWSCloudTrailParser()
        self.siemplify = siemplify

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client Cloud Trail response status code
        :param response: client Cloud Trail response
        :param error_msg: {str} Error message
        :return: raise AWSCloudTrailStatusCodeException if failed to validate response
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSCloudTrailManager.VALID_STATUS_CODES
        ):
            raise AWSCloudTrailStatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with AWS Cloud Trail
        :return:
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSCloudTrailStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.lookup_events(
            StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            EndTime=datetime.datetime.utcnow(),
            EventCategory="insight",
            MaxResults=1,
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to test connectivity with {INTEGRATION_DISPLAY_NAME} Service."
            ),
        )

    def get_events(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        last_success_time: datetime.datetime,
        existing_ids: List[str],
        limit: int,
        event_category: Optional[str] = "insight",
    ) -> List[InsightEvent]:
        """
        Looks up management events or CloudTrail Insights events that are captured by CloudTrail. You can look up events that occurred in
        a region within the last 90 days. Lookup supports the following attributes for management events:
        :param start_time: {datetime.datetime} Specifies that only events that occur after or at the specified time are returned.
            If the specified start time is after the specified end time, an error is returned.
        :param end_time: {datetime.datetime} Specifies that only events that occur before or at the specified time are returned.
            If the specified end time is before the specified start time, an error is returned.
        :param last_success_time:  {datetime.datetime} Date Time object to search insights older from.
        :param limit: {int} Max insights to returns
        :param existing_ids: {[str]} List of already seen insights
        :param event_category: {str} Specifies the event category. If you do not specify an event category, events of the category are not returned in the response. For example, if you do not specify insight as the value of EventCategory , no Insights events are returned.
        :return: {[InsightEvent]} List of Insight Events data models
        """

        paginator = self.client.get_paginator("lookup_events")
        page_iterator = paginator.paginate(
            StartTime=start_time,
            EndTime=end_time,
            EventCategory=event_category,
            PaginationConfig={"PageSize": PAGE_SIZE},
        )
        filtered_insights = []

        # Iterate in descending order and return the oldest events that are greater or equals than last success time
        for page in page_iterator:
            self.validate_response(page, error_msg="Failed to get insights page.")
            new_insights = [
                self.parser.build_insight_event_obj(event)
                for event in page.get("Events")
            ]

            # Filter insights older than last success time
            new_insights = [
                insight
                for insight in new_insights
                if insight.event_time >= last_success_time
            ]

            # Filter already seen insights
            new_insights = filter_old_alerts(
                siemplify=self.siemplify,
                alerts=new_insights,
                existing_ids=existing_ids,
                id_key=INSIGHT_ID_FIELD,
            )

            if not new_insights:
                break
            filtered_insights.extend(new_insights)

        return filtered_insights[-limit:] if limit else filtered_insights
