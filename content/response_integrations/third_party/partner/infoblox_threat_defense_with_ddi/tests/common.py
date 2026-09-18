from __future__ import annotations

import importlib
import pathlib
from types import ModuleType

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")

_PACKAGE_NAME = "infoblox_threat_defense_with_ddi"


def load_action(name: str) -> ModuleType:
    """Import an action module by its script name.

    Action filenames contain spaces (e.g. "DNS Record Lookup.py"), which are not
    valid Python identifiers, so they cannot be imported with a normal
    ``from ...actions import X`` statement. ``importlib.import_module`` does not
    validate identifier syntax on the final path component, so it can still load
    them by the literal filename stem.
    """
    return importlib.import_module(f"{_PACKAGE_NAME}.actions.{name}")


def load_connector(name: str) -> ModuleType:
    """Import a connector module by its script name (see ``load_action``).

    TIPCommon's read_ids/write_ids need a live platform-backed DataStreamFactory
    that the connector test harness's SiemplifyConnectorExecution mock doesn't
    provide, so calling them crashes with "'NoneType' object has no attribute
    'read_content'". Connectors import these two names directly into their own
    module namespace (``from TIPCommon.smp_io import read_ids, write_ids``), so
    patching ``TIPCommon.smp_io`` after import has no effect - the module-local
    names must be replaced instead.
    """
    module = importlib.import_module(f"{_PACKAGE_NAME}.connectors.{name}")
    if hasattr(module, "read_ids"):
        module.read_ids = lambda *args, **kwargs: []
    if hasattr(module, "write_ids"):
        module.write_ids = lambda *args, **kwargs: None
    return module
