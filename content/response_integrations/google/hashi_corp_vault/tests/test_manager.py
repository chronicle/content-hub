from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from hashi_corp_vault.core.datamodels import *

from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager

KV_DATA_MOCK = {
    "request_id": "19c82158-asdasdasdasdasdasdasdasd",
    "lease_id": "",
    "renewable": False,
    "lease_duration": 0,
    "data": {
        "keys": [
            "folder1/",
            "hello",
            "tesr2",
            "test"
        ]
    },
    "wrap_info": None,
    "warnings": None,
    "auth": None
}

READ_DATA_MOCK = {
    "request_id": "cea74cb4-asdasdasdasdasdasdasdasd",
    "lease_id": "",
    "renewable": False,
    "lease_duration": 0,
    "data": {
        "data": {
            "key0": "value0",
            "key1": "newkeyadded"
        }
    },
    "wrap_info": None,
    "warnings": None,
    "auth": None
}


class TestHashiCorpVaultManager(unittest.TestCase):
    def setUp(self) -> None:
        with open("config.json", "r") as f:
            data = f.read()

        config = json.loads(data)

        api_root = config.get("API Root")
        token = config.get("Token")
        username = config.get("Username")
        password = config.get("Password")
        verify_ssl = config.get("Verify SSL")
        key_value_secret_engine_path = config.get("Key-Value Secret Engine Path")
        self.manager = HashiCorpVaultManager(
            api_root,
            token,
            username,
            password,
            verify_ssl,
            key_value_secret_engine_path
        )

    def test_get_api_token(self) -> None:
        self.manager._get_api_token = Mock(return_value="dummy_token")
        self.assertEqual(
            self.manager._get_api_token(),
            "dummy_token",
            "Assertion error: mocking api token failed."
        )

    def test_test_connectivity(self) -> None:
        self.manager.test_connectivity = Mock(return_value=True)
        self.assertEqual(
            self.manager.test_connectivity(),
            True,
            "Assertion error: mocking test connectivity failed."
        )

    def test_list_key_value_secret_keys(self) -> None:
        mock_response = KeyValueResponse(
            raw_data=KV_DATA_MOCK,
            keys=KV_DATA_MOCK.get("data", {}).get("keys", [])
        )
        self.manager.list_key_value_secret_keys = Mock(
            return_value=mock_response
        )
        self.assertEqual(
            self.manager.list_key_value_secret_keys(),
            mock_response,
            "Assertion error: mocking list key value secret keys failed."
        )

    def test_read_key_value_secret(self) -> None:
        self.manager.read_key_value_secret = Mock(
            return_value=READ_DATA_MOCK
        )
        self.assertEqual(
            self.manager.read_key_value_secret(),
            READ_DATA_MOCK,
            "Assertion error: mocking read_key_value_secret failed."
        )
