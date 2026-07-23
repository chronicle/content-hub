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

import pathlib
import pytest

from ..core.MySQLManager import MySQLException, MySQLManager
from ..tests.core.session import MySQLSession

NON_MODIFYING_QUERIES = [
    "SELECT * FROM users;",
    "SELECT * FROM users JOIN orders ON users.id = orders.user_id WHERE users.id = 1;",
    "SELECT name FROM users WHERE id IN (SELECT user_id FROM active_sessions);",
]

MODIFYING_QUERIES = [
    "INSERT INTO users (id) VALUES ('1');",
    "INSERT INTO users (id, name) SELECT * FROM old_users WHERE old_users.id = 1;",
]

QUERIES_FOR_BULLETPROOF_TESTS = [NON_MODIFYING_QUERIES[0], MODIFYING_QUERIES[0]]


@pytest.mark.parametrize("query", QUERIES_FOR_BULLETPROOF_TESTS)
def test_successful_queries_are_bulletproof(query: str, mysql_session: MySQLSession):
    """
    Verifies that if cursor.execute() is successful, the transaction is closed properly.
    """
    manager = MySQLManager("user", "pass", "server", "db")
    cursor_mock = mysql_session.cursor_mock

    manager.execute(query)

    cursor_mock.execute.assert_called_once_with(query)
    mysql_session.rollback.assert_not_called()
    cursor_mock.close.assert_called_once()


@pytest.mark.parametrize("query", QUERIES_FOR_BULLETPROOF_TESTS)
def test_failing_queries_are_bulletproof(query: str, mysql_session: MySQLSession):
    """
    Verifies that if cursor.execute() fails, the transaction is
    rolled back and resources are cleaned up, for future queries safety.
    """
    manager = MySQLManager("user", "pass", "server", "db")
    cursor_mock = mysql_session.cursor_mock

    cursor_mock.execute.side_effect = Exception("Simulated DB Connection Error")

    with pytest.raises(MySQLException):
        manager.execute(query)

    cursor_mock.execute.assert_called_once_with(query)

    mysql_session.commit.assert_not_called()
    mysql_session.rollback.assert_called_once()
    cursor_mock.close.assert_called_once()


@pytest.mark.parametrize("query", NON_MODIFYING_QUERIES)
def test_select_query_does_not_commit(
    query: str,
    mysql_session: MySQLSession,
):
    """Verify that a non-modifying query (taking select as an example),
    does NOT call commit."""
    manager = MySQLManager("user", "pass", "server", "db")

    # Configure the cursor that our session holds
    mysql_session.cursor_mock.description = [("id",)]
    mysql_session.cursor_mock.fetchall.return_value = [(1,)]

    manager.execute(query)

    mysql_session.commit.assert_not_called()


@pytest.mark.parametrize("query", MODIFYING_QUERIES)
def test_insert_query_calls_commit(query: str, mysql_session: MySQLSession):
    """Verify that a modifying query (taking insert as an example), DOES call commit."""
    manager = MySQLManager("user", "pass", "server", "db")

    # Configure the cursor that our session holds
    mysql_session.cursor_instance.rowcount = 1

    manager.execute(query)

    mysql_session.commit.assert_called_once()
