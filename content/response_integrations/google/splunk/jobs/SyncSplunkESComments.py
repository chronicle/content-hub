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
from splunk.core.SplunkManager import SplunkManager
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, utc_now
from TIPCommon.extraction import extract_action_param
from splunk.core.constants import (
    OPEN_CASE_STATUS_ENUM,
    SIEMPLIFY_COMMENT_PREFIX,
    SPLUNK_COMMENT_PREFIX,
    SYNC_COMMENTS_SCRIPT_NAME,
    DEFAULT_DEVICE_PRODUCT,
)


@output_handler
def main():
    siemplify = SiemplifyJob()

    try:
        siemplify.script_name = SYNC_COMMENTS_SCRIPT_NAME

        siemplify.LOGGER.info("--------------- JOB STARTED ---------------")

        # Configurations.
        server_address = extract_action_param(
            siemplify=siemplify,
            param_name="Server Address",
            is_mandatory=True,
            print_value=True,
        )

        username = extract_action_param(
            siemplify=siemplify, param_name="Username", print_value=False
        )

        password = extract_action_param(
            siemplify=siemplify, param_name="Password", print_value=False
        )

        api_token = extract_action_param(
            siemplify=siemplify, param_name="API Token", print_value=False
        )
        verify_ssl = extract_action_param(
            siemplify=siemplify, input_type=bool, param_name="Verify SSL"
        )
        ca_certificate = extract_action_param(
            siemplify=siemplify, param_name="CA Certificate File", print_value=False
        )

        manager = SplunkManager(
            server_address=server_address,
            verify_ssl=verify_ssl,
            username=username,
            password=password,
            api_token=api_token,
            ca_certificate=ca_certificate,
            siemplify_logger=siemplify.LOGGER,
        )

        # Get last Successful execution time.
        last_successful_execution_time = siemplify.fetch_timestamp(datetime_format=True)

        # Save current time at timestamp to make sure all alerts are taken.
        new_timestamp = utc_now()

        # Get open cases that created by the connector
        cases_ids = siemplify.get_cases_by_filter(
            case_names=[DEFAULT_DEVICE_PRODUCT], statuses=[OPEN_CASE_STATUS_ENUM]
        )
        if cases_ids:
            siemplify.LOGGER.info(f"Found {len(cases_ids)} open cases")
        siemplify.LOGGER.info(cases_ids)
        all_cases = []
        for case_id in cases_ids:
            case = siemplify._get_case_by_id(str(case_id))
            all_cases.append(case)

        # Sync Events Comments to Splunk ES
        siemplify.LOGGER.info(
            "--- Start synchronize Events Comments from Siemplify to Splunk ES ---"
        )

        for case in all_cases:
            siemplify.LOGGER.info(f'Run on case with id: {case.get("identifier")}')
            case_comments = siemplify.get_case_comments(case.get("identifier"))
            siemplify.LOGGER.info(
                f"Found {len(case_comments)} comments "
                f"for case with id: {case.get('identifier')} "
            )

            for comment in case_comments:
                # Covert to datetime
                comment_time = convert_unixtime_to_datetime(
                    (comment.get("modification_time_unix_time_in_ms", 0))
                )

                # Check that the comment is newer than the JOB timestamp and comment didn't come from Splunk ES
                if comment_time > last_successful_execution_time and not comment.get(
                    "comment"
                ).startswith(SPLUNK_COMMENT_PREFIX):
                    siemplify.LOGGER.info(
                        f"Found new comment at Case {case.get('identifier')}"
                    )

                    # Add to comment Siemplify prefix in order to identify the comment as a siemplify comment
                    comment_text = f"{SIEMPLIFY_COMMENT_PREFIX}{comment.get('comment')}"

                    # Update all Alert's tickets in Splunk
                    for alert in case.get("cyber_alerts", []):
                        if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                            ticket_number = alert.get("additional_properties", {}).get(
                                "TicketId"
                            )
                        else:
                            ticket_number = alert.get("additional_data")

                        if ticket_number:
                            # Add the comment to Splunk ticket
                            try:
                                manager.add_comment_to_event(
                                    ticket_number, comment_text
                                )
                                siemplify.LOGGER.info(
                                    f"Add comment to ticket {ticket_number}"
                                )
                            except Exception as err:
                                siemplify.LOGGER.error(
                                    f"Failed to add comment to ticket {ticket_number}, "
                                    f"error: {err}"
                                )
                                siemplify.LOGGER.exception(err)
                        else:
                            siemplify.LOGGER.info(
                                "Cannot find issue key. "
                                f"Comments from case {case.get('identifier')} "
                                "not added to issue"
                            )

        siemplify.LOGGER.info(
            " --- Finish synchronize comments from cases to Splunk tickets --- "
        )

        # Sync Events Comment to Siemplify
        siemplify.LOGGER.info(
            "--- Start synchronize Events Comments from Splunk to Siemplify ---"
        )

        for case in all_cases:
            for alert in case.get("cyber_alerts", []):
                if alert.get("reporting_product") == DEFAULT_DEVICE_PRODUCT:
                    ticket_number = alert.get("additional_properties", {}).get(
                        "TicketId"
                    )
                else:
                    ticket_number = alert.get("additional_data")

                if ticket_number:
                    try:
                        tickets = manager.get_events_by_filter(
                            event_ids=[ticket_number]
                        )
                        if tickets:
                            ticket = tickets[0]
                            if ticket.comments:
                                ticket_matching_case_id = case.get("identifier")
                                case_comments = [
                                    comment.get("comment")
                                    for comment in siemplify.get_case_comments(
                                        ticket_matching_case_id
                                    )
                                ]
                                siemplify.LOGGER.info(
                                    f"Found {len(ticket.comments)} comment "
                                    f"for event: {ticket_number}"
                                )

                                # Get all comments that didn't come from Siemplify
                                comments_to_add = [
                                    comment
                                    for comment in ticket.comments
                                    if not comment.startswith(SIEMPLIFY_COMMENT_PREFIX)
                                ]
                                comments_to_add = [
                                    comment
                                    for comment in comments_to_add
                                    if f"{SPLUNK_COMMENT_PREFIX}{comment}"
                                    not in case_comments
                                ]

                                # Add comments to cases.
                                if comments_to_add:
                                    siemplify.LOGGER.info(
                                        "Add comments to case "
                                        f"with id: {ticket_matching_case_id}"
                                    )
                                    for comment in comments_to_add:
                                        comment_with_prefix = (
                                            f"{SPLUNK_COMMENT_PREFIX}{comment}"
                                        )
                                        siemplify.add_comment(
                                            comment_with_prefix,
                                            ticket_matching_case_id,
                                            None,
                                        )
                                    siemplify.LOGGER.info(
                                        "Comments were added successfully"
                                    )
                                else:
                                    siemplify.LOGGER.info(
                                        f"No new comments in event -{ticket_number}"
                                    )

                            else:
                                siemplify.LOGGER.info(
                                    f"No new comments in event -{ticket_number}"
                                )

                    except Exception as err:
                        siemplify.LOGGER.error(
                            f"Failed to get details for event {ticket_number}."
                        )
                        siemplify.LOGGER.exception(err)
                else:
                    siemplify.LOGGER.info(
                        "Cannot find issue key. Comments from "
                        f"case {case.get('identifier')} not added to issue"
                    )

        siemplify.LOGGER.info(
            " --- Finish synchronize comments from Splunk notable events to cases --- "
        )
        # Update last successful run time with new_timestamp.
        siemplify.save_timestamp(new_timestamp=new_timestamp)
        siemplify.LOGGER.info("--------------- JOB FINISHED ---------------")

    except Exception as err:
        siemplify.LOGGER.exception(f"Got exception on main handler.Error: {err}")
        raise


if __name__ == "__main__":
    main()
