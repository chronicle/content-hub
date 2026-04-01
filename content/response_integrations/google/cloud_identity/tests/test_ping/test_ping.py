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

from actions.Ping import prepare_runner


def test_should_call_test_connectivity(action_context, api_manager) -> None:
    # GIVEN
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.test_connectivity.assert_called_once()
    assert result.value is True
    assert (
        "Successfully connected to the Cloud Identity server with the provided "
        "connection parameters!" in result.output_message
    )


def test_should_show_error_when(action_context, api_manager) -> None:
    # GIVEN
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.test_connectivity.side_effect = Exception("Something went wrong")

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.test_connectivity.assert_called_once()
    assert result.value is False
    assert (
        "Failed to connect to the Cloud Identity server. Error is: Something went wrong"
        in result.output_message
    )
