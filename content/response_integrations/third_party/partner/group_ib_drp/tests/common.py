"""Shared test helpers for the Group-IB DRP integration test suite.

The DRP scripts have spaces in some filenames (`Get Violation Details.py`,
`URL-Approve.py`, …) which are not valid Python identifiers. This module
provides ``load_script`` to load such modules at test time via
``importlib.util.spec_from_file_location``.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
TESTS_PATH: pathlib.Path = INTEGRATION_PATH / "tests"
CONFIG_PATH: pathlib.Path = TESTS_PATH / "config.json"

ACTIONS_PATH: pathlib.Path = INTEGRATION_PATH / "actions"
CONNECTORS_PATH: pathlib.Path = INTEGRATION_PATH / "connectors"
JOBS_PATH: pathlib.Path = INTEGRATION_PATH / "jobs"

INTEGRATION_PACKAGE: str = INTEGRATION_PATH.name


def load_test_config() -> dict:
    """Read the local config.json used by the test suite."""
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_script(folder: pathlib.Path, filename: str, fake_module_name: str) -> types.ModuleType:
    """Load a script module from a path that may contain spaces or dashes.

    The DRP integration's actions/connectors/jobs are referenced by the
    SOAR runtime by display name, which means filenames such as
    ``Get Violation Details.py`` or ``URL-Approve.py`` are valid in the
    repository but cannot be imported with the ``import`` statement. This
    helper builds a ``ModuleSpec`` from the file path and registers the
    resulting module under ``fake_module_name`` (a valid Python identifier)
    so individual tests can patch attributes on it via
    ``unittest.mock.patch``.

    The script files use relative imports such as ``from ..core.config import
    Config``. To make those resolve correctly the parent package
    (``group_ib_drp``) is registered in ``sys.modules`` as a namespace
    package whose ``__path__`` points at the integration root, and the
    target sub-package (``actions``/``connectors``/``jobs``) is registered
    similarly. This mirrors the layout the SOAR runtime would create when
    it loads the integration as a real package.
    """
    package = INTEGRATION_PACKAGE
    sub_package = folder.name
    sub_pkg_qualname = f"{package}.{sub_package}"
    full_qualname = f"{package}.{sub_package}.{fake_module_name}"

    _ensure_namespace_package(package, INTEGRATION_PATH)
    _ensure_namespace_package(sub_pkg_qualname, folder, parent=package)

    file_path = folder / filename

    spec = importlib.util.spec_from_file_location(
        full_qualname,
        file_path,
        submodule_search_locations=None,
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Could not build spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[full_qualname] = module
    spec.loader.exec_module(module)
    return module


def _ensure_namespace_package(
    qualname: str,
    path: pathlib.Path,
    parent: str | None = None,
) -> types.ModuleType:
    """Register ``qualname`` in ``sys.modules`` as a package rooted at ``path``.

    If the package already exists in ``sys.modules`` with a usable
    ``__path__`` it is reused.
    """
    existing = sys.modules.get(qualname)
    if isinstance(existing, types.ModuleType) and getattr(existing, "__path__", None):
        return existing

    module = types.ModuleType(qualname)
    module.__path__ = [str(path)]
    module.__package__ = qualname
    sys.modules[qualname] = module

    if parent and parent in sys.modules:
        setattr(sys.modules[parent], qualname.rsplit(".", 1)[1], module)

    return module
