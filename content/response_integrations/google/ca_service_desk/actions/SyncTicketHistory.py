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
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager
import datetime

# Consts.
CA_PROVIDER = "CaServiceDesk"
CA_PREFIX = "CA: History Sync Job CA <-> Siemplify"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(CA_PROVIDER)
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    ca_manager = CaSoapManager(api_root, username, password)

    # Parameters.
    comment_type_field = siemplify.parameters.get("Comment Type Field", "type.sym")
    analyst_name_field = siemplify.parameters.get(
        "Analyst Name Field", "analyst.combo_name"
    )
    timestamp_field = siemplify.parameters.get("TimeStamp Field", "time_stamap")

    # Fetch scope data.
    ca_ticket_id = siemplify.current_alert.external_id

    # Get comments for ticket.
    comments = ca_manager.get_incident_comments_since_time(
        ref_num=ca_ticket_id, start_time_unixtime_milliseconds=0
    )

    # Inject history to case.
    for comment in comments:
        comment_content = comment.get("description")
        comment_type = comment.get(comment_type_field)
        analyst_name = comment.get(analyst_name_field)
        comment_timestamp = comment.get(timestamp_field)

        # Convert Unix time to UTC datetime.
        ticket_time_datetime = (
            datetime.datetime.utcfromtimestamp(float(comment_timestamp))
            if comment_timestamp
            else None
        )

        # Build comment string.
        comment_str = f"{CA_PREFIX} \nTicket ID:{ca_ticket_id}  \nComment: {comment_content} \nAnalyst: {analyst_name} \nTicket Type: {comment_type} \nTime: {ticket_time_datetime}"

        # Add comment to case.
        siemplify.add_comment(comment_str)

    output_message = (
        f'History synced."{len(comments) if comments else 0}" comments added'
    )

    siemplify.result.add_result_json(comments)
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
