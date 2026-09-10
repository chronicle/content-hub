from __future__ import annotations

import pathlib
import sys
import types

import pytest
import requests

STUBS_DIR = pathlib.Path(__file__).parent / "stubs"
MANAGERS_DIR = pathlib.Path(__file__).parent.parent / "Managers"
ACTIONS_DIR = pathlib.Path(__file__).parent.parent / "ActionsScripts"
REPO_ROOT = pathlib.Path(__file__).parent.parent

for path in (STUBS_DIR, MANAGERS_DIR, ACTIONS_DIR, REPO_ROOT):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

from SiemplifyAction import SiemplifyAction  # noqa: E402
from tests.core.product import VectraProduct  # noqa: E402
from tests.core.session import MockVectraSession  # noqa: E402

DEFAULT_CONFIG = {
    "API Root": "https://test.vectra.ai",
    "Client ID": "test-client-id",
    "Client Secret": "test-client-secret",
}


@pytest.fixture
def product() -> VectraProduct:
    return VectraProduct()


@pytest.fixture(autouse=True)
def mock_session(monkeypatch: pytest.MonkeyPatch, product: VectraProduct) -> MockVectraSession:
    """Route every `requests` call VectraRUXManager makes to the in-memory mock.

    VectraRUXManager builds its own `requests.session()` for API calls, and
    VectraOAuthAdapter uses the module-level `requests.post` directly for the
    OAuth token endpoint, so both entry points are patched to the same
    MockVectraSession instance/product for a given test.
    """
    session = MockVectraSession(product)
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.setattr(requests, "session", lambda: session)
    monkeypatch.setattr(requests, "post", session.post)
    monkeypatch.setattr(requests, "get", session.get)
    return session


@pytest.fixture
def siemplify() -> SiemplifyAction:
    action = SiemplifyAction()
    action.set_configuration(DEFAULT_CONFIG)
    return action


def run_action(action_module, siemplify_action, parameters):
    """Runs an action module's `main()` with the given parameters against the
    provided (already-configured) SiemplifyAction test double, and returns
    the recorded ActionOutput.

    Action scripts do `from SiemplifyAction import SiemplifyAction`, binding
    the class directly into their own module namespace, so the patch must
    target that name on the already-loaded action module, not the
    `SiemplifyAction` module itself.
    """
    siemplify_action.set_parameters(parameters)

    original = action_module.SiemplifyAction
    action_module.SiemplifyAction = lambda: siemplify_action
    try:
        action_module.main()
    finally:
        action_module.SiemplifyAction = original

    return siemplify_action._output
