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

import json
import pathlib

from TIPCommon.types import SingleJson
from ...actions import RunSQLQuery

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from integration_testing.common import get_def_file_content

from ...tests.core.session import MySQLSession


CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

INSERT_QUERY = "INSERT INTO users (name) VALUES ('test');"
ACTION_PARAMETERS_INSERT = {"Database Name": "test_db", "Query": INSERT_QUERY}

SELECT_QUERY = "SELECT * FROM users WHERE id = 1;"
ACTION_PARAMETERS_SELECT = {"Database Name": "test_db", "Query": SELECT_QUERY}

FOUND_ONE_ROW_MSG = "Successfully finished search. Found 1 rows."
FOUND_ZERO_ROW_MSG = "Successfully finished search. Found 0 rows."


@set_metadata(
    parameters=ACTION_PARAMETERS_INSERT,
    integration_config=INTEGRATION_CONFIG,
)
def test_runsqlquery_action_with_insert(
    mysql_session: MySQLSession, action_output: MockActionOutput
):
    """
    Tests the full action script with an INSERT query.
    """
    cursor_mock = mysql_session.cursor_mock
    cursor_mock.rowcount = 1

    RunSQLQuery.main()

    assert FOUND_ZERO_ROW_MSG in action_output.results.output_message

    expected_json = []
    json_result = action_output.results.json_output.json_result
    assert json_result == expected_json
    assert action_output.results.result_value == json.dumps(expected_json)


@set_metadata(
    parameters=ACTION_PARAMETERS_SELECT,
    integration_config=INTEGRATION_CONFIG,
)
def test_runsqlquery_action_with_select(
    mysql_session: MySQLSession, action_output: MockActionOutput
):
    """
    Tests the full action script with a SELECT query.
    """
    cursor_mock = mysql_session.cursor_mock
    cursor_mock.description = [("id",)]
    cursor_mock.fetchall.return_value = [(101,)]

    RunSQLQuery.main()

    assert FOUND_ONE_ROW_MSG in action_output.results.output_message

    expected_json = [{"id": 101}]
    returned_json = action_output.results.json_output.json_result
    assert returned_json == expected_json

    returned_result_value = action_output.results.result_value
    assert returned_result_value == json.dumps(expected_json)
