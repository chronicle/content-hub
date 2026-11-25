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

"""Tests configuration file."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rsa_net_witness_edr.core.RSAExceptions import RSAError
from rsa_net_witness_edr.core.RSAManager import RSAManager

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def mock_get_endpoint_details_to_raise_manager_error(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Mock the test get endpoint details function to raise
    RSANetWitnessEDR error
    """
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
        raise RSAError("Connectivity error")

    monkeypatch.setattr(
        RSAManager,
        "get_endpoint_details",
        mock_raise_manager_error,
    )
