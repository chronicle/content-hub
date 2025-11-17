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

import pytest

from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.data_models.playbooks.step.step_debug_data import (
    StepDebugData,
)
from mp.core.data_models.playbooks.step.step_debug_enrichment_data import (
    DebugStepEnrichmentData,
)
from mp.core.data_models.playbooks.step.step_parameter import (
    StepParameter,
)

from .constants import (
    BUILT_STEP,
    BUILT_STEP_DEBUG_DATA,
    BUILT_STEP_DEBUG_DATA_WITH_NONE,
    BUILT_STEP_DEBUG_ENRICHMENT_DATA,
    BUILT_STEP_PARAMETER,
    BUILT_STEP_PARAMETER_WITH_NONE,
    BUILT_STEP_WITH_NONE,
    DEBUG_STEP_ENRICHMENT_DATA,
    NON_BUILT_STEP,
    NON_BUILT_STEP_DEBUG_DATA,
    NON_BUILT_STEP_DEBUG_DATA_WITH_NONE,
    NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA,
    NON_BUILT_STEP_PARAMETER,
    NON_BUILT_STEP_PARAMETER_WITH_NONE,
    NON_BUILT_STEP_WITH_NONE,
    STEP,
    STEP_DEBUG_DATA,
    STEP_DEBUG_DATA_WITH_NONE,
    STEP_PARAMETER,
    STEP_PARAMETER_WITH_NONE,
    STEP_WITH_NONE,
)


class TestDebugStepEnrichmentDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert (
            DebugStepEnrichmentData.from_built(BUILT_STEP_DEBUG_ENRICHMENT_DATA)
            == DEBUG_STEP_ENRICHMENT_DATA
        )

    def test_from_non_built_with_valid_data(self) -> None:
        assert (
            DebugStepEnrichmentData.from_non_built(NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA)
            == DEBUG_STEP_ENRICHMENT_DATA
        )

    def test_to_built(self) -> None:
        assert DEBUG_STEP_ENRICHMENT_DATA.to_built() == BUILT_STEP_DEBUG_ENRICHMENT_DATA

    def test_to_non_built(self) -> None:
        assert DEBUG_STEP_ENRICHMENT_DATA.to_non_built() == NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            DebugStepEnrichmentData.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            DebugStepEnrichmentData.from_non_built({})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert (
            DebugStepEnrichmentData.from_built(BUILT_STEP_DEBUG_ENRICHMENT_DATA).to_built()
            == BUILT_STEP_DEBUG_ENRICHMENT_DATA
        )

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            DebugStepEnrichmentData.from_non_built(
                NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA
            ).to_non_built()
            == NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA
        )


class TestStepDebugDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert StepDebugData.from_built(BUILT_STEP_DEBUG_DATA) == STEP_DEBUG_DATA

    def test_from_non_built_with_valid_data(self) -> None:
        assert StepDebugData.from_non_built(NON_BUILT_STEP_DEBUG_DATA) == STEP_DEBUG_DATA

    def test_to_built(self) -> None:
        assert StepDebugData.from_built(BUILT_STEP_DEBUG_DATA).to_built() == BUILT_STEP_DEBUG_DATA

    def test_to_non_built(self) -> None:
        assert (
            StepDebugData.from_non_built(NON_BUILT_STEP_DEBUG_DATA).to_non_built()
            == NON_BUILT_STEP_DEBUG_DATA
        )

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            StepDebugData.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            StepDebugData.from_non_built({})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert StepDebugData.from_built(BUILT_STEP_DEBUG_DATA).to_built() == BUILT_STEP_DEBUG_DATA

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            StepDebugData.from_non_built(NON_BUILT_STEP_DEBUG_DATA).to_non_built()
            == NON_BUILT_STEP_DEBUG_DATA
        )

    def test_from_built_with_none_values(self) -> None:
        assert (
            StepDebugData.from_built(BUILT_STEP_DEBUG_DATA_WITH_NONE) == STEP_DEBUG_DATA_WITH_NONE
        )

    def test_from_non_built_with_none_values(self) -> None:
        assert (
            StepDebugData.from_non_built(NON_BUILT_STEP_DEBUG_DATA_WITH_NONE)
            == STEP_DEBUG_DATA_WITH_NONE
        )

    def test_to_built_with_none_values(self) -> None:
        assert STEP_DEBUG_DATA_WITH_NONE.to_built() == BUILT_STEP_DEBUG_DATA_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert STEP_DEBUG_DATA_WITH_NONE.to_non_built() == NON_BUILT_STEP_DEBUG_DATA_WITH_NONE


class TestStepParameterDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert StepParameter.from_built(BUILT_STEP_PARAMETER) == STEP_PARAMETER

    def test_from_non_built_with_valid_data(self) -> None:
        assert StepParameter.from_non_built(NON_BUILT_STEP_PARAMETER) == STEP_PARAMETER

    def test_to_built(self) -> None:
        assert STEP_PARAMETER.to_built() == BUILT_STEP_PARAMETER

    def test_to_non_built(self) -> None:
        assert STEP_PARAMETER.to_non_built() == NON_BUILT_STEP_PARAMETER

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            StepParameter.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            StepParameter.from_non_built({})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert StepParameter.from_built(BUILT_STEP_PARAMETER).to_built() == BUILT_STEP_PARAMETER

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            StepParameter.from_non_built(NON_BUILT_STEP_PARAMETER).to_non_built()
            == NON_BUILT_STEP_PARAMETER
        )

    def test_from_built_with_none_values(self) -> None:
        assert StepParameter.from_built(BUILT_STEP_PARAMETER_WITH_NONE) == STEP_PARAMETER_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert (
            StepParameter.from_non_built(NON_BUILT_STEP_PARAMETER_WITH_NONE)
            == STEP_PARAMETER_WITH_NONE
        )

    def test_to_built_with_none_values(self) -> None:
        assert STEP_PARAMETER_WITH_NONE.to_built() == BUILT_STEP_PARAMETER_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert STEP_PARAMETER_WITH_NONE.to_non_built() == NON_BUILT_STEP_PARAMETER_WITH_NONE


class TestStepDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert Step.from_built("", BUILT_STEP) == STEP

    def test_from_non_built_with_valid_data(self) -> None:
        assert Step.from_non_built("", NON_BUILT_STEP) == STEP

    def test_to_built(self) -> None:
        assert STEP.to_built() == BUILT_STEP

    def test_to_non_built(self) -> None:
        assert STEP.to_non_built() == NON_BUILT_STEP

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            Step.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            Step.from_non_built("", {})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert Step.from_built("", BUILT_STEP).to_built() == BUILT_STEP

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert Step.from_non_built("", NON_BUILT_STEP).to_non_built() == NON_BUILT_STEP

    def test_from_built_with_none_values(self) -> None:
        assert Step.from_built("", BUILT_STEP_WITH_NONE) == STEP_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert Step.from_non_built("", NON_BUILT_STEP_WITH_NONE) == STEP_WITH_NONE

    def test_to_built_with_none_values(self) -> None:
        assert STEP_WITH_NONE.to_built() == BUILT_STEP_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert STEP_WITH_NONE.to_non_built() == NON_BUILT_STEP_WITH_NONE
