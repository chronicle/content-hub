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
from mp.core.data_models.playbooks.playbook import (
    Playbook,
    BuiltPlaybook,
    NonBuiltPlaybook,
)
from mp.core.data_models.release_notes.metadata import (
    ReleaseNote,
    BuiltReleaseNote,
    NonBuiltReleaseNote,
)
from .constants import (
    STEP,
    BUILT_STEP,
    NON_BUILT_STEP,
    OVERVIEW,
    BUILT_OVERVIEW,
    NON_BUILT_OVERVIEW,
    PLAYBOOK_WIDGET_METADATA,
    BUILT_PLAYBOOK_WIDGET_METADATA,
    NON_BUILT_PLAYBOOK_WIDGET_METADATA,
    TRIGGER,
    BUILT_TRIGGER,
    NON_BUILT_TRIGGER,
    PLAYBOOK_METADATA,
    BUILT_PLAYBOOK_METADATA,
    NON_BUILT_PLAYBOOK_METADATA,
)

BUILT_RELEASE_NOTE: BuiltReleaseNote = {
    "ChangeDescription": "description",
    "Deprecated": False,
    "New": True,
    "ItemName": "item_name",
    "ItemType": "item_type",
    "PublishTime": 1672531200,
    "Regressive": False,
    "Removed": False,
    "TicketNumber": "ticket",
    "IntroducedInIntegrationVersion": 1.0,
}

NON_BUILT_RELEASE_NOTE: NonBuiltReleaseNote = {
    "description": "description",
    "deprecated": False,
    "integration_version": 1.0,
    "item_name": "item_name",
    "item_type": "item_type",
    "publish_time": "2023-01-01",
    "regressive": False,
    "removed": False,
    "ticket_number": "ticket",
    "new": True,
}

RELEASE_NOTE = ReleaseNote(
    description="description",
    deprecated=False,
    new=True,
    item_name="item_name",
    item_type="item_type",
    publish_time=1672531200,
    regressive=False,
    removed=False,
    ticket="ticket",
    version=1.0,
)

BUILT_PLAYBOOK: BuiltPlaybook = {
    "CategoryName": "Content Hub",
    "OverviewTemplatesDetails": [
        {
            "OverviewTemplate": BUILT_OVERVIEW,
            "Roles": ["role1", "role2"],
        }
    ],
    "WidgetTemplates": [BUILT_PLAYBOOK_WIDGET_METADATA],
    "Definition": {
        **BUILT_PLAYBOOK_METADATA,
        "Steps": [BUILT_STEP],
        "Triggers": [BUILT_TRIGGER],
        "OverviewTemplates": [BUILT_OVERVIEW],
    },
}

NON_BUILT_PLAYBOOK: NonBuiltPlaybook = {
    "steps": [NON_BUILT_STEP],
    "triggers": [NON_BUILT_TRIGGER],
    "overviews": [NON_BUILT_OVERVIEW],
    "widgets": [NON_BUILT_PLAYBOOK_WIDGET_METADATA],
    "release_notes": [NON_BUILT_RELEASE_NOTE],
    "meta_data": NON_BUILT_PLAYBOOK_METADATA,
}

PLAYBOOK = Playbook(
    steps=[STEP],
    overviews=[OVERVIEW],
    widgets=[PLAYBOOK_WIDGET_METADATA],
    triggers=[TRIGGER],
    release_notes=[RELEASE_NOTE],
    meta_data=PLAYBOOK_METADATA,
)


class TestPlaybookDataModel:
    def test_to_built(self):
        assert PLAYBOOK.to_built() == BUILT_PLAYBOOK

    def test_to_non_built(self):
        assert PLAYBOOK.to_non_built() == NON_BUILT_PLAYBOOK
