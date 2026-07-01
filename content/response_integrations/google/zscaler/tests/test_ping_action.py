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

import pathlib
from typing import Any
from ..actions import Ping


def test_ping_isolated(
    script_session: Any,
    mock_siemplify: Any,
    action_output: Any,
) -> None:
    _ = script_session
    _ = mock_siemplify

    Ping.main()

    assert action_output.is_success is True
    assert "Connection Established" in action_output.output_message
