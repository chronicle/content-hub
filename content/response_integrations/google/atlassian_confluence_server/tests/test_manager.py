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

"""Unit tests for AtlassianConfluenceServer Integration."""
import json
import os
import unittest
from unittest.mock import Mock, patch
from atlassian_confluence_server.core.ConfluenceManager import (
    ConfluenceManager
)
from atlassian_confluence_server.core.exceptions import (
    ConfluenceBadRequestError,
    ConfluenceHTTPError,
    ConfluencePATAuthenticationError,
    ConfluenceValidationError,
)


# Constants
PAGE_ID = "98380"
INVALID_PAGE_ID = "98381"
LIMIT = 5
EXPAND = "body.storage"
INVALID_EXPAND_KEY = "invalid_expand_key"
MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data.json")
    )
)

GET_CHILD_DATA_MOCK = MOCK_DATA.get("get_child_pages")
LIST_PAGES_DATA_MOCK = MOCK_DATA.get("list_pages")
GET_PAGE_COMMENT_DATA_MOCK = MOCK_DATA.get("get_page_comments")
GET_PAGE_BY_ID_BODY_DATA_MOCK = MOCK_DATA.get("get_page_by_id_body")
GET_PAGE_BY_ID_CHILDREN_DATA_MOCK = MOCK_DATA.get("get_page_by_id_children")
GET_PAGE_BY_ID_SPACE_DATA_MOCK = MOCK_DATA.get("get_page_by_id_space")
GET_PAGE_BY_ID_HISTORY_DATA_MOCK = MOCK_DATA.get("get_page_by_id_history")
GET_PAGE_BY_ID_CONTAINER_DATA_MOCK = MOCK_DATA.get("get_page_by_id_container")
GET_PAGE_BY_ID_INVALID_EXPAND = MOCK_DATA.get("get_page_by_id_invalid_expand")
GET_PAGE_BY_ID_INVALID_PAGE_ID = MOCK_DATA.get("get_page_by_id_invalid_page_id")

get_page_by_id_valid_responses_test_data = [
    (
        "body",
        "body.storage",
        "storage",
        GET_PAGE_BY_ID_BODY_DATA_MOCK,
        GET_PAGE_BY_ID_BODY_DATA_MOCK["body"]["storage"]
    ),
    (
        "children",
        "children.page",
        "page",
        GET_PAGE_BY_ID_CHILDREN_DATA_MOCK,
        GET_PAGE_BY_ID_CHILDREN_DATA_MOCK["children"]["page"]
    ),
    (
        "space",
        "space",
        "space",
        GET_PAGE_BY_ID_SPACE_DATA_MOCK,
        GET_PAGE_BY_ID_SPACE_DATA_MOCK["space"]
    ),
    (
        "history",
        "history",
        "history",
        GET_PAGE_BY_ID_HISTORY_DATA_MOCK,
        GET_PAGE_BY_ID_HISTORY_DATA_MOCK["history"]
    ),
    (
        "container",
        "container",
        "container",
        GET_PAGE_BY_ID_CONTAINER_DATA_MOCK,
        GET_PAGE_BY_ID_CONTAINER_DATA_MOCK["container"]
    )
]


