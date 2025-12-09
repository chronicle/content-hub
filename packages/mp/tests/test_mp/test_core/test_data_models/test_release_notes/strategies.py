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

from hypothesis import strategies as st

from test_mp.test_core.test_data_models.utils import (
    st_valid_long_description,
    st_valid_version,
)

# Strategies for ReleaseNote
ST_VALID_BUILT_RELEASE_NOTE_DICT = st.fixed_dictionaries(
    {
        "ChangeDescription": st_valid_long_description,
        "Deprecated": st.booleans(),
        "New": st.booleans(),
        "ItemName": st.text(),
        "ItemType": st.text(),
        "Regressive": st.booleans(),
        "Removed": st.booleans(),
        "TicketNumber": st.none() | st.text(),
        "IntroducedInIntegrationVersion": st_valid_version,
    },
    optional={
        "PublishTime": st.integers(),
    },
)

ST_VALID_NON_BUILT_RELEASE_NOTE_DICT = st.fixed_dictionaries(
    {
        "description": st_valid_long_description,
        "integration_version": st_valid_version,
        "item_name": st.text(),
        "item_type": st.text(),
    },
    optional={
        "deprecated": st.booleans(),
        "publish_time": st.none() | st.datetimes().map(lambda d: d.strftime("%Y-%m-%d")),
        "regressive": st.booleans(),
        "removed": st.booleans(),
        "ticket_number": st.text(),
        "new": st.booleans(),
    },
)
