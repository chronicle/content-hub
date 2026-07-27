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
from .constants import ASYNC_ACTION_TIMEOUT_THRESHOLD_MS


def is_approaching_timeout(action_start_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_start_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    return (
        action_start_time > python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS
    )
