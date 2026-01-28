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

import pytest
from unittest.mock import MagicMock
from mp_describe.plugin_impl import MyPluginInput, MyPluginOutput, run_feature

@pytest.mark.anyio
async def test_run_feature():
    # Setup
    test_case = MagicMock()
    test_case.input = MyPluginInput(user_query="test query")
    resources_dir = MagicMock()

    # Execute
    output = await run_feature(test_case, resources_dir)

    # Verify
    assert isinstance(output, MyPluginOutput)
    assert output.response == "Hello from plugin!"
