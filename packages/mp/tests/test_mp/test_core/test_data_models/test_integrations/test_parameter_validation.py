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

import pydantic
import pytest

import mp.core.constants
from mp.core.data_models.integrations.integration_meta.parameter import IntegrationParameter
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from mp.core.validators import validate_param_name


class TestVerifySSLParameterValidations:
    def test_param_name_max_length(self) -> None:
        long_name = "a" * (mp.core.constants.PARAM_NAME_MAX_LENGTH + 1)

        with pytest.raises(pydantic.ValidationError, match="string_too_long"):
            IntegrationParameter(
                name=long_name,
                type_=ScriptParamType.BOOLEAN,
                description="Test description",
                is_mandatory=False,
                default_value=True,
                integration_identifier="Integration",
            )

    def test_param_name_exact_max_length(self) -> None:
        exact_max_name = "a" * mp.core.constants.PARAM_NAME_MAX_LENGTH

        # Should not raise an exception
        param = IntegrationParameter(
            name=exact_max_name,
            type_=ScriptParamType.BOOLEAN,
            description="Test description",
            is_mandatory=False,
            default_value=True,
            integration_identifier="Integration",
        )

        assert len(param.name) == mp.core.constants.PARAM_NAME_MAX_LENGTH

    def test_param_name_max_words_validation(self) -> None:
        too_many_words = " ".join(["word"] * (mp.core.constants.PARAM_NAME_MAX_WORDS + 1))

        with pytest.raises(ValueError, match="exceeds maximum number of words"):
            validate_param_name(too_many_words)

    def test_param_name_exact_max_words(self) -> None:
        exact_max_words = " ".join(["word"] * mp.core.constants.PARAM_NAME_MAX_WORDS)

        # Should not raise an exception
        result = validate_param_name(exact_max_words)

        assert result == exact_max_words
        assert len(result.split()) == mp.core.constants.PARAM_NAME_MAX_WORDS

    def test_excluded_param_names_with_too_many_words(self) -> None:
        for excluded_name in mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS:
            # Should not raise an exception
            result = validate_param_name(excluded_name)
            assert result == excluded_name
