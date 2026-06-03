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

from typing import TYPE_CHECKING

import pytest
from file_utilities.actions import GetAttachment
from file_utilities.tests.common import (
    ACTION_ALERT_SCOPE_CONTEXT,
    ACTION_ALERT_SCOPE_ENTITIES,
    ACTION_ALERT_SCOPE_PARAMS,
    ACTION_CASE_SCOPE_CONTEXT,
    ACTION_CASE_SCOPE_PARAMS,
    ALERTS_FULL_DETAILS_KEY,
    ATTACHMENT_METADATA_1_KEY,
    ATTACHMENT_METADATA_CASE_KEY,
    CASE_METADATA_KEY,
    EXPECTED_OUTPUT_MESSAGE,
)
from file_utilities.tests.core.product import FileUtilitiesProduct
from file_utilities.tests.core.session import FileUtilitiesMockSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=ACTION_ALERT_SCOPE_PARAMS,
    entities=ACTION_ALERT_SCOPE_ENTITIES,
    input_context=ACTION_ALERT_SCOPE_CONTEXT,
)
def test_get_attachment_alert_scope(
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Verify end-to-end GetAttachment execution logic under Alert scope mapping.

    Args:
        product: Injected simulator fixture managing metadata and binary blobs.
        script_session: Intercepted outgoing mock HTTP session framework.
        load_mock_data: Dynamic declarative JSON loader mapping raw payloads.
        action_output: Intercepted action standard output streaming buffer.
    """
    rec: SingleJson = load_mock_data[ATTACHMENT_METADATA_1_KEY]
    product.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    product.set_alerts_full_details(load_mock_data[ALERTS_FULL_DETAILS_KEY])
    product.set_metadata_records([rec])
    product.set_blob("4", b"dummy_image_bytes")

    GetAttachment.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert EXPECTED_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value == 1
    assert len(script_session.request_history) == 4


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=ACTION_CASE_SCOPE_PARAMS,
    input_context=ACTION_CASE_SCOPE_CONTEXT,
)
def test_get_attachment_case_scope(
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Verify end-to-end GetAttachment execution logic under Case scope configuration.

    Args:
        product: Injected simulator fixture managing metadata and binary blobs.
        script_session: Intercepted outgoing mock HTTP session framework.
        load_mock_data: Dynamic declarative JSON loader mapping raw payloads.
        action_output: Intercepted action standard output streaming buffer.
    """
    rec: SingleJson = load_mock_data[ATTACHMENT_METADATA_CASE_KEY]
    product.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    product.set_alerts_full_details(load_mock_data[ALERTS_FULL_DETAILS_KEY])
    product.set_metadata_records([rec])
    product.set_blob("5", b"dummy_pdf_bytes")

    GetAttachment.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert EXPECTED_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value == 1
    assert len(script_session.request_history) == 4
