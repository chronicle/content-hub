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

from typing import Annotated, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc


class ConnectorRuleType(mp.core.data_models.abc.RepresentableEnum):
    ALLOW_LIST = 0
    DISALLOW_LIST = 1


class BuiltConnectorRule(TypedDict):
    RuleName: str
    RuleType: int


class NonBuiltConnectorRule(TypedDict):
    rule_name: str
    rule_type: str


class ConnectorRule(mp.core.data_models.abc.Buildable[BuiltConnectorRule, NonBuiltConnectorRule]):
    rule_name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    rule_type: ConnectorRuleType

    @classmethod
    def _from_built(cls, built: BuiltConnectorRule) -> ConnectorRule:
        return cls(
            rule_name=built["RuleName"],
            rule_type=ConnectorRuleType(built["RuleType"]),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltConnectorRule) -> ConnectorRule:
        return cls(
            rule_name=non_built["rule_name"],
            rule_type=ConnectorRuleType.from_string(non_built["rule_type"]),
        )

    def to_built(self) -> BuiltConnectorRule:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object

        """
        return BuiltConnectorRule(
            RuleName=self.rule_name,
            RuleType=self.rule_type.value,
        )

    def to_non_built(self) -> NonBuiltConnectorRule:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltConnectorRule(
            rule_name=self.rule_name,
            rule_type=self.rule_type.to_string(),
        )
