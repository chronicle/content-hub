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


from google_threat_intelligence.core.auth_manager import (
    AuthManager,
    AuthManagerParams,
)


def test_auth_manager_active_group_injection():
    params = AuthManagerParams(
        api_root="https://api.test",
        api_key="test_key",
        asm_project_name="proj1",
        verify_ssl=True,
        active_group="test-group-123",
    )
    manager = AuthManager(params=params)
    session = manager.prepare_session()

    assert session.headers.get("x-apikey") == "test_key"
    assert session.headers.get("X-Active-Group") == "test-group-123"


def test_auth_manager_no_active_group():
    params = AuthManagerParams(
        api_root="https://api.test",
        api_key="test_key",
        asm_project_name="proj1",
        verify_ssl=True,
        active_group=None,
    )
    manager = AuthManager(params=params)
    session = manager.prepare_session()

    assert session.headers.get("x-apikey") == "test_key"
    assert "X-Active-Group" not in session.headers
