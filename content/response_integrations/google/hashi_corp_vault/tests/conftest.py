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

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

import pytest
import soar_sdk  # noqa: F401

from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="module")
def manager_fixture() -> Iterator[HashiCorpVaultManager]:
    config_path = pathlib.Path(__file__).parent / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    api_root = config.get("API Root")
    token = config.get("Token")
    username = config.get("Username")
    password = config.get("Password")
    verify_ssl = config.get("Verify SSL")
    key_value_secret_engine_path = config.get("Key-Value Secret Engine Path")

    yield HashiCorpVaultManager(
        api_root,
        token,
        username,
        password,
        verify_ssl,
        key_value_secret_engine_path,
    )
