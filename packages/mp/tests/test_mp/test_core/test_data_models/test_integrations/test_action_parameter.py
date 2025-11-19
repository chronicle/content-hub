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

import pytest

from mp.core.data_models.integrations.action.parameter import ActionParameter, ActionParamType

NO_OPT_VALUES_MSG: str = "Multiple options parameters must have optional values"
OPT_VALUES_WRONG_TYPE_MSG: str = "Non-multiple options parameters must not have optional values"
DEFAULT_VALUE_NOT_IN_OPTIONS: str = (
    "The default value of a multiple options parameter must be one of the options"
)


class TestActionParameterValidation:
    def test_ddl_with_optional_values_valid(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=["option1", "option2"],
            default_value=None,
        )
        # If no exception is raised, the test passes
        assert param.optional_values == ["option1", "option2"]

    def test_multi_choice_with_optional_values_valid(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.MULTI_CHOICE_PARAMETER,
            optional_values=["choice1", "choice2"],
            default_value=None,
        )
        assert param.optional_values == ["choice1", "choice2"]

    def test_multi_values_with_optional_values_valid(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.MULTI_VALUES,
            optional_values=["value1", "value2"],
            default_value=None,
        )
        assert param.optional_values == ["value1", "value2"]

    def test_ddl_without_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=NO_OPT_VALUES_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.DDL,
                optional_values=None,
                default_value=None,
            )

    def test_multi_choice_without_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=NO_OPT_VALUES_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.MULTI_CHOICE_PARAMETER,
                optional_values=None,
                default_value=None,
            )

    def test_multi_values_without_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=NO_OPT_VALUES_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.MULTI_VALUES,
                optional_values=None,
                default_value=None,
            )

    def test_string_with_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=OPT_VALUES_WRONG_TYPE_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.STRING,
                optional_values=["value1", "value2"],
                default_value=None,
            )

    def test_integer_with_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=OPT_VALUES_WRONG_TYPE_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.INTEGER,
                optional_values=["1", "2"],
                default_value=None,
            )

    def test_boolean_with_optional_values_invalid(self) -> None:
        with pytest.raises(ValueError, match=OPT_VALUES_WRONG_TYPE_MSG):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.BOOLEAN,
                optional_values=["true", "false"],
                default_value=None,
            )

    def test_string_without_optional_values_valid(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.STRING,
            optional_values=None,
            default_value=None,
        )
        assert param.optional_values is None

    def test_empty_optional_values_list_for_ddl_valid(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=[],
            default_value=None,
        )
        assert param.optional_values == []


class TestActionParameterDefaultValueValidation:
    def test_ddl_default_value_in_optional_values(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=["option1", "option2"],
            default_value="option1",
        )
        # If no exception is raised, the test passes
        assert param.default_value == "option1"

    def test_multi_choice_default_value_in_optional_values(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.MULTI_CHOICE_PARAMETER,
            optional_values=["choice1", "choice2"],
            default_value="choice2",
        )
        assert param.default_value == "choice2"

    def test_ddl_default_value_not_in_optional_values(self) -> None:
        with pytest.raises(ValueError, match=DEFAULT_VALUE_NOT_IN_OPTIONS):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.DDL,
                optional_values=["option1", "option2"],
                default_value="invalid_option",
            )

    def test_multi_choice_default_value_not_in_optional_values(self) -> None:
        with pytest.raises(ValueError, match=DEFAULT_VALUE_NOT_IN_OPTIONS):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.MULTI_CHOICE_PARAMETER,
                optional_values=["choice1", "choice2"],
                default_value="invalid_choice",
            )

    def test_ddl_no_default_value(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=["option1", "option2"],
            default_value=None,
        )
        assert param.default_value is None

    def test_multi_values_multiple_default_values(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.MULTI_VALUES,
            optional_values=["value1", "value2", "value3"],
            default_value="value1",
        )
        assert param.default_value == "value1"

    def test_case_sensitive_validation(self) -> None:
        with pytest.raises(ValueError, match=DEFAULT_VALUE_NOT_IN_OPTIONS):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.DDL,
                optional_values=["Option1", "Option2"],
                default_value="option1",
            )

    def test_empty_string_default_value(self) -> None:
        ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=["option1", "option2"],
            default_value="",
        )

    def test_none_default_value(self) -> None:
        ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.DDL,
            optional_values=["option1", "option2"],
            default_value=None,
        )

    def test_non_ddl_parameter_default_value(self) -> None:
        param: ActionParameter = ActionParameter(
            name="test param",
            description="Test parameter",
            is_mandatory=True,
            type_=ActionParamType.STRING,
            optional_values=None,
            default_value="any_value",
        )
        assert param.default_value == "any_value"

    def test_numeric_default_value(self) -> None:
        with pytest.raises(ValueError, match=DEFAULT_VALUE_NOT_IN_OPTIONS):
            ActionParameter(
                name="test param",
                description="Test parameter",
                is_mandatory=True,
                type_=ActionParamType.DDL,
                optional_values=["1", "2", "3"],
                default_value=1,  # numeric instead of string
            )
