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
from typing import Any
from unittest.mock import MagicMock
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from azure_active_directory.actions.Ping import main
from azure_active_directory.tests.conftest import LegacyActionOutput
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession


class TestPing:
    def test_ping_success(
        self,
        _script_session: AzureADSession,
        _product: AzureADProduct,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test successful connectivity check."""
        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Connection Established" in action_output.output_message

    def test_ping_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
    ) -> None:
        """Test Ping fails gracefully when the API returns an error."""
        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert "error" in action_output.output_message.lower()
