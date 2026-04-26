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
from soar_sdk.SiemplifyUtils import utc_now, unix_now
import datetime
import json
import os

from .ObserveITConstants import LIMIT_IDS_IN_IDS_FILE, ALERT_ID_FIELD, TIMEOUT_THRESHOLD


class ObserveITCommon:
    def __init__(self, siemplify_logger):
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def is_approaching_timeout(connector_starting_time, python_process_timeout):
        """
        Check if a timeout is approaching.
        :return: {bool} True if timeout is close, False otherwise
        """
        processing_time_ms = unix_now() - connector_starting_time
        return processing_time_ms > python_process_timeout * 1000 * TIMEOUT_THRESHOLD

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset_in_hours):
        """
        Validate timestamp in range
        :param last_run_timestamp: {datetime} last run timestamp
        :param offset_in_hours: {datetime} last run timestamp
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        current_time = utc_now()
        # Check if first run
        if current_time - last_run_timestamp > datetime.timedelta(
            hours=offset_in_hours
        ):
            return current_time - datetime.timedelta(hours=offset_in_hours)
        else:
            return last_run_timestamp

    def read_ids(self, ids_file_path):
        """
        Read existing alerts IDs from ids file (from last 24h only)
        :param ids_file_path: {unicode} Path to the IDS file.
        :return: {list} List of ids
        """
        if not os.path.exists(ids_file_path):
            return []

        try:
            with open(ids_file_path, "r") as f:
                return json.loads(f.read())
        except Exception as e:
            self.siemplify_logger.error(f"Unable to read ids file: {e}")
            self.siemplify_logger.exception(e)
            return []

    def write_ids(self, ids_file_path, ids):
        """
        Write ids to the ids file
        :param ids_file_path: {unicode} Path to the IDS file.
        :param ids: {list} The ids to write to the file
        :return: {None}
        """
        ids = ids[-LIMIT_IDS_IN_IDS_FILE:]
        try:
            if not os.path.exists(os.path.dirname(ids_file_path)):
                os.makedirs(os.path.dirname(ids_file_path))

            with open(ids_file_path, "w") as f:
                try:
                    for chunk in json.JSONEncoder().iterencode(ids):
                        f.write(chunk)
                except:
                    f.seek(0)
                    f.truncate()
                    f.write("[]")
                    raise
        except Exception as e:
            self.siemplify_logger.error(
                f"Failed writing IDs to IDs file, ERROR: {str(e)}"
            )
            self.siemplify_logger.exception(e)

    @staticmethod
    def filter_old_ids(alerts, existing_ids, id_field=ALERT_ID_FIELD):
        """
        Filter ids that were already processed
        :param alerts: {list} The objects to filter
        :param existing_ids: {list} The ids to filter
        :param id_field: {str or unicode} Id filed to get from alert
        :return: {list} The filtered alerts
        """
        new_alerts = []

        for alert in alerts:
            if getattr(alert, id_field) not in existing_ids:
                new_alerts.append(alert)

        return new_alerts

    @staticmethod
    def convert_comma_separated_to_list(comma_separated):
        # type: (unicode or str) -> list
        """
        Convert comma-separated string to list
        @param comma_separated: String with comma-separated values
        @return: List of values
        """
        return (
            [item.strip() for item in comma_separated.split(",")]
            if comma_separated
            else []
        )

    @staticmethod
    def convert_list_to_comma_separated_string(iterable):
        # type: (list or set) -> unicode
        """
        Convert list to comma separated string
        @param iterable: List or Set to covert
        """
        return ", ".join(iterable)
