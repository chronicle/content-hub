# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyJob import SiemplifyJob
from ..core.LogRhythmManager import LogRhythmRESTManager
from soar_sdk.SiemplifyUtils import (
    convert_unixtime_to_datetime,
    utc_now,
    convert_string_to_datetime,
)
from ..core.constants import (
    SYNC_ALARM_COMMENTS_SCRIPT_NAME,
    DEFAULT_DEVICE_PRODUCT,
    CASE_STATUS_OPEN,
    LOGRHYTHM_COMMENT_PREFIX,
    SIEMPLIFY_COMMENT_PREFIX,
    LOGRHYTHM_ALERT_COMMENTS_PREFIX,
)


UTC_TIMEZONE_STRING = "UTC"


def get_clean_comments(raw_comments):

    return [
        (
            comment[len(LOGRHYTHM_ALERT_COMMENTS_PREFIX) :]
            if comment.startswith(LOGRHYTHM_ALERT_COMMENTS_PREFIX)
            else comment
        )
        for comment in raw_comments
    ]


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_ALARM_COMMENTS_SCRIPT_NAME

        api_root = siemplify.extract_job_param(param_name="Api Root", is_mandatory=True)
        api_token = siemplify.extract_job_param(
            param_name="Api Token", is_mandatory=True
        )
        verify_ssl = siemplify.extract_job_param(
            param_name="Verify SSL", is_mandatory=True, input_type=bool
        )

        siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

        manager = LogRhythmRESTManager(
            api_root=api_root,
            api_key=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        last_successful_execution_time = siemplify.fetch_timestamp(datetime_format=True)

        new_timestamp = utc_now()

        fetched_open_cases_ids = siemplify.get_cases_by_filter(
            statuses=[CASE_STATUS_OPEN], case_names=[DEFAULT_DEVICE_PRODUCT]
        )

        siemplify.LOGGER.info(
            "--- Start synchronize cases Comments from "
            "Siemplify to LogRhythm alarm comments---"
        )

        for case_id in fetched_open_cases_ids:
            case = siemplify._get_case_by_id(case_id)
            case_identifier = case.get("identifier")
            siemplify.LOGGER.info(f"Run on case with id: {case_identifier}")
            case_comments = siemplify.get_case_comments(case_identifier)
            siemplify.LOGGER.info(
                f"Found {len(case_comments)} comments for case with id: "
                f"{case_identifier}"
            )
            for comment in case_comments:
                comment_time = convert_unixtime_to_datetime(
                    (comment.get("modification_time_unix_time_in_ms", 0))
                )
                if comment_time < last_successful_execution_time or comment.get(
                    "comment"
                ).startswith(LOGRHYTHM_COMMENT_PREFIX):
                    continue
                siemplify.LOGGER.info(f"Found new comment at Case {case_identifier}")

                comment_text = f"{SIEMPLIFY_COMMENT_PREFIX}{comment.get('comment')}"
                for alert in case.get("cyber_alerts", []):
                    alarm_id = None
                    if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                        if alert.get("additional_properties", {}).get("number") is None:
                            alarm_id = alert.get("additional_properties", {}).get(
                                "TicketId"
                            )
                    else:
                        alarm_id = alert.get("additional_data")
                    if alarm_id:
                        try:
                            manager.add_comment_to_alarm(
                                alarm_id=alarm_id, comment=comment_text
                            )
                            siemplify.LOGGER.info(f"Add comment to alarm {alarm_id}")
                        except Exception as err:
                            siemplify.LOGGER.error(
                                f"Failed to add comment to alarm {alarm_id}, "
                                f"error: {err}"
                            )
                            siemplify.LOGGER.exception(err)
                    else:
                        siemplify.LOGGER.info(
                            f"Cannot find issue key. Comments from case "
                            f"{case_identifier} not added to issue"
                        )
        siemplify.LOGGER.info(
            " --- Finish synchronize comments from cases to LogRhythm alarms --- "
        )

        siemplify.LOGGER.info(
            "--- Start synchronize alarm comments from LogRhythm to Siemplify ---"
        )
        for case_id in fetched_open_cases_ids:
            case = siemplify._get_case_by_id(case_id)
            case_identifier = case.get("identifier")
            for alert in case.get("cyber_alerts", []):
                alarm_id = None
                if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                    if alert.get("additional_properties", {}).get("number") is None:
                        alarm_id = alert.get("additional_properties", {}).get(
                            "TicketId"
                        )
                else:
                    alarm_id = alert.get("additional_data")
                if alarm_id:
                    try:
                        raw_comments = manager.get_alarm_comments(alarm_id=alarm_id)
                        if raw_comments:
                            raw_comments = sorted(
                                raw_comments, key=lambda raw_comment: raw_comment.date
                            )
                            comments_to_add = [
                                raw_comment.comments
                                for raw_comment in raw_comments
                                if convert_string_to_datetime(
                                    raw_comment.date, UTC_TIMEZONE_STRING
                                )
                                >= last_successful_execution_time
                                and convert_string_to_datetime(
                                    raw_comment.date, UTC_TIMEZONE_STRING
                                )
                                < new_timestamp
                            ]
                            clean_comments = get_clean_comments(comments_to_add)
                            comments_to_add = [
                                comment
                                for comment in clean_comments
                                if not (comment).startswith(SIEMPLIFY_COMMENT_PREFIX)
                            ]

                            if comments_to_add:
                                siemplify.LOGGER.info(
                                    f"Add comments to case with id: {case_identifier}"
                                )
                                for comment in comments_to_add:
                                    comment_with_prefix = (
                                        f"{LOGRHYTHM_COMMENT_PREFIX}{comment}"
                                    )
                                    siemplify.add_comment(
                                        comment_with_prefix, case_identifier, None
                                    )
                                siemplify.LOGGER.info(
                                    "Comments were added successfully"
                                )
                            else:
                                siemplify.LOGGER.info(
                                    f"No new comments in case - {case_identifier}"
                                )
                        else:
                            siemplify.LOGGER.info(
                                f"No new comments in case - {case_identifier}"
                            )
                    except Exception as err:
                        siemplify.LOGGER.error(
                            f"Failed to get details for alarm {alarm_id}."
                        )
                        siemplify.LOGGER.exception(err)
                else:
                    siemplify.LOGGER.info(
                        f"Cannot find issue key. Comments from case {case_identifier} "
                        f"not added to issue"
                    )
        siemplify.LOGGER.info(
            " --- Finish synchronize alarm comments from LogRhythm to Siemplify --- "
        )
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")
    except Exception as err:
        siemplify.LOGGER.exception(f"Got exception on main handler.Error: {err}")
        raise


if __name__ == "__main__":
    main()
