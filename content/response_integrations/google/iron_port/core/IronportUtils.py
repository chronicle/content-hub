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
from .IronportConstants import ASYNC_RUN_TIMEOUT_MS, ITERATION_DURATION_BUFFER
from soar_sdk.SiemplifyUtils import unix_now


def is_script_approaching_timeout(action_start_time):
    """
    Check if script timeout approaching
    :param action_start_time: {int} timeout in milliseconds
    :return: {bool} True - if timeout approaching, False - otherwise.
    """
    return (
        unix_now()
        >= action_start_time + ASYNC_RUN_TIMEOUT_MS - ITERATION_DURATION_BUFFER
    )
