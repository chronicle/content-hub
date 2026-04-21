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

from TIPCommon.base.action import ExecutionState

from open_search.actions import advanced_os_search
from open_search.tests.common import CONFIG_PATH, SEARCH_RESULTS
from open_search.tests.core.product import OpenSearchProduct
from open_search.tests.core.session import OpenSearchSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE = "Query ran successfully 1 hits found"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Index": "test-index",
        "Query": "foo:bar",
        "Limit": 10,
        "Display Field": "foo",
        "Search Field": "bar",
        "Timestamp Field": "timestamp",
        "Oldest Date": "2023-01-01",
        "Earliest Date": "2023-01-31",
    },
)
def test_advanced_os_search_success(
    opensearch_product: OpenSearchProduct,
    os_mock_session: OpenSearchSession,
    action_output: MockActionOutput,
) -> None:
    opensearch_product.set_search_results(SEARCH_RESULTS)
    advanced_os_search.main()
    assert len(os_mock_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
