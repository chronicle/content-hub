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
from typing import Tuple
import datetime

from .constants import QUERY_TIME_FORMAT


# Move to TIP Common
def get_timestamps(start_time_string: str, end_time_string: str) -> Tuple[str, str]:
    """
    Get start and end time timestamps
    Args:
        start_time_string (str): Start time
        end_time_string (str): End time
    Returns:
        (tuple): start and end time
    """
    if not start_time_string:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Range" parameter.'
        )

    if not end_time_string:
        end_time_string = datetime.datetime.utcnow().strftime(QUERY_TIME_FORMAT)

    if start_time_string > end_time_string:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time_string, end_time_string
