"""Speed up local action development without deploying to Google SecOps.

This runner is useful for fast iteration when building or debugging OpenCTI actions:
developers can replay deterministic payloads, validate action outputs,
and troubleshoot integration behavior directly from a local terminal.
It reduces feedback time by avoiding full platform deployment and playbook runs
for each small code change.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import sysconfig
import traceback
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# Capture real stdout before the SOAR SDK is added to sys.path — the SDK
# redirects sys.stdout to an in-memory StringIO buffer at import time.
_real_stdout = sys.stdout

# On the Google SOAR platform environment, SDK modules (e.g. SiemplifyAddressProvider) are
# top-level imports. Locally they're bundled inside `soar_sdk/`, so we add that
# folder to sys.path to replicate the platform's import structure during tests.
_SOAR_SDK = Path(sysconfig.get_path("purelib")) / "soar_sdk"
if _SOAR_SDK.exists() and str(_SOAR_SDK) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK))

INTEGRATION_ROOT = Path(__file__).resolve().parent.parent
if str(INTEGRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_ROOT))

from core.base_action import BaseAction  # noqa: E402

# Override sys.stdout to the real stdout so that print() calls in the SDK
# (e.g. in TIPCommon.base.action) are visible in the console
sys.stdout = _real_stdout


def _discover_actions() -> list[str]:
    """Return PascalCase action names discovered from files in actions/."""
    actions_directory = INTEGRATION_ROOT / "actions"

    action_names: list[str] = []
    for action_file in sorted(actions_directory.glob("*.py")):
        module_name = action_file.stem
        if module_name == "__init__":
            continue
        action_names.append(module_name)

    return action_names


def _pascal_to_snake(action_name: str) -> str:
    """CreateIncident -> create_incident (used to locate the payload file)."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", action_name).lower()


def _pascal_to_human(action_name: str) -> str:
    """CreateIncident -> 'Create Incident' (used to build the script name)."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", action_name)


def _load_payload(action_name: str) -> dict[str, Any]:
    """Load the payload for a given action."""
    payloads_directory = INTEGRATION_ROOT / "dev" / "payloads"
    payload_path = payloads_directory / f"{_pascal_to_snake(action_name)}.json"
    if not payload_path.exists():
        print(
            f"local_action_runner: Payload file not found at {payload_path}. "
            "Using empty payload."
        )
        return {}

    with payload_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Payload in {payload_path} must be a JSON object.")

    return payload


def _build_configuration() -> dict[str, Any]:
    """Build the configuration for the action."""

    opencti_url = os.getenv("OPENCTI_URL")
    opencti_token = os.getenv("OPENCTI_TOKEN")
    verify_ssl = os.getenv("OPENCTI_VERIFY_SSL", "true").lower() == "true"

    if not opencti_url or not opencti_token:
        raise ValueError(
            "OPENCTI_URL and OPENCTI_TOKEN must be set in the environment."
        )

    return {"URL": opencti_url, "API Token": opencti_token, "Verify SSL": verify_ssl}


def _build_stub_soar_action(
    payload: dict[str, Any], configuration: dict[str, Any]
) -> MagicMock:
    """Build a fake SiemplifyAction carrying real payload + configuration data."""
    stub_soar_action = MagicMock()
    stub_soar_action.get_configuration.return_value = configuration

    if payload.get("target_entities"):  # "Enrich" actions
        stub_soar_action.target_entities = [
            MagicMock(**entity) for entity in payload["target_entities"]
        ]

        # TIPCommon entity loop checks execution_deadline_unix_time_ms and
        # expects a numeric value. Test doubles often leave this as MagicMock.
        stub_soar_action.execution_deadline_unix_time_ms = 2**63 - 1
    else:  # "Create" actions
        stub_soar_action.parameters = payload

    return stub_soar_action


def run_action(action_name: str, payload: dict[str, Any]) -> None:
    """Execute run action."""
    configuration = _build_configuration()
    stub_soar_action = _build_stub_soar_action(payload, configuration)

    action_module = importlib.import_module(f"actions.{action_name}")
    action_class = getattr(action_module, action_name)
    script_name = BaseAction.build_script_name(_pascal_to_human(action_name))

    with patch(
        "TIPCommon.base.action.base_action.create_soar_action",
        return_value=stub_soar_action,
    ):
        action = action_class(script_name)
        action.run()
    print(f"local_action_runner: Action '{action_name}' completed.")
    print(f"local_action_runner: output_message: {action.output_message}")
    if action.json_results:
        print(
            "local_action_runner: json_result: "
            f"{json.dumps(action.json_results, indent=2, default=str)}"
        )


def main() -> None:
    """Script entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run a single OpenCTI action locally against a real OpenCTI instance "
            "using convention-based payload examples."
        )
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=_discover_actions(),
        help="Which action to run locally.",
    )
    args = parser.parse_args()

    try:
        payload = _load_payload(args.action)
        run_action(args.action, payload)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"local_action_runner: Runner error: {exc}")
        raise exc
    except (ImportError, AttributeError) as exc:
        print(
            f"local_action_runner: Runner error: unsupported action '{args.action}' ({exc})"
        )
        raise exc


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
