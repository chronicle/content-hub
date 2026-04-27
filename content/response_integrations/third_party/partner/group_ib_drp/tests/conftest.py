"""Shared pytest fixtures for the Group-IB DRP integration test suite.

Each ``main()`` in the DRP scripts builds its own poller via
``GIBConnector(siemplify).init_action_poller(...)`` and constructs
``SiemplifyAction()``/``SiemplifyConnectorExecution()``/``SiemplifyJob()``
internally. The fixtures here let individual tests:

- get a ``FakeDRPPoller`` they can program with canned responses and
  inspect for recorded calls,
- get pre-built siemplify stubs (action / connector / job),
- patch the script's module-level ``SiemplifyAction``/``GIBConnector``/etc. without each test having to do its own ``unittest.mock.patch``
  boilerplate.

The structure is modelled after
``content/response_integrations/third_party/community/telegram/tests/conftest.py``: one
fixture per "product" (the fake DRP poller) and one fixture per
"session" (the patched module-level Siemplify entry point).
"""

from __future__ import annotations

import pathlib
import sys
import sysconfig

# The ``soar_sdk`` package ships its top-level modules (``SiemplifyUtils``,
# ``SiemplifyLogger``, ``OverflowManager``, …) inside the ``soar_sdk``
# directory but uses absolute imports against them (``import SiemplifyUtils``).
# When the SOAR runtime executes a script it puts that directory on ``sys.path``
# directly. We replicate that here so ``from soar_sdk.SiemplifyAction import
# SiemplifyAction`` (and the transitive ``import SiemplifyUtils`` inside it)
# resolves cleanly during tests.
_SITE_PACKAGES = pathlib.Path(sysconfig.get_paths()["purelib"])
_SOAR_SDK_DIR = _SITE_PACKAGES / "soar_sdk"
if _SOAR_SDK_DIR.is_dir() and str(_SOAR_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK_DIR))

# The integration directory is named ``group_ib_drp`` and ships an
# ``__init__.py``, so making the parent directory (``partner/``) visible on
# ``sys.path`` lets tests do ``from group_ib_drp.core.UtilsManager import ...``
# without going through ``importlib.util.spec_from_file_location``.
_INTEGRATION_PARENT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_INTEGRATION_PARENT) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_PARENT))

from typing import Callable
from unittest.mock import MagicMock

import pytest

from .common import load_test_config
from .core.poller import FakeDRPPoller
from .core.siemplify_mocks import (
    make_action_siemplify,
    make_connector_siemplify,
    make_job_siemplify,
)


@pytest.fixture
def integration_config() -> dict:
    return load_test_config()


@pytest.fixture
def fake_poller() -> FakeDRPPoller:
    """The DRP API double — analogous to telegram's ``Telegram`` fixture."""
    return FakeDRPPoller()


@pytest.fixture
def action_siemplify_factory(integration_config) -> Callable[..., MagicMock]:
    """Factory that mints ``SiemplifyAction`` doubles with the test config wired in.

    Tests use it like::

        siemplify = action_siemplify_factory(target_entities=[...], security_events=[...])
    """

    def _factory(
        parameters: dict | None = None,
        target_entities: list | None = None,
        security_events: list | None = None,
        config_override: dict | None = None,
    ) -> MagicMock:
        cfg = dict(integration_config)
        if config_override:
            cfg.update(config_override)
        return make_action_siemplify(
            parameters=parameters,
            target_entities=target_entities,
            security_events=security_events,
            integration_config=cfg,
        )

    return _factory


@pytest.fixture
def connector_siemplify_factory(integration_config) -> Callable[..., MagicMock]:
    """Factory minting ``SiemplifyConnectorExecution`` doubles."""

    def _factory(
        parameters: dict | None = None,
        config_override: dict | None = None,
        fetched_timestamp: int | None = None,
        environment: str = "Default Environment",
        is_overflow: bool = False,
    ) -> MagicMock:
        cfg = dict(integration_config)
        if config_override:
            cfg.update(config_override)
        params = dict(parameters or {})
        for k, v in cfg.items():
            params.setdefault(k, v)
        return make_connector_siemplify(
            parameters=params,
            integration_config=cfg,
            fetched_timestamp=fetched_timestamp,
            environment=environment,
            is_overflow=is_overflow,
        )

    return _factory


@pytest.fixture
def job_siemplify_factory() -> Callable[..., MagicMock]:
    """Factory minting ``SiemplifyJob`` doubles for the dedup job tests."""

    def _factory(
        parameters: dict | None = None,
        case_ids: list | None = None,
        cases_by_id: dict[str, dict] | None = None,
    ) -> MagicMock:
        return make_job_siemplify(
            parameters=parameters,
            case_ids=case_ids,
            cases_by_id=cases_by_id,
        )

    return _factory
