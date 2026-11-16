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

import re

from integration_testing.request import HttpMethod
from integration_testing.requests.session import HistoryRecord


def assert_search_alerts(
    history_records: list[HistoryRecord],
    index: int,
):
    """Assert that a history record on given index is a get search alerts request."""
    assert re.search(
        r"/api/alerts/v7/orgs/\w+/alerts/_search",
        history_records[index].request.url.path
    ) is not None
    assert history_records[index].request.method == HttpMethod.POST
