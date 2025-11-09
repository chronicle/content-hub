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
from mp.core.data_models.playbooks.overview.metadata import (
    Overview,
    BuiltOverview,
    NonBuiltOverview,
    OverviewType,
)

BUILT_OVERVIEW: BuiltOverview = {
    "OverviewTemplate": {
        "Identifier": "identifier",
        "Name": "name",
        "Creator": "creator",
        "PlaybookDefinitionIdentifier": "playbook_id",
        "Type": 0,
        "AlertRuleType": "alert_rule_type",
        "Roles": [1, 2],
    },
    "Roles": ["role1", "role2"],
}

NON_BUILT_OVERVIEW: NonBuiltOverview = {
    "identifier": "identifier",
    "name": "name",
    "creator": "creator",
    "playbook_id": "playbook_id",
    "type": "PLAYBOOK_DEFAULT",
    "alert_rule_type": "alert_rule_type",
    "roles": [1, 2],
    "role_names": ["role1", "role2"],
}

OVERVIEW = Overview(
    identifier="identifier",
    name="name",
    creator="creator",
    playbook_id="playbook_id",
    type_=OverviewType.PLAYBOOK_DEFAULT,
    alert_rule_type="alert_rule_type",
    roles=[1, 2],
    role_names=["role1", "role2"],
)

BUILT_OVERVIEW_WITH_NONE: BuiltOverview = {
    "OverviewTemplate": {
        "Identifier": "identifier",
        "Name": "name",
        "Creator": None,
        "PlaybookDefinitionIdentifier": "playbook_id",
        "Type": 0,
        "AlertRuleType": None,
        "Roles": [1, 2],
    },
    "Roles": ["role1", "role2"],
}

NON_BUILT_OVERVIEW_WITH_NONE: NonBuiltOverview = {
    "identifier": "identifier",
    "name": "name",
    "creator": None,
    "playbook_id": "playbook_id",
    "type": "PLAYBOOK_DEFAULT",
    "alert_rule_type": None,
    "roles": [1, 2],
    "role_names": ["role1", "role2"],
}

OVERVIEW_WITH_NONE = Overview(
    identifier="identifier",
    name="name",
    creator=None,
    playbook_id="playbook_id",
    type_=OverviewType.PLAYBOOK_DEFAULT,
    alert_rule_type=None,
    roles=[1, 2],
    role_names=["role1", "role2"],
)


class TestOverviewDataModel:
    def test_from_built_with_valid_data(self):
        assert Overview.from_built("", BUILT_OVERVIEW) == OVERVIEW

    def test_from_non_built_with_valid_data(self):
        assert Overview.from_non_built("", NON_BUILT_OVERVIEW) == OVERVIEW

    def test_to_built(self):
        assert OVERVIEW.to_built() == BUILT_OVERVIEW

    def test_to_non_built(self):
        assert OVERVIEW.to_non_built() == NON_BUILT_OVERVIEW

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Overview.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Overview.from_non_built("", {})

    def test_from_built_with_none_values(self):
        assert Overview.from_built("", BUILT_OVERVIEW_WITH_NONE) == OVERVIEW_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert Overview.from_non_built("", NON_BUILT_OVERVIEW_WITH_NONE) == OVERVIEW_WITH_NONE

    def test_to_built_with_none_values(self):
        assert OVERVIEW_WITH_NONE.to_built() == BUILT_OVERVIEW_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert OVERVIEW_WITH_NONE.to_non_built() == NON_BUILT_OVERVIEW_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert Overview.from_built("", BUILT_OVERVIEW).to_built() == BUILT_OVERVIEW

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert Overview.from_non_built("", NON_BUILT_OVERVIEW).to_non_built() == NON_BUILT_OVERVIEW
