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

import base64
import json
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
import TIPCommon
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import EntityTypes

if not hasattr(TIPCommon, "extract_configuration_param"):
    from TIPCommon.extraction import extract_configuration_param

    TIPCommon.extract_configuration_param = extract_configuration_param

from cisco_umbrella.actions import GetDomainSecurityInfo

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def mock_siemplify() -> Iterator[Mock]:
    with patch("cisco_umbrella.actions.GetDomainSecurityInfo.SiemplifyAction") as mock_class:
        siemplify = Mock()
        mock_class.return_value = siemplify
        siemplify.target_entities = []
        siemplify.result = Mock()
        yield siemplify


@pytest.fixture
def mock_umbrella_manager() -> Iterator[Mock]:
    with patch("cisco_umbrella.actions.GetDomainSecurityInfo.CiscoUmbrellaIvestigate") as mock_class:
        manager = Mock()
        mock_class.return_value = manager
        yield manager


def test_get_domain_security_info_attachment_is_string(
    mock_siemplify: Mock,
    mock_umbrella_manager: Mock
) -> None:
    """Test base64_content passed to add_entity_attachment is a str."""
    entity = Mock()
    entity.entity_type = EntityTypes.HOSTNAME
    entity.identifier = "example.com"
    entity.is_internal = False

    mock_siemplify.target_entities = [entity]

    mock_response = {
        "dga_score": 0,
        "security_score": 100,
        "rip_score": 0,
    }
    mock_umbrella_manager.get_domain_security_info.return_value = (
        mock_response
    )

    with patch(
        "cisco_umbrella.actions.GetDomainSecurityInfo.extract_configuration_param",
        return_value="dummy_token",
    ):
        GetDomainSecurityInfo.main()

    mock_umbrella_manager.get_domain_security_info.assert_called_once_with(
        "example.com"
    )
    mock_siemplify.result.add_entity_attachment.assert_called_once()

    args, _ = mock_siemplify.result.add_entity_attachment.call_args
    target_identifier, filename, base64_content = args

    assert target_identifier == "example.com"
    assert filename == "SecurityInfo.json"

    assert isinstance(
        base64_content, str
    ), "base64_content must be a string to be JSON serializable."
    assert not isinstance(base64_content, bytes)

    serialized_payload = json.dumps({"attachment": base64_content})
    assert isinstance(serialized_payload, str)

    decoded_bytes = base64.b64decode(base64_content)
    decoded_json = json.loads(decoded_bytes.decode("utf-8"))
    assert decoded_json == mock_response

    mock_siemplify.end.assert_called_once()
    output_message, result_value, status = mock_siemplify.end.call_args[0]
    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True


def test_get_domain_security_info_not_found_handling(
    mock_siemplify: Mock,
    mock_umbrella_manager: Mock
) -> None:
    """Test handling when a queried domain is not found in Umbrella."""
    entity = Mock()
    entity.entity_type = EntityTypes.HOSTNAME
    entity.identifier = "unknown-domain.com"
    entity.is_internal = False

    mock_siemplify.target_entities = [entity]
    mock_umbrella_manager.get_domain_security_info.side_effect = Exception(
        "Domain not found"
    )

    with patch(
        "cisco_umbrella.actions.GetDomainSecurityInfo.extract_configuration_param",
        return_value="dummy_token",
    ):
        GetDomainSecurityInfo.main()

    mock_umbrella_manager.get_domain_security_info.assert_called_once_with(
        "unknown-domain.com"
    )
    mock_siemplify.result.add_entity_attachment.assert_not_called()
    mock_siemplify.end.assert_called_once()
    output_message, _result_value, _status = mock_siemplify.end.call_args[0]
    expected_message = "\nThe following entities were not found in Cisco Umbrella:\nunknown-domain.com\n"
    assert output_message == expected_message


def test_get_domain_security_info_no_matching_entities(
    mock_siemplify: Mock,
    mock_umbrella_manager: Mock
) -> None:
    """Test handling when no external HOSTNAME entities exist."""
    internal_entity = Mock()
    internal_entity.entity_type = EntityTypes.HOSTNAME
    internal_entity.identifier = "internal.local"
    internal_entity.is_internal = True

    mock_siemplify.target_entities = [internal_entity]

    with patch(
        "cisco_umbrella.actions.GetDomainSecurityInfo.extract_configuration_param",
        return_value="dummy_token",
    ):
        GetDomainSecurityInfo.main()

    mock_umbrella_manager.get_domain_security_info.assert_not_called()
    mock_siemplify.result.add_entity_attachment.assert_not_called()
    mock_siemplify.end.assert_called_once()
    output_message, result_value, status = mock_siemplify.end.call_args[0]
    assert "No entities were enriched" in output_message
