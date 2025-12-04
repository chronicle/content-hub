# Copyright 2025 Google LLC
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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import DefangText


@set_metadata(
    integration_config={},
    parameters={"Input": "http://example.com"},
)
def test_defang_http(action_output: MockActionOutput) -> None:
    DefangText.main()

    assert action_output.results.json_output.json_result == {
        "converted_text": "hxxp://example[.]com"
    }
    assert action_output.results.output_message == "Successfully defanged the input."
    assert action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config={},
    parameters={"Input": "https://example.com"},
)
def test_defang_https(action_output: MockActionOutput) -> None:
    DefangText.main()
    assert action_output.results.json_output.json_result == {
        "converted_text": "hxxps://example[.]com"
    }


@set_metadata(
    integration_config={},
    parameters={"Input": "1.1.1.1"},
)
def test_defang_ip(action_output: MockActionOutput) -> None:
    DefangText.main()
    assert action_output.results.json_output.json_result == {"converted_text": "1[.]1[.]1[.]1"}


@set_metadata(
    integration_config={},
    parameters={"Input": "user@example.com"},
)
def test_defang_email(action_output: MockActionOutput) -> None:
    DefangText.main()
    # Note: Our regex defangs domain too if it matches the pattern
    assert action_output.results.json_output.json_result == {
        "converted_text": "user[at]example[.]com"
    }


@set_metadata(
    integration_config={},
    parameters={
        "Input": "Check https://example.com/path?query=1 and 192.168.1.1 or "
        "user.name+tag@sub.example.co.uk"
    },
)
def test_defang_mixed(action_output: MockActionOutput) -> None:
    DefangText.main()
    expected = (
        "Check hxxps://example[.]com/path?query=1 and 192[.]168[.]1[.]1 or "
        "user.name+tag[at]sub[.]example[.]co[.]uk"
    )
    assert action_output.results.json_output.json_result == {"converted_text": expected}


@set_metadata(
    integration_config={},
    parameters={
        "Input": (
            "Check out https://example.com/path, http://test.org, and contact "
            "admin@example.com or support@sub.test.co.uk. Also check IPs "
            "192.168.1.1 and 10.0.0.1. This is some benign text that should "
            "not be affected. Here is another sentence with no IOCs."
        )
    },
)
def test_defang_complex(action_output: MockActionOutput) -> None:
    DefangText.main()
    expected = (
        "Check out hxxps://example[.]com/path, hxxp://test[.]org, and contact "
        "admin[at]example[.]com or support[at]sub[.]test[.]co[.]uk. Also check IPs "
        "192[.]168[.]1[.]1 and 10[.]0[.]0[.]1. This is some benign text that should "
        "not be affected. Here is another sentence with no IOCs."
    )
    assert action_output.results.json_output.json_result == {"converted_text": expected}


@set_metadata(
    integration_config={},
    parameters={"Input": ""},
)
def test_empty_input(action_output: MockActionOutput) -> None:
    DefangText.main()
    assert action_output.results.output_message == "Input text is empty."
    assert action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result == {"converted_text": ""}
