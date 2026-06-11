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

from file_utilities.core.AttachmentsManager import (
    AttachmentsManager,
    ExecutionScope,
)
from file_utilities.tests.common import (
    ATTACHMENT_METADATA_1_KEY,
    ATTACHMENT_METADATA_CASE_KEY,
    EXPECTED_BASE64_BLOB_LENGTH,
    EXPECTED_CASE_EVIDENCE_NAME,
    EXPECTED_EVIDENCE_NAME,
    SCOPE_ALERT_PARAM,
    SCOPE_CASE_PARAM,
)
from file_utilities.tests.core.product import FileUtilitiesProduct

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from TIPCommon.types import SingleJson


def test_attachments_manager_alert_scope(
    product: FileUtilitiesProduct,
    mock_siemplify: MagicMock,
    load_mock_data: SingleJson,
) -> None:
    """Verify attachment retrieval and filtering under Alert execution scope.

    Args:
        product: Injected simulator fixture handling entity and blob state.
        mock_siemplify: Initialized mock SDK controller setting target scope context.
        load_mock_data: Declarative JSON fixture mapping raw metadata records.
    """
    rec: SingleJson = load_mock_data[ATTACHMENT_METADATA_1_KEY]
    product.set_metadata_records([rec])

    mock_siemplify.current_alert.identifier = rec["alertIdentifier"]

    mgr: AttachmentsManager = AttachmentsManager(mock_siemplify)
    filtered: list[SingleJson] = mgr.get_attachments_by_scope(
        execution_scope=ExecutionScope.Alert,
        attachment_scope_param=SCOPE_ALERT_PARAM,
    )

    assert len(filtered) == 1
    assert filtered[0]["evidenceName"] == EXPECTED_EVIDENCE_NAME


def test_attachments_manager_case_scope(
    product: FileUtilitiesProduct,
    mock_siemplify: MagicMock,
    load_mock_data: SingleJson,
) -> None:
    """Verify attachment filtering under Case execution scope choice.

    Args:
        product: Injected simulator fixture handling entity and blob state.
        mock_siemplify: Initialized mock SDK controller setting target scope context.
        load_mock_data: Declarative JSON fixture mapping raw metadata records.
    """
    rec: SingleJson = load_mock_data[ATTACHMENT_METADATA_CASE_KEY]
    product.set_metadata_records([rec])

    mgr: AttachmentsManager = AttachmentsManager(mock_siemplify)
    filtered: list[SingleJson] = mgr.get_attachments_by_scope(
        execution_scope=ExecutionScope.Alert,
        attachment_scope_param=SCOPE_CASE_PARAM,
    )

    assert len(filtered) == 1
    assert filtered[0]["evidenceName"] == EXPECTED_CASE_EVIDENCE_NAME


def test_attachments_manager_blobs_population(
    product: FileUtilitiesProduct,
    mock_siemplify: MagicMock,
    load_mock_data: SingleJson,
) -> None:
    """Verify dynamic base64 encoding and population of binary attachment streams.

    Args:
        product: Injected simulator fixture handling entity and blob state.
        mock_siemplify: Initialized mock SDK controller setting target scope context.
        load_mock_data: Declarative JSON fixture mapping raw metadata records.
    """
    rec: SingleJson = load_mock_data[ATTACHMENT_METADATA_1_KEY]
    product.set_metadata_records([rec])
    product.set_blob("4", b"dummy_image_bytes")

    mgr: AttachmentsManager = AttachmentsManager(mock_siemplify)
    populated: list[SingleJson] = mgr.get_attachment_blobs([rec])

    assert len(populated) == 1
    assert "base64_blob" in populated[0]
    assert len(populated[0]["base64_blob"]) == EXPECTED_BASE64_BLOB_LENGTH
