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

from .all_blocks_existing_validation import AllBlocksExistValidation
from .block_env_matches_playbook_env_validation import BlockEnvMatchesPlaybookEnvValidation
from .block_overview_validation import BlockDoesNotContainAnOverviewValidation
from .debug_data_validation import DebugDataValidation
from .environments_validation import EnvironmentsValidation
from .loop_step_validation import LoopStepValidation
from .steps_parameters_validation import StepParamsValidation
from .version_bump_validation import VersionBumpValidation

if TYPE_CHECKING:
    from mp.validate.data_models import Validator


def get_playbooks_pre_build_validations() -> list[Validator]:
    """Get a list of all available pre-build validations.

    Returns:
        A list of all `Validator` instances.

    """
    return _get_non_priority_validations() + _get_priority_validations()


def _get_non_priority_validations() -> list[Validator]:
    return [
        VersionBumpValidation(),
        BlockDoesNotContainAnOverviewValidation(),
        EnvironmentsValidation(),
        StepParamsValidation(),
        BlockEnvMatchesPlaybookEnvValidation(),
        DebugDataValidation(),
    ]


def _get_priority_validations() -> list[Validator]:
    return [AllBlocksExistValidation(), LoopStepValidation()]
