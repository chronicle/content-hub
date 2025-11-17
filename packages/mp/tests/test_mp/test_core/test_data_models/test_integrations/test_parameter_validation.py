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
from mp.core.data_models.integrations.connector.parameter import ConnectorParameter, ParamMode
from mp.core.data_models.integrations.integration_meta.parameter import IntegrationParameter
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from mp.core.validators import validate_param_name, validate_ssl_parameter


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

    def test_ssl_parameter_missing(self) -> None:
        script_name = "TestIntegration"  # Not in excluded list
        parameters: list[IntegrationParameter | ConnectorParameter] = []

        with pytest.raises(ValueError, match="missing a 'Verify SSL' parameter"):
            validate_ssl_parameter(script_name, parameters)

    def test_ssl_parameter_excluded_integration(self) -> None:
        for script_name in mp.core.constants.EXCLUDED_NAMES_WITHOUT_VERIFY_SSL:
            parameters: list[IntegrationParameter | ConnectorParameter] = []
            # Should not raise an exception
            validate_ssl_parameter(script_name, parameters)

    def test_ssl_parameter_wrong_type(self) -> None:
        script_name = "TestIntegration"  # Not in excluded list
        parameters = [
            IntegrationParameter(
                name="Verify SSL",
                type_=ScriptParamType.STRING,  # Wrong type, should be BOOLEAN
                description="Test description",
                is_mandatory=False,
                default_value="true",
                integration_identifier="Integration",
            )
        ]

        with pytest.raises(TypeError, match="must be of type 'boolean'"):
            validate_ssl_parameter(script_name, parameters)

    def test_ssl_parameter_wrong_default_value(self) -> None:
        script_name = "TestIntegration"  # Not in excluded list
        parameters = [
            IntegrationParameter(
                name="Verify SSL",
                type_=ScriptParamType.BOOLEAN,
                description="Test description",
                is_mandatory=False,
                default_value=False,  # Wrong default value, should be True
                integration_identifier="Integration",
            )
        ]

        with pytest.raises(ValueError, match="must be a boolean true"):
            validate_ssl_parameter(script_name, parameters)

    def test_ssl_parameter_excluded_from_default_value_check(self) -> None:
        for script_name in mp.core.constants.EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE:
            parameters = [
                IntegrationParameter(
                    name="Verify SSL",
                    type_=ScriptParamType.BOOLEAN,
                    description="Test description",
                    is_mandatory=False,
                    default_value=False,
                    integration_identifier="Integration",
                )
            ]
            # Should not raise an exception
            validate_ssl_parameter(script_name, parameters)

    def test_valid_ssl_parameter_names(self) -> None:
        script_name = "TestIntegration"  # Not in excluded list

        for ssl_param_name in mp.core.constants.VALID_SSL_PARAM_NAMES:
            parameters = [
                IntegrationParameter(
                    name=ssl_param_name,
                    type_=ScriptParamType.BOOLEAN,
                    description="Test description",
                    is_mandatory=False,
                    default_value=True,
                    integration_identifier="Integration",
                )
            ]
            # Should not raise an exception
            validate_ssl_parameter(script_name, parameters)

    def test_connector_parameter_with_valid_ssl_parameter(self) -> None:
        # Create a valid SSL parameter
        ssl_param = ConnectorParameter(
            name="Verify SSL",
            type_=ScriptParamType.BOOLEAN,
            description="Whether to verify SSL certificates",
            is_mandatory=False,
            default_value=True,
            integration_identifier="Integration",
            is_advanced=False,
            mode=ParamMode.REGULAR,
        )

        # If we get here without exceptions, the test passed
        assert ssl_param.name == "Verify SSL"
        assert ssl_param.type_ == ScriptParamType.BOOLEAN
        assert ssl_param.default_value is True
