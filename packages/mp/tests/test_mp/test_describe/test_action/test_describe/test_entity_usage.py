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

import tempfile
from typing import Any

import anyio
import deepdiff
import pytest
import yaml

from mp.core.constants import ACTIONS_AI_DESCRIPTION_FILE
from mp.describe.action.describe import DescribeAction


class TestEntityScopes:
    @pytest.mark.anyio
    async def test_action_run_on_no_entities(
        self,
        mock_integration: anyio.Path,
        ping_action: anyio.Path,
        ping_expected_results: dict[str, Any],
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = anyio.Path(tmpdir)
            describer: DescribeAction = DescribeAction(
                integration=mock_integration.name,
                actions={ping_action.name},
                src=mock_integration,
                dst=results_dir,
            )

            await describer.describe_actions()

            results_file: anyio.Path = results_dir / ACTIONS_AI_DESCRIPTION_FILE
            actual_content: str = await results_file.read_text(encoding="utf-8")
            ping_actual_results: dict[str, Any] = yaml.safe_load(actual_content)

            assert deepdiff.DeepDiff(ping_expected_results, ping_actual_results) == {}
