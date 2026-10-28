from __future__ import annotations

import importlib.util
import pathlib
import sys

ACTIONS_DIR = pathlib.Path(__file__).parent.parent / "ActionsScripts"
CONNECTORS_DIR = pathlib.Path(__file__).parent.parent / "ConnectorsScripts"
JOBS_DIR = pathlib.Path(__file__).parent.parent / "JobsScrips"


def _load_module_from_path(path: pathlib.Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_action(action_name: str):
    """Load an ActionsScripts/<action_name>.py module fresh for each call.

    Action filenames contain spaces (e.g. "List Entities.py"), so they
    cannot be imported with a normal `import` statement.  A fresh module
    object is returned/loaded every time so that each test gets its own
    `main` without stale module-level state leaking between tests.
    """
    path = ACTIONS_DIR / f"{action_name}.py"
    module_name = "action_under_test_" + "".join(
        ch if ch.isalnum() else "_" for ch in action_name
    )
    return _load_module_from_path(path, module_name)


def load_connector(connector_name: str):
    """Load a ConnectorsScripts/<connector_name>.py module fresh for each call.

    Same rationale as `load_action`: connector filenames contain spaces, and
    a fresh module object avoids state (e.g. `connector_starting_time`)
    leaking between tests.
    """
    path = CONNECTORS_DIR / f"{connector_name}.py"
    module_name = "connector_under_test_" + "".join(
        ch if ch.isalnum() else "_" for ch in connector_name
    )
    return _load_module_from_path(path, module_name)


def load_job(job_name: str):
    """Load a JobsScrips/<job_name>.py module fresh for each call.

    Same rationale as `load_action`/`load_connector`: job filenames contain
    spaces, and a fresh module object avoids state leaking between tests.
    """
    path = JOBS_DIR / f"{job_name}.py"
    module_name = "job_under_test_" + "".join(
        ch if ch.isalnum() else "_" for ch in job_name
    )
    return _load_module_from_path(path, module_name)
