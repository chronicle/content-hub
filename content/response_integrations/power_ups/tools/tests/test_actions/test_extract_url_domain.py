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

from ...core.ToolsCommon import get_domain_from_string


def test_get_domain_from_string() -> None:
    assert (
        get_domain_from_string(
            identifier="https://test.google.com",
            extract_subdomain=True,
        )
        == "test.google.com"
    )
    assert (
        get_domain_from_string(
            identifier="https://google.com",
            extract_subdomain=True,
        )
        == "google.com"
    )
    assert (
        get_domain_from_string(
            identifier="https://subdomain.google.com",
            extract_subdomain=False,
        )
        == "google.com"
    )
    assert (
        get_domain_from_string(
            identifier="https://subdomain1.subdomain2.google.com",
            extract_subdomain=False,
        )
        == "google.com"
    )
    assert (
        get_domain_from_string(
            identifier="https://subdomain1.subdomain2.google.com",
            extract_subdomain=True,
        )
        == "subdomain1.subdomain2.google.com"
    )