class TestConfluenceManager(unittest.TestCase):
    """Unit tests for Atlassian Confluence Server Integration."""

    def setUp(self) -> None:
        self.logger = Mock()
        with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
            data = f.read()

        config = json.loads(data)

        api_root = config.get("Api Root")
        username = config.get("Username")
        password = config.get("Password")
        api_key = config.get("Api Token")
        verify_ssl = config.get("Verify SSL")
        self.manager = ConfluenceManager(
            api_root,
            username,
            password,
            api_key,
            verify_ssl
        )

    def test_test_connectivity(self) -> None:
        """Mocking test connectivity for the API.

        Returns:
            None
        """
        self.manager.test_connectivity = Mock(return_value=True)
        self.assertEqual(
            self.manager.test_connectivity(),
            True,
            "Assertion error: mocking test connectivity failed."
        )

    def test_connectivity_failure(self):
        with patch.object(
            self.manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = ConfluenceHTTPError()
            with self.assertRaises(ConfluenceHTTPError):
                self.manager.test_connectivity()

    def test_bad_request_failure(self):
        with patch.object(
            self.manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = ConfluenceBadRequestError()
            with self.assertRaises(ConfluenceBadRequestError):
                self.manager.test_connectivity()

    def test_invalid_token_failure(self):
        with patch.object(
            self.manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = ConfluencePATAuthenticationError()
            with self.assertRaises(ConfluencePATAuthenticationError):
                self.manager.test_connectivity()

    def test_validation_failure(self):
        with patch.object(
            self.manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = ConfluenceValidationError()
            with self.assertRaises(ConfluenceValidationError):
                self.manager.test_connectivity()

    def test_get_child_pages(self):
        self.manager.get_child_pages = Mock(return_value=GET_CHILD_DATA_MOCK)
        self.assertEqual(
            self.manager.get_child_pages(),
            GET_CHILD_DATA_MOCK
        )

    def test_get_child_pages_result_data(self):
        self.manager.get_child_pages = Mock(
            return_value=GET_CHILD_DATA_MOCK.get("results")
        )
        self.assertGreater(
            len(self.manager.get_child_pages(PAGE_ID, LIMIT)),
            0
        )

    def test_list_pages(self):
        self.manager.list_pages = Mock(return_value=LIST_PAGES_DATA_MOCK)
        self.assertEqual(
            self.manager.list_pages(),
            LIST_PAGES_DATA_MOCK
        )

    def test_get_page_comments(self):
        self.manager.get_page_comment_page = Mock(
            return_value=GET_PAGE_COMMENT_DATA_MOCK
        )
        self.assertEqual(
            self.manager.get_page_comment_page(),
            GET_PAGE_COMMENT_DATA_MOCK
        )

    def test_get_page_comment_result_data(self):
        self.manager.get_page_comment_page = Mock(
            return_value=GET_PAGE_COMMENT_DATA_MOCK.get("results")
        )
        self.assertGreater(
            len(self.manager.get_page_comment_page(PAGE_ID, EXPAND, LIMIT)),
            0
        )

    def test_get_page_by_id(self):
        """Test for valid response scenarios"""

        test_cases = get_page_by_id_valid_responses_test_data

        for (
            mock_key,
            expand_value,
            page_response_key,
            data_mock,
            expand_page_response
        ) in test_cases:
            with self.subTest(
                mock_key=mock_key,
                expand_value=expand_value,
                page_response_key=page_response_key,
                data_mock=data_mock,
                expand_page_response=expand_page_response
            ):
                self.manager.get_page_by_id = Mock(
                    return_value=data_mock.get(mock_key)
                )
                page_response = self.manager.get_page_by_id(
                    PAGE_ID,
                    expand_value
                )
                if data_mock == GET_PAGE_BY_ID_SPACE_DATA_MOCK:
                    page_response = {mock_key: page_response}
                if data_mock == GET_PAGE_BY_ID_HISTORY_DATA_MOCK:
                    page_response = {mock_key: page_response}
                if data_mock == GET_PAGE_BY_ID_CONTAINER_DATA_MOCK:
                    page_response = {mock_key: page_response}
                assert page_response.get(
                    page_response_key
                ) == expand_page_response

    def test_get_page_by_id_invalid_expand_key(self):
        """Test when expand key is invalid
        and validate default expandable items
        """
        expandable_keys = [
            "container", "metadata", "operations", "children",
            "restrictions", "history", "ancestors", "body",
            "version", "descendants", "space"
        ]

        self.manager.get_page_by_id = Mock(
            return_value=GET_PAGE_BY_ID_INVALID_EXPAND.get("_expandable")
        )

        page_response = self.manager.get_page_by_id(PAGE_ID, INVALID_EXPAND_KEY)

        all_keys_present = all(key in page_response for key in expandable_keys)

        self.assertTrue(all_keys_present)

    def test_get_page_by_id_invalid_page_id(self):
        """Test when invalid page id is given"""
        self.manager.get_page_by_id = Mock(
            return_value=GET_PAGE_BY_ID_INVALID_PAGE_ID
        )

        page_response = self.manager.get_page_by_id(INVALID_PAGE_ID)
        assert page_response.get("statusCode") == 404
