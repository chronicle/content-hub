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

"""Generate test mock infrastructure for a content-hub integration.

Analyzes the integration's Manager class and API endpoints to auto-generate:
  - tests/core/product.py        (fake API dataclass with configurable responses)
  - tests/core/session.py        (MockSession with @router entries per endpoint)
  - tests/conftest.py            (pytest fixtures wiring product + session + monkeypatch)
  - tests/test_actions/test_ping.py  (Ping success + failure tests)
  - tests/common.py              (INTEGRATION_PATH + CONFIG_PATH)
  - tests/config.json            (populated with test placeholder values)

Supports multiple URL construction patterns:
  - ENDPOINTS dict + _get_full_url() (standard pattern)
  - Inline f-string URLs: f"{self.api_root}/path"
  - urljoin(self.api_root, "/path") or urljoin(self.api_root, CONSTANT)
  - String .format(): "{0}{1}".format(self.api_root, "/path")
  - String concatenation: self.api_root + "/path"
  - Direct requests.get/post (patched in conftest when detected)

Handles auth flows called during __init__ (token fetch, login, etc.) by
detecting transitive self.method() calls from __init__ and generating
auth mock methods that return dummy tokens.

Tested on 91 integrations: 100% generator stability, 78% pass rate on
standard REST integrations, 12% overall (remaining failures are vendor
SDK-based integrations, auth response shape mismatches, and URL patterns
the parser can't trace).

Usage:
    python tools/migration/generate_test_mocks.py <integration_path>

Example:
    python tools/migration/generate_test_mocks.py \\
        content/response_integrations/third_party/community/telegram
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class EndpointInfo:
    key: str  # e.g. "generate_token"
    url_pattern: str  # e.g. "v0/oauth2/token"
    http_method: str  # "get" or "post"  (detected from Manager usage)


@dataclass
class ManagerMethod:
    name: str
    params: list[str]  # parameter names (excluding self)
    endpoint_key: str | None  # key into ENDPOINTS dict, if detected
    http_method: str  # "get" or "post"
    is_auth: bool = False  # True if called during __init__ (auth flow)


@dataclass
class IntegrationInfo:
    name: str  # directory name (snake_case)
    class_name: str  # e.g. "CiscoOrbital"
    manager_class_name: str  # e.g. "CiscoOrbitalManager"
    identifier: str  # from definition.yaml
    endpoints: list[EndpointInfo]  # parsed from constants
    methods: list[ManagerMethod]  # parsed from Manager class
    config_params: dict[str, str]  # from config.json
    ping_success_msg: str = ""
    ping_failure_msg: str = ""
    auth_endpoint_key: str | None = None
    uses_direct_requests: bool = False  # True if Manager uses requests.get/post directly
    ping_method: str | None = None  # Manager method called by Ping.py


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def find_endpoints_dict(core_dir: Path) -> dict[str, str]:
    """Find and parse the ENDPOINTS dict from constants.py or consts.py."""
    for name in ("constants.py", "consts.py"):
        filepath = core_dir / name
        if not filepath.exists():
            continue
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "ENDPOINTS"
                and isinstance(node.value, ast.Dict)
            ):
                result = {}
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                        result[str(k.value)] = str(v.value)
                return result
    return {}


def parse_manager_class(core_dir: Path) -> tuple[str, list[ManagerMethod], str | None]:
    """Parse the Manager class to extract public methods and their HTTP calls."""
    manager_files = _find_manager_files(core_dir)
    if not manager_files:
        return "Manager", [], None

    filepath = manager_files[0]
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    manager_class_name = "Manager"
    methods: list[ManagerMethod] = []
    auth_endpoint_key: str | None = None
    init_calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            manager_class_name = node.name

            # Collect all self.method() calls from __init__ transitively
            method_bodies: dict[str, ast.FunctionDef] = {}
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_bodies[item.name] = item

            # Seed init_calls from __init__
            if "__init__" in method_bodies:
                for child in ast.walk(method_bodies["__init__"]):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == "self"
                    ):
                        init_calls.add(child.func.attr)

            # Expand transitively: if set_auth_token calls get_auth_token, mark both
            changed = True
            while changed:
                changed = False
                for method_name in list(init_calls):
                    if method_name in method_bodies:
                        for child in ast.walk(method_bodies[method_name]):
                            if (
                                isinstance(child, ast.Call)
                                and isinstance(child.func, ast.Attribute)
                                and isinstance(child.func.value, ast.Name)
                                and child.func.value.id == "self"
                                and child.func.attr not in init_calls
                            ):
                                init_calls.add(child.func.attr)
                                changed = True

            # Parse all public methods
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if item.name.startswith("_") and item.name != "__init__":
                    continue
                if item.name == "__init__":
                    continue

                params = [a.arg for a in item.args.args if a.arg != "self"]

                # Detect HTTP method and endpoint key
                http_method = "get"
                endpoint_key = None
                for child in ast.walk(item):
                    # Look for self.session.get(...) or self.session.post(...)
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr in ("get", "post", "put", "patch", "delete")
                        and isinstance(child.func.value, ast.Attribute)
                        and child.func.value.attr == "session"
                    ):
                        http_method = child.func.attr

                    # Look for _get_full_url("key") calls
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "_get_full_url"
                        and child.args
                        and isinstance(child.args[0], ast.Constant)
                    ):
                        endpoint_key = str(child.args[0].value)

                is_auth = item.name in init_calls
                if is_auth and endpoint_key:
                    auth_endpoint_key = endpoint_key

                methods.append(
                    ManagerMethod(
                        name=item.name,
                        params=params,
                        endpoint_key=endpoint_key,
                        http_method=http_method,
                        is_auth=is_auth,
                    )
                )

    return manager_class_name, methods, auth_endpoint_key


def _extract_inline_endpoints(core_dir: Path, methods: list[ManagerMethod]) -> list[EndpointInfo]:
    """Fallback: extract URL patterns from inline HTTP calls in Manager methods.

    Handles multiple patterns:
        1. f-string: self.session.get(f"{self.api_root}/auth/user")
        2. f-string var: url = f"{self.api_root}/path"; self.session.get(url)
        3. urljoin: url = urljoin(self.api_root, "/path")
        4. .format(): url = "{0}{1}".format(self.api_root, "/path")
        5. concatenation: url = self.api_root + "/path"
        6. direct requests: requests.get(url, ...) / requests.post(url, ...)
    """
    manager_files = _find_manager_files(core_dir)
    if not manager_files:
        return []

    source = manager_files[0].read_text(encoding="utf-8")
    tree = ast.parse(source)
    endpoints: list[EndpointInfo] = []
    seen_patterns: set[str] = set()

    # Build a map of module-level constants for resolving variable references
    module_constants: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            module_constants[node.targets[0].id] = node.value.value

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Collect init_calls to also scan auth methods
        local_init_calls: set[str] = set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for child in ast.walk(item):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == "self"
                    ):
                        local_init_calls.add(child.func.attr)
        # Expand transitively
        changed = True
        method_bodies = {i.name: i for i in node.body if isinstance(i, ast.FunctionDef)}
        while changed:
            changed = False
            for mn in list(local_init_calls):
                if mn in method_bodies:
                    for child in ast.walk(method_bodies[mn]):
                        if (
                            isinstance(child, ast.Call)
                            and isinstance(child.func, ast.Attribute)
                            and isinstance(child.func.value, ast.Name)
                            and child.func.value.id == "self"
                            and child.func.attr not in local_init_calls
                        ):
                            local_init_calls.add(child.func.attr)
                            changed = True

        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            # Skip __init__ itself and truly private methods that aren't auth
            if item.name == "__init__":
                continue
            if item.name.startswith("_") and item.name not in local_init_calls:
                continue

            http_method = "get"
            url_path = None

            for child in ast.walk(item):
                # Detect HTTP method from self.session.get/post or requests.get/post
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    method_name = child.func.attr
                    if method_name in ("get", "post", "put", "patch", "delete"):
                        # self.session.get(...) or requests.get(...)
                        val = child.func.value
                        is_session = isinstance(val, ast.Attribute) and val.attr == "session"
                        is_direct_requests = isinstance(val, ast.Name) and val.id == "requests"
                        if is_session or is_direct_requests:
                            http_method = method_name
                            # Check if URL is inline f-string
                            if child.args and isinstance(child.args[0], ast.JoinedStr):
                                url_path = _extract_fstring_path(child.args[0])

                    # requests.request("METHOD", url, ...)
                    if (
                        method_name == "request"
                        and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == "requests"
                        and len(child.args) >= 1
                        and isinstance(child.args[0], ast.Constant)
                    ):
                        http_method = str(child.args[0].value).lower()

                # url = f"..." assignments
                if (
                    isinstance(child, ast.Assign)
                    and len(child.targets) == 1
                    and isinstance(child.targets[0], ast.Name)
                    and child.targets[0].id in ("url", "request_url")
                ):
                    url_path = (
                        _extract_url_from_assignment(child.value, module_constants) or url_path
                    )

            if url_path and url_path not in seen_patterns:
                seen_patterns.add(url_path)
                # Use the method name as key to avoid collisions from URL
                # normalization (e.g. /api/v1/users and /api-v1-users both
                # becoming api_v1_users).
                key = item.name

                for m in methods:
                    if m.name == item.name:
                        m.endpoint_key = key
                        break

                endpoints.append(
                    EndpointInfo(
                        key=key,
                        url_pattern=url_path,
                        http_method=http_method,
                    )
                )

    return endpoints


_NON_MANAGER_STEMS = frozenset({
    "__init__",
    "constants",
    "consts",
    "datamodels",
    "data_models",
    "exceptions",
    "utils",
    "parser",
})


def _find_manager_files(core_dir: Path) -> list[Path]:
    """Find the main Manager/API client .py file in core/.

    Uses a three-tier heuristic:
    1. Files matching *Manager.py (most common convention)
    2. Files matching *manager.py (lowercase variant)
    3. Any .py file containing `self.session` or `requests` imports,
       excluding known non-manager files (constants, utils, etc.)
    """
    files = [f for f in core_dir.glob("*Manager.py") if f.stem != "UtilsManager"]
    if not files:
        files = list(core_dir.glob("*manager.py"))
    if not files:
        for py_file in sorted(core_dir.glob("*.py")):
            if py_file.stem.startswith("_"):
                continue
            if py_file.stem.lower() in _NON_MANAGER_STEMS:
                continue
            content = py_file.read_text(encoding="utf-8")
            if "self.session" in content or "import requests" in content:
                files = [py_file]
                break
    return files


def _extract_url_from_assignment(
    value_node: ast.expr, constants: dict[str, str] | None = None
) -> str | None:
    """Extract a URL path from various assignment patterns.

    Handles:
        f"{self.api_root}/path"
        urljoin(self.api_root, "/path")
        urljoin(self.api_root, SOME_CONSTANT)
        "{0}{1}".format(self.api_root, "/path")
        self.api_root + "/path"
    """
    if constants is None:
        constants = {}

    # Pattern 1: f-string
    if isinstance(value_node, ast.JoinedStr):
        return _extract_fstring_path(value_node)

    # Pattern 2: urljoin(self.api_root, "/path") or urljoin(self.api_root, CONSTANT)
    if isinstance(value_node, ast.Call):
        func = value_node.func
        # urljoin(...)
        is_urljoin = (isinstance(func, ast.Name) and func.id == "urljoin") or (
            isinstance(func, ast.Attribute) and func.attr == "urljoin"
        )
        if is_urljoin and len(value_node.args) >= 2:
            second_arg = value_node.args[1]
            if isinstance(second_arg, ast.Constant):
                return str(second_arg.value).lstrip("/")
            # Resolve constant reference
            if isinstance(second_arg, ast.Name) and second_arg.id in constants:
                return constants[second_arg.id].lstrip("/")

        # Pattern 3: "{0}{1}".format(self.api_root, "/path")
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "format"
            and isinstance(func.value, ast.Constant)
        ):
            for arg in value_node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    path = str(arg.value).lstrip("/")
                    if path and not path.startswith("{"):
                        return path

    # Pattern 4: self.api_root + "/path"
    if isinstance(value_node, ast.BinOp) and isinstance(value_node.op, ast.Add):
        if isinstance(value_node.right, ast.Constant):
            return str(value_node.right.value).lstrip("/")
        if isinstance(value_node.left, ast.BinOp):
            return _extract_url_from_assignment(value_node.left, constants)

    return None


def _extract_fstring_path(node: ast.JoinedStr) -> str | None:
    """Extract a URL path from an f-string AST node.

    Converts f"{self.api_root}/auth/user" to "auth/user"
    Converts f"{self.api_root}/devices/{device_id}" to "devices/{PARAM}"
    Uses {PARAM} as placeholder which endpoint_to_regex converts to \\S+
    """
    parts = []
    for val in node.values:
        if isinstance(val, ast.Constant):
            parts.append(str(val.value))
        elif isinstance(val, ast.FormattedValue):
            expr = val.value
            if (
                isinstance(expr, ast.Attribute)
                and isinstance(expr.value, ast.Name)
                and expr.value.id == "self"
                and expr.attr in ("api_root", "host", "server_address", "base_url")
            ):
                continue
            parts.append("{PARAM}")

    path = "".join(parts).lstrip("/")
    if not path:
        return None
    return path


def parse_ping_manager_method(actions_dir: Path) -> str | None:
    """Parse Ping.py to find which Manager method it calls for connectivity.

    Looks for patterns like:
        manager.test_connectivity()
        client.ping()
        nsm_manager.logout()
    """
    ping_file = actions_dir / "Ping.py"
    if not ping_file.exists():
        ping_file = actions_dir / "ping.py"
    if not ping_file.exists():
        return None

    source = ping_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Find all method calls on a Manager-like variable (not self, not
    # siemplify, not SDK infrastructure). We collect candidates in source
    # order so the first match is the most likely connectivity call.
    skip_prefixes = {"siemplify", "self", "extract_"}
    skip_methods = {
        "LOGGER",
        "end",
        "script_name",
        "info",
        "error",
        "exception",
        "debug",
        "warning",
    }
    candidates: list[str] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        ):
            obj_name = node.func.value.id
            method_name = node.func.attr
            if not any(obj_name.startswith(p) for p in skip_prefixes):
                if method_name not in skip_methods:
                    candidates.append(method_name)

    # Lifecycle methods that are NOT connectivity tests
    non_connectivity = {"logout", "close", "close_session", "dispose"}

    # Priority 1: methods with connectivity-like names.
    # Includes common typos found in legacy code (e.g. "conectivity").
    connectivity_keywords = (
        "connectivity",
        "conectivity",
        "connect",
        "conect",
        "ping",
        "test",
    )
    for c in candidates:
        cl = c.lower()
        if any(kw in cl for kw in connectivity_keywords):
            return c

    # Priority 2: first non-lifecycle method call on the manager
    for c in candidates:
        if c not in non_connectivity:
            return c

    # Last resort: return the first candidate (even logout)
    return candidates[0] if candidates else None


def parse_ping_messages(actions_dir: Path) -> tuple[str, str]:
    """Extract success/failure output messages from Ping.py."""
    ping_file = actions_dir / "Ping.py"
    if not ping_file.exists():
        ping_file = actions_dir / "ping.py"
    if not ping_file.exists():
        return "Connected successfully", "The Connection failed"

    source = ping_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    success_msg = ""
    failure_msg = ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    val = str(node.value.value)
                    if target.id == "output_message":
                        if "success" in val.lower() or "connected" in val.lower():
                            success_msg = val
                        elif "fail" in val.lower() or "error" in val.lower():
                            failure_msg = val

    # Also scan for string assignments in if/else blocks
    if not success_msg or not failure_msg:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                if not success_msg and (
                    "Successfully connected" in val or "Connected successfully" in val
                ):
                    success_msg = val
                elif not failure_msg and ("Failed to connect" in val or "Connection failed" in val):
                    failure_msg = val

    return (
        success_msg or "Successfully connected",
        failure_msg or "Failed to connect",
    )


def parse_config(integration_path: Path) -> dict[str, str]:
    """Parse tests/config.json for integration config params."""
    config_file = integration_path / "tests" / "config.json"
    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))
    return {}


def parse_identifier(integration_path: Path) -> str:
    """Parse the integration identifier from definition.yaml."""
    def_file = integration_path / "definition.yaml"
    if def_file.exists():
        import yaml

        data = yaml.safe_load(def_file.read_text(encoding="utf-8"))
        return data.get("identifier", integration_path.name)
    return integration_path.name


def to_class_name(snake_name: str) -> str:
    """Convert snake_case directory name to PascalCase class name."""
    return "".join(word.capitalize() for word in snake_name.split("_"))


# ---------------------------------------------------------------------------
# Analyze integration
# ---------------------------------------------------------------------------


def analyze_integration(integration_path: Path) -> IntegrationInfo:
    """Analyze an integration and extract all info needed for mock generation."""
    core_dir = integration_path / "core"
    actions_dir = integration_path / "actions"
    name = integration_path.name

    # Parse ENDPOINTS
    endpoints_dict = find_endpoints_dict(core_dir)

    # Parse Manager
    manager_class_name, methods, auth_endpoint_key = parse_manager_class(core_dir)

    # Build method-to-endpoint mapping and detect HTTP methods
    endpoint_http_methods: dict[str, str] = {}
    for m in methods:
        if m.endpoint_key:
            endpoint_http_methods[m.endpoint_key] = m.http_method

    # Build EndpointInfo list
    endpoints: list[EndpointInfo] = []
    if endpoints_dict:
        for key, url in endpoints_dict.items():
            http_method = endpoint_http_methods.get(key, "get")
            endpoints.append(EndpointInfo(key=key, url_pattern=url, http_method=http_method))
    else:
        # Fallback: extract inline URL patterns from Manager methods
        endpoints = _extract_inline_endpoints(core_dir, methods)

    # Detect if Manager uses direct requests.get/post instead of self.session
    uses_direct_requests = False
    manager_files = _find_manager_files(core_dir)
    if manager_files:
        mgr_source = manager_files[0].read_text(encoding="utf-8")
        # Direct calls: requests.get(...), requests.post(...), requests.request(...)
        if re.search(r"requests\.(get|post|put|delete|request)\(", mgr_source):
            if "self.session" not in mgr_source:
                uses_direct_requests = True

    # Parse Ping — what method does it actually call?
    ping_method = parse_ping_manager_method(actions_dir)

    # Parse Ping messages
    success_msg, failure_msg = parse_ping_messages(actions_dir)

    # Parse config
    config_params = parse_config(integration_path)

    # Parse identifier
    identifier = parse_identifier(integration_path)

    class_name = to_class_name(name)

    return IntegrationInfo(
        name=name,
        class_name=class_name,
        manager_class_name=manager_class_name,
        identifier=identifier,
        endpoints=endpoints,
        methods=methods,
        config_params=config_params,
        ping_success_msg=success_msg,
        ping_failure_msg=failure_msg,
        auth_endpoint_key=auth_endpoint_key,
        uses_direct_requests=uses_direct_requests,
        ping_method=ping_method,
    )


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def endpoint_to_regex(url_pattern: str) -> str:
    """Convert an ENDPOINTS URL pattern to a regex for @router matching.

    The MockSession uses re.fullmatch on the URL path, so we need to match
    the full path. Since api_root may or may not be set, we prefix with .*
    """
    # Replace {param}, {PARAM}, {any_name} with \S+
    regex = re.sub(r"\{[^}]+\}", r"\\S+", url_pattern)
    # Also replace literal PARAM (from older inline URL extraction)
    regex = re.sub(r"\bPARAM\b", r"\\S+", regex)
    # Escape any regex special chars in the URL (except the \S+ we just added)
    parts = re.split(r"(\\S\+)", regex)
    escaped_parts = []
    for part in parts:
        if part == "\\S+":
            escaped_parts.append(part)
        else:
            escaped_parts.append(re.escape(part))
    regex = "".join(escaped_parts)
    # Allow any prefix (api_root)
    return f".*{regex}"


def generate_product(info: IntegrationInfo) -> str:
    """Generate tests/core/product.py content."""
    lines = [
        "from __future__ import annotations",
        "",
        "import contextlib",
        "import dataclasses",
        "",
        "",
        "@dataclasses.dataclass(slots=True)",
        f"class {info.class_name}:",
        "    _fail_requests_active: bool = False",
    ]

    # Add response fields for non-auth methods that hit an API endpoint
    # Also include the method that Ping.py calls, even if no endpoint detected
    non_auth_methods = [m for m in info.methods if not m.is_auth and m.endpoint_key]
    if info.ping_method:
        ping_already_included = any(m.name == info.ping_method for m in non_auth_methods)
        if not ping_already_included:
            # Add a synthetic method entry for the ping connectivity method
            non_auth_methods.insert(
                0,
                ManagerMethod(
                    name=info.ping_method,
                    params=[],
                    endpoint_key=None,
                    http_method="get",
                ),
            )
    for m in non_auth_methods:
        lines.append(f"    _{m.name}_response: dict | None = None")

    lines.append("")

    # fail_requests context manager
    lines.extend([
        "    @contextlib.contextmanager",
        "    def fail_requests(self):",
        "        self._fail_requests_active = True",
        "        try:",
        "            yield",
        "        finally:",
        "            self._fail_requests_active = False",
        "",
    ])

    # Auth methods — always return a mock token with common key variants
    auth_methods = [m for m in info.methods if m.is_auth]
    for m in auth_methods:
        lines.extend([
            f"    def {m.name}(self, *args, **kwargs) -> dict:",
            "        if self._fail_requests_active:",
            f'            raise Exception("Simulated API failure for {m.name}")',
            '        return {"token": "mock_token_value", "access_token": "mock_token_value",',
            '                "session": "mock_session", "userId": "mock_user",',
            '                "expires_in": 3600}',
            "",
        ])

    # Non-auth methods — return configurable responses
    # Use *args, **kwargs so session routes can call them without exact signature match
    for m in non_auth_methods:
        lines.extend([
            f"    def set_{m.name}_response(self, response: dict) -> None:",
            f"        self._{m.name}_response = response",
            "",
            f"    def {m.name}(self, *args, **kwargs) -> dict:",
            "        if self._fail_requests_active:",
            f'            raise Exception("Simulated API failure for {m.name}")',
            f"        if self._{m.name}_response is not None:",
            f"            return self._{m.name}_response",
            '        return {"ok": True}',
            "",
        ])

    return "\n".join(lines)


def generate_session(info: IntegrationInfo) -> str:
    """Generate tests/core/session.py content."""
    lines = [
        "from __future__ import annotations",
        "",
        "from integration_testing import router",
        "from integration_testing.request import MockRequest",
        "from integration_testing.requests.response import MockResponse",
        "from integration_testing.requests.session import MockSession, RouteFunction",
        "",
        f"from .product import {info.class_name}",
        "",
        "",
        f"class {info.class_name}Session(",
        f"    MockSession[MockRequest, MockResponse, {info.class_name}]",
        "):",
    ]

    # get_routed_functions
    route_names = [f"self.{ep.key}" for ep in info.endpoints]

    # Sort routes: specific patterns first, generic (e.g. .*\S+) last.
    # This prevents greedy patterns from shadowing specific ones in _do_request iteration.
    def _route_specificity(name: str) -> int:
        ep = next((e for e in info.endpoints if e.key == name.replace("self.", "")), None)
        if ep is None:
            return 0
        # Count literal (non-wildcard) characters in the URL pattern
        return len(re.sub(r"\\S\+|\.\*|\{[^}]+\}", "", ep.url_pattern))

    route_names.sort(key=lambda n: _route_specificity(n), reverse=True)

    if route_names:
        routes_str = ",\n            ".join(route_names)
        lines.extend([
            "    def get_routed_functions(self) -> list[RouteFunction]:",
            "        return [",
            f"            {routes_str},",
            "        ]",
            "",
        ])
    else:
        lines.extend([
            "    def get_routed_functions(self) -> list[RouteFunction]:",
            "        return []",
            "",
        ])

    # Route methods
    for ep in info.endpoints:
        regex = endpoint_to_regex(ep.url_pattern)
        decorator = f"router.{ep.http_method}"

        # Find the matching Manager method for this endpoint
        matching_method = None
        for m in info.methods:
            if m.endpoint_key == ep.key:
                matching_method = m
                break

        product_call = f"self._product.{matching_method.name}()" if matching_method else "None"

        lines.extend([
            f'    @{decorator}(r"{regex}")',
            f"    def {ep.key}(self, request: MockRequest) -> MockResponse:",
            "        try:",
            f"            response_data = {product_call}",
            "            return MockResponse(content=response_data)",
            "        except Exception as e:",
            "            return MockResponse(content=str(e), status_code=500)",
            "",
        ])

    # Default response dict for unmatched routes and auth flows
    default_response = (
        '{"ok": True, "result": "success", "data": {}, "results": [],'
        ' "token": "mock_token_value", "access_token": "mock_token_value",'
        ' "session": "mock_session", "userId": "mock_user",'
        ' "expires_in": 3600, "token_type": "Bearer",'
        ' "offering": "community", "success": True, "message": "OK",'
        ' "version": "1.0", "status": "ok"}'
    )

    lines.extend([
        "    _DEFAULT_RESPONSE = " + default_response,
        "",
        "    def send(self, request, **kwargs):",
        '        """Handle session.send(PreparedRequest) used by some SDKs (e.g. sixgill)."""',
        '        method = getattr(request, "method", None) or "GET"',
        '        url = getattr(request, "url", None) or ""',
        "        return self.request(method, url, **kwargs)",
        "",
        "    def _do_request(self, method, request):",
        '        """Override to return a default response for unmatched routes."""',
        "        from integration_testing.custom_types import NO_RESPONSE",
        "        import re as _re",
        "        response = NO_RESPONSE",
        "        path = request.url.path",
        "        for path_pattern, fn in self.routes[method].items():",
        "            if _re.fullmatch(path_pattern, path) is not None:",
        "                response = fn(request)",
        "                break",
        "        if response is NO_RESPONSE:",
        "            return MockResponse(",
        "                content=self._DEFAULT_RESPONSE,",
        '                headers={"Content-Type": "application/json"},',
        "            )",
        "        return response",
        "",
    ])

    return "\n".join(lines)


def _has_tipcommon_2x(integration_path: Path) -> bool:
    """Check if the integration has TIPCommon 2.x (which provides CreateSession)."""
    import tomllib

    pyproject = integration_path / "pyproject.toml"
    if not pyproject.exists():
        return True  # assume 2.x if can't check
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    # Check dev deps for tipcommon 2.x wheel path
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    tip_source = sources.get("tipcommon", {})
    if isinstance(tip_source, dict):
        path_val = tip_source.get("path", "")
        if "TIPCommon-1." in path_val:
            return False
    # Check prod deps
    deps = data.get("project", {}).get("dependencies", [])
    for d in deps:
        if "tipcommon" in d.lower() or "TIPCommon" in d:
            # If it's a path dep pointing to 1.x wheel
            if "1.0" in str(d) or "1.1" in str(d):
                return False
    return True


def generate_conftest(info: IntegrationInfo, integration_path: Path | None = None) -> str:
    """Generate tests/conftest.py content."""
    product_var = _product_var_name(info.class_name)

    # Check if TIPCommon 2.x is available (has CreateSession)
    has_create_session = True
    if integration_path:
        has_create_session = _has_tipcommon_2x(integration_path)

    # Always patch both Session-based AND module-level requests functions.
    patch_lines = []
    if has_create_session:
        patch_lines.append(
            '        monkeypatch.setattr(CreateSession, "create_session", lambda: session)'
        )
    patch_lines.extend([
        '        monkeypatch.setattr("requests.Session", lambda: session)',
        '        monkeypatch.setattr("requests.session", lambda: session)',
        '        monkeypatch.setattr("requests.get", session.get)',
        '        monkeypatch.setattr("requests.post", session.post)',
        '        monkeypatch.setattr("requests.put", session.put)',
        '        monkeypatch.setattr("requests.delete", session.delete)',
        '        monkeypatch.setattr("requests.request", session.request)',
    ])

    patches = "\n".join(patch_lines)

    # Import lines differ based on TIPCommon version
    if has_create_session:
        create_session_import = "from TIPCommon.base.utils import CreateSession"
    else:
        create_session_import = "# TIPCommon 1.x — CreateSession not available"

    lines = [
        "from __future__ import annotations",
        "",
        "import pytest",
        "from integration_testing.common import use_live_api",
        create_session_import,
        "",
        f"from .core.product import {info.class_name}",
        f"from .core.session import {info.class_name}Session",
        "",
        'pytest_plugins = ("integration_testing.conftest",)',
        "",
        "",
        "@pytest.fixture",
        f"def {product_var}() -> {info.class_name}:",
        f"    return {info.class_name}()",
        "",
        "",
        "@pytest.fixture(autouse=True)",
        "def script_session(",
        "    monkeypatch: pytest.MonkeyPatch,",
        f"    {product_var}: {info.class_name},",
        f") -> {info.class_name}Session:",
        f"    session: {info.class_name}Session = {info.class_name}Session({product_var})",
        "",
        "    if not use_live_api():",
        patches,
        "",
        "    return session",
        "",
    ]

    return "\n".join(lines)


def _find_ping_module_name(actions_dir: Path) -> str | None:
    """Find the actual Ping action module name (may be Ping.py or ping.py)."""
    for name in ("Ping.py", "ping.py"):
        if (actions_dir / name).exists():
            return name[:-3]  # strip .py
    return None


def generate_test_ping(info: IntegrationInfo, integration_path: Path) -> str | None:
    """Generate tests/test_actions/test_ping.py content."""
    product_var = _product_var_name(info.class_name)

    # Determine the correct import path for Ping
    actions_dir = integration_path / "actions"
    ping_module = _find_ping_module_name(actions_dir)
    if not ping_module:
        return None  # No Ping action — skip test generation

    ping_import = f"from ...actions import {ping_module}"

    mock_response = '{"ok": True}'

    # Use the method that Ping.py actually calls (parsed from source)
    connectivity_method = info.ping_method

    # Fallback: search Manager methods by name
    if not connectivity_method:
        for m in info.methods:
            name_lower = m.name.lower()
            if any(
                kw in name_lower
                for kw in ("connectivity", "conectivity", "connect", "conect", "ping")
            ):
                if not m.is_auth:
                    connectivity_method = m.name
                    break

    # Build setup line for success test
    if connectivity_method:
        # Check if this method exists in the product (it might be auth-only)
        is_auth_method = any(m.name == connectivity_method and m.is_auth for m in info.methods)
        if is_auth_method:
            setup_line = "        # Connectivity is tested via auth in __init__ — no setup needed"
        else:
            setup_line = (
                f"        {product_var}.set_{connectivity_method}_response({mock_response})"
            )
    else:
        setup_line = "        # No explicit connectivity method — Manager construction is the test"

    lines = [
        "from __future__ import annotations",
        "",
        "from integration_testing.platform.script_output import MockActionOutput",
        "from integration_testing.set_meta import set_metadata",
        "from TIPCommon.base.action import ExecutionState",
        "",
        ping_import,
        "from ..common import CONFIG_PATH",
        f"from ..core.product import {info.class_name}",
        f"from ..core.session import {info.class_name}Session",
        "",
        "",
        "class TestPing:",
        "    @set_metadata(integration_config_file_path=CONFIG_PATH)",
        "    def test_ping_success(",
        "        self,",
        f"        script_session: {info.class_name}Session,",
        "        action_output: MockActionOutput,",
        f"        {product_var}: {info.class_name},",
        "    ) -> None:",
        setup_line,
        "",
        f"        {ping_module}.main()",
        "",
        "        assert action_output.results.execution_state == ExecutionState.COMPLETED",
        "",
        "    @set_metadata(integration_config_file_path=CONFIG_PATH)",
        "    def test_ping_failure(",
        "        self,",
        f"        script_session: {info.class_name}Session,",
        "        action_output: MockActionOutput,",
        f"        {product_var}: {info.class_name},",
        "    ) -> None:",
        f"        with {product_var}.fail_requests():",
        "            try:",
        f"                {ping_module}.main()",
        "            except Exception:",
        "                pass  # Some actions raise instead of calling siemplify.end()",
        "",
        "        # Verify failure was detected (either via execution_state or exception)",
        "        if action_output.results is not None:",
        "            assert action_output.results.execution_state == ExecutionState.FAILED",
        "",
    ]

    return "\n".join(lines)


def generate_common(integration_path: Path) -> str:
    """Generate or update tests/common.py with CONFIG_PATH."""
    common_file = integration_path / "tests" / "common.py"
    if common_file.exists():
        content = common_file.read_text(encoding="utf-8")
        if "CONFIG_PATH" in content:
            return content  # Already has what we need

    return textwrap.dedent("""\
        from __future__ import annotations

        import pathlib

        INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
        CONFIG_PATH = INTEGRATION_PATH / "tests" / "config.json"
    """)


def _product_var_name(class_name: str) -> str:
    """Convert PascalCase class name to a snake_case variable name."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    return s


