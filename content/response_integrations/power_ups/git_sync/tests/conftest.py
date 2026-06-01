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

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from .core.product import GitSyncProduct
from .core.session import GitSyncMockSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def git_sync_product() -> GitSyncProduct:
    return GitSyncProduct()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    git_sync_product,
) -> GitSyncMockSession:
    """Mock GitSync scripts' session and get back an object to view request history"""
    session = GitSyncMockSession(git_sync_product)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

        # Delegate BaseUrlSession.request to our mock session
        from git_sync.core.SiemplifyApiClient import BaseUrlSession
        monkeypatch.setattr(
            BaseUrlSession,
            "request",
            lambda self, method, url, *args, **kwargs: session.request(
                method, self.create_url(url), *args, **kwargs
            ),
        )

        # Monkeypatch SiemplifyBase.__init__ to set valid local run folder paths
        import sys
        for mod_name in ("SiemplifyBase", "soar_sdk.SiemplifyBase"):
            mod = sys.modules.get(mod_name)
            if mod:
                cls = getattr(mod, "SiemplifyBase", None)
                if cls and not hasattr(cls, "_is_patched_run_folder"):
                    original_init = cls.__init__
                    def new_init(self, *args, **kwargs):
                        original_init(self, *args, **kwargs)
                        self.RUN_FOLDER = "/tmp"
                        self.FILE_SYSTEM_CONTEXT_PATH = "/tmp/context_file.json"
                    cls.__init__ = new_init
                    cls._is_patched_run_folder = True

    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, git_sync_product) -> GitSyncMockSession:
    """Mock the SDK sessions and get it back to view request and response history"""
    session = GitSyncMockSession(git_sync_product)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

        # Delegate BaseUrlSession.request to our mock session
        from git_sync.core.SiemplifyApiClient import BaseUrlSession
        monkeypatch.setattr(
            BaseUrlSession,
            "request",
            lambda self, method, url, *args, **kwargs: session.request(
                method, self.create_url(url), *args, **kwargs
            ),
        )

        # Monkeypatch SiemplifyBase.__init__ to set valid local run folder paths
        import sys
        for mod_name in ("SiemplifyBase", "soar_sdk.SiemplifyBase"):
            mod = sys.modules.get(mod_name)
            if mod:
                cls = getattr(mod, "SiemplifyBase", None)
                if cls and not hasattr(cls, "_is_patched_run_folder"):
                    original_init = cls.__init__
                    def new_init(self, *args, **kwargs):
                        original_init(self, *args, **kwargs)
                        self.RUN_FOLDER = "/tmp"
                        self.FILE_SYSTEM_CONTEXT_PATH = "/tmp/context_file.json"
                    cls.__init__ = new_init
                    cls._is_patched_run_folder = True

    yield session