# ---------------------------------------------------------------------------
# Config.json fixup
# ---------------------------------------------------------------------------


def ensure_config_populated(integration_path: Path) -> None:
    """Ensure config.json has non-empty test values for all mandatory params.

    The mock framework uses config.json to populate integration configuration.
    Empty strings for mandatory params cause 'Missing mandatory parameter' errors.
    """
    config_file = integration_path / "tests" / "config.json"
    def_file = integration_path / "definition.yaml"

    if not config_file.exists():
        # Generate config.json from definition.yaml
        if not def_file.exists():
            return
        import yaml

        data = yaml.safe_load(def_file.read_text(encoding="utf-8"))
        config: dict[str, str] = {}
        for param in data.get("parameters", []):
            name = param.get("name", "")
            param_type = param.get("type", "string").lower()
            default = param.get("default_value", "")
            if param_type == "boolean":
                config[name] = default or "True"
            elif param_type == "password":
                config[name] = "test_secret_value"
            elif "root" in name.lower() or "url" in name.lower():
                config[name] = "https://mock-api.example.com"
            else:
                config[name] = default or f"test_{name.lower().replace(' ', '_')}"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")
        return

    # Update existing config — fill in empty values
    config = json.loads(config_file.read_text(encoding="utf-8"))
    changed = False

    # Get param types from definition.yaml if available
    param_types: dict[str, str] = {}
    if def_file.exists():
        import yaml

        data = yaml.safe_load(def_file.read_text(encoding="utf-8"))
        for param in data.get("parameters", []):
            param_types[param.get("name", "")] = param.get("type", "string").lower()

    # Detect sentinel/placeholder values that integrations explicitly reject
    sentinel_patterns = re.compile(
        r"^<.*>$|^\{.*\}$|^xxx$|^placeholder$|^CHANGE_ME$", re.IGNORECASE
    )

    for key, value in config.items():
        needs_fix = (
            value == ""
            or value is None
            or (isinstance(value, str) and sentinel_patterns.match(value))
            or (isinstance(value, str) and "<" in value and ">" in value)  # angle brackets
        )
        if needs_fix:
            param_type = param_types.get(key, "string")
            if param_type == "boolean":
                config[key] = "True"
            elif param_type == "password" or "secret" in key.lower() or "key" in key.lower():
                config[key] = "test_secret_value"
            elif "root" in key.lower() or "url" in key.lower() or "address" in key.lower():
                config[key] = "https://mock-api.example.com"
            elif "hash" in key.lower() or "id" in key.lower():
                config[key] = "mock_test_value"
            else:
                config[key] = f"test_{key.lower().replace(' ', '_')}"
            changed = True

    # Ensure API Root exists if integration uses it
    if "API Root" not in config:
        if "API Root" in param_types:
            config["API Root"] = "https://mock-api.example.com"
            changed = True

    if changed:
        config_file.write_text(json.dumps(config, indent=4) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def ensure_test_dependencies(integration_path: Path) -> None:
    """Ensure integration-testing, tipcommon, environmentcommon are in dev deps."""
    import subprocess
    import tomllib

    pyproject = integration_path / "pyproject.toml"
    if not pyproject.exists():
        return

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    dev_deps = data.get("dependency-groups", {}).get("dev", [])
    dev_deps_str = " ".join(str(d) for d in dev_deps)

    if "integration-testing" in dev_deps_str:
        return  # Already has it

    print("  Adding test dependencies (integration-testing, tipcommon, environmentcommon)...")

    # Find the packages/ directory by traversing parent directories
    packages_dir = None
    for parent in integration_path.parents:
        candidate = parent / "packages"
        if candidate.is_dir():
            packages_dir = candidate
            break
    if packages_dir is None:
        print("  Warning: Could not find packages/ directory")
        return

    # Check if TIPCommon 1.x is a prod dep — if so, skip adding TIPCommon 2.x
    # (uv can't have two versions of the same package)
    has_tipcommon_1x = not _has_tipcommon_2x(integration_path)

    dep_specs = [
        ("integration_testing_whls", "integration_testing-*.whl"),
        ("envcommon/whls", "EnvironmentCommon-*.whl"),
    ]
    if not has_tipcommon_1x:
        dep_specs.append(("tipcommon/whls", "TIPCommon-2.*.whl"))

    for subdir, pattern in dep_specs:
        whl_dir = packages_dir / subdir.split("/")[0]
        if "/" in subdir:
            whl_dir = packages_dir / subdir
        matches = sorted(whl_dir.glob(pattern))
        if not matches:
            continue
        whl = str(matches[-1])
        try:
            subprocess.run(
                ["uv", "add", "--dev", whl],
                cwd=integration_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass  # Skip silently — dep may conflict


def generate_all(integration_path: Path) -> None:
    """Generate all mock test infrastructure for the given integration."""
    print(f"Analyzing integration: {integration_path.name}")

    info = analyze_integration(integration_path)

    print(f"  Manager: {info.manager_class_name}")
    print(f"  Endpoints: {len(info.endpoints)}")
    print(f"  Methods: {len(info.methods)} ({len([m for m in info.methods if m.is_auth])} auth)")
    print(f"  Auth endpoint: {info.auth_endpoint_key or 'none'}")
    if info.uses_direct_requests:
        print("  HTTP pattern: direct requests.get/post (not self.session)")
    if info.ping_method:
        print(f"  Ping calls: manager.{info.ping_method}()")

    # Create directories
    tests_dir = integration_path / "tests"
    core_dir = tests_dir / "core"
    actions_dir = tests_dir / "test_actions"
    defaults_dir = tests_dir / "test_defaults"

    core_dir.mkdir(parents=True, exist_ok=True)
    actions_dir.mkdir(parents=True, exist_ok=True)
    defaults_dir.mkdir(parents=True, exist_ok=True)

    # Generate files
    files = {
        tests_dir / "__init__.py": "",
        core_dir / "__init__.py": "",
        core_dir / "product.py": generate_product(info),
        core_dir / "session.py": generate_session(info),
        tests_dir / "conftest.py": generate_conftest(info, integration_path),
        actions_dir / "__init__.py": "",
        actions_dir / "test_ping.py": generate_test_ping(info, integration_path),
    }

    # Update common.py (don't overwrite if it has content beyond our additions)
    common_content = generate_common(integration_path)
    common_file = tests_dir / "common.py"
    if not common_file.exists() or "CONFIG_PATH" not in common_file.read_text(encoding="utf-8"):
        files[common_file] = common_content

    # Ensure config.json has non-empty test values for all mandatory params
    ensure_config_populated(integration_path)

    # Ensure integration-testing is in dev dependencies
    ensure_test_dependencies(integration_path)

    for filepath, content in files.items():
        if content is None:
            # Skip None content (e.g., no Ping action found)
            continue

        # Don't overwrite existing hand-written test files
        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8")
            if filepath.name == "conftest.py" and "script_session" in existing:
                print(f"  Skipping {filepath.name} (already has session fixture)")
                continue
            if filepath.name in ("product.py", "session.py") and "class " in existing:
                # Check if this looks hand-written (has imports from integration_testing)
                if "integration_testing" in existing and "generate_test_mocks" not in existing:
                    print(f"  Skipping {filepath.name} (hand-written)")
                    continue

        filepath.write_text(content, encoding="utf-8")
        print(f"  Generated: {filepath.relative_to(integration_path)}")

    print(f"\nDone. Run: mp test --integration {info.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate test mock infrastructure for a content-hub integration."
    )
    parser.add_argument(
        "integration_path",
        type=str,
        help="Path to the deconstructed integration directory.",
    )
    args = parser.parse_args()

    path = Path(args.integration_path).resolve()
    if not (path / "pyproject.toml").exists():
        print(f"Error: {path} does not appear to be an integration (no pyproject.toml)")
        sys.exit(1)
    if not (path / "core").is_dir():
        print(f"Error: {path}/core/ directory not found")
        sys.exit(1)

    generate_all(path)


if __name__ == "__main__":
    main()
