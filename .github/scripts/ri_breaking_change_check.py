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

"""Deterministic breaking-change check for Response Integrations.

For every integration directory touched by a pull request, the script compares
the integration metadata at the PR merge base with the metadata at the PR head
and reports changes that break customers who already use the integration
(playbooks, connectors and jobs configured on the previous version).

Rules that FAIL the check:
    1. An action, connector or job is removed, or its ``name`` changes, or it
       is re-pointed at another integration. The integration ``identifier`` /
       ``name`` in ``definition.yaml`` change, or the integration is removed.
    2. A parameter is removed, becomes mandatory, changes type, or a new
       mandatory parameter *without a default value* is added to an existing
       component / integration.
    3. Top-level keys disappear from an existing action's JSON result example,
       or the example changes between list and object shape.

Rules that only WARN (tuned on a replay of merged PRs so routine changes do
not block): a new mandatory parameter that has a default value, a ``string``
parameter hardened to ``password``, ``default_value`` changed, an option
removed from ``optional_values``, ``script_result_name`` changed, component
files renamed while ``name`` stays the same, an integration moved to another
directory, a result example removed, and files that cannot be parsed.

Escape hatch: failures are downgraded to warnings when the PR carries the
``breaking-change`` label or when a ``release_notes.yaml`` entry added by the
PR is marked ``regressive: true`` (or mentions the word "regressive"/"breaking";
negated forms such as "non-breaking" do not count).

Names (integration identifier/name, component names, parameter names) are
compared exactly, including case and surrounding whitespace, because that is
how the platform matches them when existing content is upgraded.

The script only needs ``git`` and PyYAML. It never talks to the GitHub API,
so it works for pull requests from forks with a read-only token: results are
reported through workflow annotations and ``$GITHUB_STEP_SUMMARY``.

Usage:
    python ri_breaking_change_check.py --base <sha> --head <sha> \\
        [--labels "a,b" | --labels '["a", "b"]'] [--repo-root .] [--summary-file PATH] [--json PATH]
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, Protocol

import yaml

RI_ROOT = "content/response_integrations"
DEFINITION_FILE = "definition.yaml"
RELEASE_NOTES_FILE = "release_notes.yaml"
# ``mp`` loads every ``*.yaml`` below these directories (recursively); ``.yml`` files are not components.
COMPONENT_DIRS: Mapping[str, str] = {"actions": "action", "connectors": "connector", "jobs": "job"}
COMPONENT_SUFFIX = ".yaml"
BREAKING_LABEL = "breaking-change"
# A release note declares a breaking change when its description contains one of these words, unless a negation
# ("non-breaking", "not a breaking change", "no breaking changes") precedes it within the same clause.
BREAKING_WORDS: frozenset[str] = frozenset({"regressive", "breaking"})
NEGATION_WORDS: frozenset[str] = frozenset({
    "no",
    "non",
    "not",
    "nothing",
    "never",
    "without",
    "isn't",
    "aren't",
    "wasn't",
})
NEGATION_WINDOW = 2  # words
_CLAUSE_SPLIT_RE = re.compile(r"[.;:!?()\[\]\n]+")
_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
ENTITY_RESULT_KEY = "EntityResult"
MAX_LISTED_KEYS = 10
# $GITHUB_STEP_SUMMARY is capped at 1 MiB; the table stops after this many rows and says how many were left out.
MAX_SUMMARY_ROWS = 200
# Action parameter types that are the same type on the platform (both map to
# ``ActionParamType`` value 0 in ``packages/mp``), so switching between them
# is not a breaking change.
ACTION_TYPE_ALIASES: Mapping[str, str] = {"integer": "string"}
# Type changes that keep the stored value and only change how the UI shows it
# (hardening an API key from ``string`` to ``password``). Reported as warnings.
COMPATIBLE_TYPE_CHANGES: frozenset[tuple[str, str]] = frozenset({("string", "password")})
# Default values that mean "no default".
EMPTY_DEFAULTS: frozenset[str] = frozenset({"", "null", "none"})

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_NAME_LINE_RE = re.compile(r"^\s*-?\s*name:\s*(?P<value>.+?)\s*$")


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"


class Rule(enum.Enum):
    """Identifier of every check, with the remediation shown to the author."""

    INTEGRATION_REMOVED = ("integration-removed", Severity.ERROR)
    INTEGRATION_IDENTIFIER_CHANGED = ("integration-identifier-changed", Severity.ERROR)
    INTEGRATION_NAME_CHANGED = ("integration-name-changed", Severity.ERROR)
    INTEGRATION_MOVED = ("integration-moved", Severity.WARNING)
    COMPONENT_REMOVED = ("component-removed", Severity.ERROR)
    COMPONENT_NAME_CHANGED = ("component-name-changed", Severity.ERROR)
    COMPONENT_INTEGRATION_CHANGED = ("component-integration-changed", Severity.ERROR)
    COMPONENT_FILE_RENAMED = ("component-file-renamed", Severity.WARNING)
    PARAMETER_REMOVED = ("parameter-removed", Severity.ERROR)
    PARAMETER_MADE_MANDATORY = ("parameter-made-mandatory", Severity.ERROR)
    NEW_MANDATORY_PARAMETER = ("new-mandatory-parameter", Severity.ERROR)
    NEW_MANDATORY_PARAMETER_WITH_DEFAULT = ("new-mandatory-parameter-with-default", Severity.WARNING)
    PARAMETER_TYPE_CHANGED = ("parameter-type-changed", Severity.ERROR)
    PARAMETER_TYPE_MASKED = ("parameter-type-masked", Severity.WARNING)
    DEFAULT_VALUE_CHANGED = ("default-value-changed", Severity.WARNING)
    OPTIONAL_VALUE_REMOVED = ("optional-value-removed", Severity.WARNING)
    RESULT_KEYS_REMOVED = ("result-keys-removed", Severity.ERROR)
    RESULT_SHAPE_CHANGED = ("result-shape-changed", Severity.ERROR)
    RESULT_EXAMPLE_REMOVED = ("result-example-removed", Severity.WARNING)
    SCRIPT_RESULT_NAME_CHANGED = ("script-result-name-changed", Severity.WARNING)
    PARSE_ERROR = ("parse-error", Severity.WARNING)

    def __init__(self, rule_id: str, severity: Severity) -> None:
        self.rule_id = rule_id
        self.severity = severity


FIXES: Mapping[Rule, str] = {
    Rule.INTEGRATION_REMOVED: (
        "Keep the integration. If removing it is intentional, mark the release note `regressive: true` or add the"
        " `breaking-change` label and call it out in the PR description."
    ),
    Rule.INTEGRATION_IDENTIFIER_CHANGED: "Keep the original `identifier`; customers' content is bound to it.",
    Rule.INTEGRATION_NAME_CHANGED: "Keep the original integration `name`.",
    Rule.INTEGRATION_MOVED: "Make sure the move is intentional; the integration identifier is unchanged.",
    Rule.COMPONENT_REMOVED: (
        "Keep the component (it may be marked deprecated in its description). If removing it is intentional, mark"
        " the release note `regressive: true` or add the `breaking-change` label."
    ),
    Rule.COMPONENT_NAME_CHANGED: "Keep the original `name`; existing playbooks reference components by name.",
    Rule.COMPONENT_INTEGRATION_CHANGED: "Keep the original integration identifier on the component.",
    Rule.COMPONENT_FILE_RENAMED: (
        "Prefer keeping the script file name. If the rename is intentional, rename the `.py` consistently and"
        " mention it in the release note."
    ),
    Rule.PARAMETER_REMOVED: (
        "Keep the old parameter and make it optional (`is_mandatory: false`); ignore it in code if it is unused."
    ),
    Rule.PARAMETER_MADE_MANDATORY: "Keep `is_mandatory: false` and validate the value in code, or provide a default.",
    Rule.NEW_MANDATORY_PARAMETER: "Add the new parameter as optional (`is_mandatory: false`) with a `default_value`.",
    Rule.NEW_MANDATORY_PARAMETER_WITH_DEFAULT: (
        "Existing configurations receive the default on upgrade; make sure the default keeps today's behaviour, or"
        " add the parameter as optional."
    ),
    Rule.PARAMETER_TYPE_CHANGED: "Keep the original `type`; add a new parameter if a different type is needed.",
    Rule.PARAMETER_TYPE_MASKED: "Stored values are kept; confirm the parameter is read the same way in code.",
    Rule.DEFAULT_VALUE_CHANGED: (
        "Confirm the new default does not change behaviour for existing playbook steps and mention it in the release"
        " note."
    ),
    Rule.OPTIONAL_VALUE_REMOVED: "Keep accepting the old value, or document the removal in the release note.",
    Rule.RESULT_KEYS_REMOVED: "Keep the old result key alongside the new one (populate both).",
    Rule.RESULT_SHAPE_CHANGED: "Keep the original result shape (list vs object).",
    Rule.RESULT_EXAMPLE_REMOVED: "Keep the JSON result example so playbook designers can still see the result fields.",
    Rule.SCRIPT_RESULT_NAME_CHANGED: "Keep the original `script_result_name` unless no playbook can depend on it.",
    Rule.PARSE_ERROR: "Fix the file so it parses; the check could not compare it.",
}


@dataclasses.dataclass(frozen=True)
class Finding:
    rule: Rule
    integration: str
    component: str
    detail: str
    file: str | None = None
    line: int = 1
    waived_by: str | None = None

    @property
    def severity(self) -> Severity:
        return self.rule.severity

    @property
    def is_blocking(self) -> bool:
        return self.severity is Severity.ERROR and self.waived_by is None

    @property
    def fix(self) -> str:
        return FIXES[self.rule]

    def waived(self, reason: str) -> Finding:
        return dataclasses.replace(self, waived_by=reason)


@dataclasses.dataclass(frozen=True)
class Parameter:
    name: str
    type: str | None
    is_mandatory: bool
    default_value: Any
    optional_values: tuple[str, ...] | None
    line: int = 1


@dataclasses.dataclass(frozen=True)
class ResultExample:
    result_name: str
    path: str | None
    data: Any = None
    error: str | None = None  # "missing" or a parse error message


@dataclasses.dataclass(frozen=True)
class Component:
    kind: str
    file: str
    name: str
    integration_identifier: str | None
    parameters: tuple[Parameter, ...]
    result_examples: tuple[ResultExample, ...] = ()
    script_result_name: str | None = None
    name_line: int = 1

    @property
    def label(self) -> str:
        return f'{self.kind} "{self.name}"'


@dataclasses.dataclass(frozen=True)
class IntegrationSnapshot:
    root: str
    exists: bool
    identifier: str | None = None
    name: str | None = None
    parameters: tuple[Parameter, ...] = ()
    components: tuple[Component, ...] = ()
    release_notes: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[Finding, ...] = ()
    definition_parsed: bool = False
    unparsed_files: frozenset[str] = frozenset()  # component files (relative to root) that could not be parsed

    def components_of(self, kind: str) -> list[Component]:
        return [c for c in self.components if c.kind == kind]


@dataclasses.dataclass
class IntegrationReport:
    base_root: str
    head_root: str
    findings: list[Finding]
    release_note_hatch: str | None = None

    @property
    def root(self) -> str:
        return self.head_root


@dataclasses.dataclass
class CheckResult:
    base: str
    head: str
    merge_base: str
    reports: list[IntegrationReport]
    label_hatch: bool

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.reports for f in r.findings]

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.is_blocking]

    @property
    def exit_code(self) -> int:
        return 1 if self.blocking else 0


# --------------------------------------------------------------------------- #
# Tree access (git or in-memory for tests)
# --------------------------------------------------------------------------- #
class Tree(Protocol):
    """Read-only view of a repository tree at one revision."""

    def list_files(self, prefix: str) -> list[str]: ...

    def read_text(self, path: str) -> str | None: ...


class DictTree:
    """In-memory tree used by the unit tests."""

    def __init__(self, files: Mapping[str, str]) -> None:
        self._files = dict(files)

    def list_files(self, prefix: str) -> list[str]:
        return sorted(p for p in self._files if p.startswith(prefix))

    def read_text(self, path: str) -> str | None:
        return self._files.get(path)


class GitRepo:
    """Thin wrapper around git; blobs are read through one long-lived ``git cat-file --batch`` process."""

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self._batch: subprocess.Popen[bytes] | None = None

    def _git(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(["git", *args], cwd=self.repo_root, capture_output=True, check=False)

    def run(self, *args: str, check: bool = True) -> str:
        proc = self._git(*args)
        if check and proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
        return proc.stdout.decode("utf-8", "replace")

    def rev_exists(self, rev: str) -> bool:
        return self._git("cat-file", "-e", f"{rev}^{{commit}}").returncode == 0

    def merge_base(self, base: str, head: str) -> str | None:
        out = self.run("merge-base", base, head, check=False).strip()
        return out or None

    def changed_files(self, base: str, head: str, prefix: str) -> list[str]:
        # ``-z`` keeps paths verbatim; without it git C-quotes names with spaces, quotes or non-ASCII characters.
        out = self.run("diff", "--no-renames", "--name-only", "-z", base, head, "--", prefix)
        return [path for path in out.split("\0") if path]

    def read_blob(self, rev: str, path: str) -> str | None:
        if self._batch is None or self._batch.poll() is not None:
            self._batch = subprocess.Popen(
                ["git", "cat-file", "--batch"],
                cwd=self.repo_root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        proc = self._batch
        if proc.stdin is None or proc.stdout is None:
            return None
        try:
            proc.stdin.write(f"{rev}:{path}\n".encode())
            proc.stdin.flush()
            header_line = proc.stdout.readline().decode("utf-8", "replace").rstrip("\n")
        except (BrokenPipeError, OSError):
            return None
        # Success: "<oid> <type> <size>". Otherwise git echoes the request followed by " missing" / " ambiguous";
        # the echoed path may itself contain spaces, so parse from the right and validate the size.
        header = header_line.rsplit(None, 2)
        if len(header) != 3 or not header[2].isdigit():
            return None
        _, object_type, size = header
        content = proc.stdout.read(int(size) + 1)[:-1]  # payload is followed by a newline
        if object_type != "blob":
            return None
        return content.decode("utf-8-sig", "replace")

    def close(self) -> None:
        if self._batch is not None and self._batch.poll() is None:
            if self._batch.stdin is not None:
                self._batch.stdin.close()
            self._batch.wait(timeout=10)
        self._batch = None


class GitTree:
    def __init__(self, repo: GitRepo, rev: str) -> None:
        self.repo = repo
        self.rev = rev
        self._listing: dict[str, list[str]] = {}

    def list_files(self, prefix: str) -> list[str]:
        if prefix not in self._listing:
            # A listing of a parent directory (the RI root is listed first) already contains the answer; this
            # keeps a PR that touches hundreds of integrations to one ``ls-tree`` per revision.
            parent = next((p for p in self._listing if prefix.startswith(p)), None)
            if parent is not None:
                self._listing[prefix] = [p for p in self._listing[parent] if p.startswith(prefix)]
            else:
                out = self.repo.run("ls-tree", "-r", "--name-only", "-z", self.rev, "--", prefix, check=False)
                self._listing[prefix] = sorted(p for p in out.split("\0") if p)
        return self._listing[prefix]

    def read_text(self, path: str) -> str | None:
        return self.repo.read_blob(self.rev, path)


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse_yaml(text: str) -> tuple[Any, str | None]:
    """Parse YAML, returning ``(data, error)``; never raises."""
    try:
        return yaml.load(text.lstrip("\ufeff"), Loader=_YAML_LOADER), None
    except Exception as exc:  # any parser failure is reported as a warning, never raised
        return None, f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}".strip()


def parse_json(text: str) -> tuple[Any, str | None]:
    try:
        return json.loads(text.lstrip("\ufeff")), None
    except ValueError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "yes", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def as_name(value: Any) -> str | None:
    """A name/identifier exactly as the platform will see it (no trimming); ``None`` when blank or missing."""
    if value is None or isinstance(value, (Mapping, list)):
        return None
    text = str(value)
    return text if text.strip() else None


def name_lines(text: str) -> dict[str, int]:
    """Map every ``name: <value>`` in the file (value trimmed) to its first line number (1-based)."""
    lines: dict[str, int] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        match = _NAME_LINE_RE.match(line)
        if match:
            value = match.group("value").strip().strip("'\"").strip()
            lines.setdefault(value, number)
    return lines


def parse_parameters(raw: Any, lines: Mapping[str, int]) -> tuple[Parameter, ...]:
    params: list[Parameter] = []
    if not isinstance(raw, list):
        return ()
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = as_name(item.get("name"))
        if not name:
            continue
        optional = item.get("optional_values")
        params.append(
            Parameter(
                name=name,
                type=as_text(item.get("type")),
                is_mandatory=as_bool(item.get("is_mandatory")),
                default_value=item.get("default_value"),
                optional_values=tuple(str(v) for v in optional) if isinstance(optional, list) else None,
                line=lines.get(name.strip(), 1),
            )
        )
    return tuple(params)


def parse_component(kind: str, path: str, text: str, tree: Tree, root: str) -> tuple[Component | None, str | None]:
    data, error = parse_yaml(text)
    if error:
        return None, error
    if not isinstance(data, Mapping):
        return None, "component YAML is not a mapping"
    name = as_name(data.get("name"))
    if not name:
        return None, "component YAML has no `name`"
    lines = name_lines(text)
    integration_identifier = as_name(data.get("integration_identifier") or data.get("integration"))
    results: list[ResultExample] = []
    if kind == "action":
        results = load_result_examples(data.get("dynamic_results_metadata"), tree, root)
    return (
        Component(
            kind=kind,
            file=path,
            name=name,
            integration_identifier=integration_identifier,
            parameters=parse_parameters(data.get("parameters"), lines),
            result_examples=tuple(results),
            script_result_name=as_text(data.get("script_result_name")),
            name_line=lines.get(name.strip(), 1),
        ),
        None,
    )


def load_result_examples(raw: Any, tree: Tree, root: str) -> list[ResultExample]:
    results: list[ResultExample] = []
    if not isinstance(raw, list):
        return results
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        result_name = as_text(item.get("result_name")) or "JsonResult"
        rel_path = as_text(item.get("result_example_path"))
        if not rel_path:
            results.append(ResultExample(result_name=result_name, path=None, error="missing"))
            continue
        path = str(PurePosixPath(root) / rel_path)
        text = tree.read_text(path)
        if text is None:
            results.append(ResultExample(result_name=result_name, path=path, error="missing"))
            continue
        data, error = parse_json(text)
        results.append(ResultExample(result_name=result_name, path=path, data=data, error=error))
    return results


def load_snapshot(tree: Tree, root: str) -> IntegrationSnapshot:
    """Load everything the check needs about one integration at one revision."""
    files = tree.list_files(root.rstrip("/") + "/")
    definition_path = f"{root}/{DEFINITION_FILE}"
    definition_text = tree.read_text(definition_path) if definition_path in files else None
    if definition_text is None:
        return IntegrationSnapshot(root=root, exists=False)

    warnings: list[Finding] = []
    definition, error = parse_yaml(definition_text)
    identifier = name = None
    parameters: tuple[Parameter, ...] = ()
    definition_parsed = not error and isinstance(definition, Mapping)
    if not definition_parsed:
        warnings.append(
            Finding(
                Rule.PARSE_ERROR,
                root,
                "integration",
                f"`{DEFINITION_FILE}` could not be parsed ({error or 'not a mapping'}).",
                file=definition_path,
            )
        )
    else:
        identifier = as_name(definition.get("identifier"))
        name = as_name(definition.get("name"))
        parameters = parse_parameters(definition.get("parameters"), name_lines(definition_text))

    components: list[Component] = []
    unparsed: set[str] = set()
    for path in files:
        relative = PurePosixPath(path).relative_to(root)
        if len(relative.parts) < 2 or relative.suffix != COMPONENT_SUFFIX:
            continue
        kind = COMPONENT_DIRS.get(relative.parts[0])
        if kind is None:
            continue
        text = tree.read_text(path)
        if text is None:
            continue
        component, error = parse_component(kind, path, text, tree, root)
        if component is None:
            unparsed.add(str(relative))
            warnings.append(
                Finding(Rule.PARSE_ERROR, root, f"{kind} file `{relative}`", f"Skipped: {error}.", file=path)
            )
            continue
        components.append(component)

    notes: tuple[Mapping[str, Any], ...] = ()
    notes_path = f"{root}/{RELEASE_NOTES_FILE}"
    notes_text = tree.read_text(notes_path) if notes_path in files else None
    if notes_text is not None:
        parsed, error = parse_yaml(notes_text)
        if isinstance(parsed, list):
            notes = tuple(n for n in parsed if isinstance(n, Mapping))
        elif error:
            warnings.append(
                Finding(
                    Rule.PARSE_ERROR,
                    root,
                    "release notes",
                    f"`{RELEASE_NOTES_FILE}` could not be parsed ({error}).",
                    file=notes_path,
                )
            )

    return IntegrationSnapshot(
        root=root,
        exists=True,
        identifier=identifier,
        name=name,
        parameters=parameters,
        components=tuple(components),
        release_notes=notes,
        warnings=tuple(warnings),
        definition_parsed=definition_parsed,
        unparsed_files=frozenset(unparsed),
    )


# --------------------------------------------------------------------------- #
# Locating integrations
# --------------------------------------------------------------------------- #
def integration_roots(files: Iterable[str]) -> set[str]:
    """Every directory that contains a ``definition.yaml`` under the RI root."""
    roots: set[str] = set()
    for path in files:
        pure = PurePosixPath(path)
        if pure.name == DEFINITION_FILE and str(pure).startswith(RI_ROOT + "/"):
            roots.add(str(pure.parent))
    return roots


def root_for_path(path: str, roots: set[str]) -> str | None:
    """The innermost integration root that contains ``path``."""
    current = PurePosixPath(path).parent
    while str(current) not in {".", ""}:
        if str(current) in roots:
            return str(current)
        current = current.parent
    return None


def touched_integrations(changed_files: Iterable[str], base_tree: Tree, head_tree: Tree) -> list[str]:
    roots = integration_roots(base_tree.list_files(RI_ROOT + "/")) | integration_roots(
        head_tree.list_files(RI_ROOT + "/")
    )
    touched = {root for path in changed_files if (root := root_for_path(path, roots)) is not None}
    return sorted(touched)


# --------------------------------------------------------------------------- #
# Comparison (pure functions)
# --------------------------------------------------------------------------- #
def normalize_type(kind: str, value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if kind == "action":
        normalized = ACTION_TYPE_ALIASES.get(normalized, normalized)
    return normalized


def normalize_scalar(value: Any) -> str:
    """Compare default values loosely.

    ``'True'``/``true``, ``4``/``'4'``/``4.0``, whitespace variants and the
    "no default" spellings (``null``, ``''``, missing) are all considered equal.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).casefold()
    text = " ".join(str(value).split()).casefold()
    if text in EMPTY_DEFAULTS:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else repr(number)


def has_default(value: Any) -> bool:
    return normalize_scalar(value) != ""


def display(value: Any) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= 60 else text[:57] + "..."


def name_hint(name: str, candidates: Iterable[str]) -> str:
    """Explain a near miss when ``name`` differs from a candidate only by case or surrounding whitespace."""
    for candidate in candidates:
        if candidate != name and candidate.strip().casefold() == name.strip().casefold():
            return f" Found `{candidate}` instead; names must match exactly (case and surrounding whitespace)."
    return ""


def compare_parameters(
    base_params: Sequence[Parameter],
    head_params: Sequence[Parameter],
    *,
    kind: str,
    integration: str,
    component: str,
    file: str | None,
) -> list[Finding]:
    findings: list[Finding] = []
    base_by_name = {p.name: p for p in base_params}
    head_by_name = {p.name: p for p in head_params}

    for name, base_param in base_by_name.items():
        head_param = head_by_name.get(name)
        if head_param is None:
            hint = name_hint(name, head_by_name)
            findings.append(
                Finding(
                    Rule.PARAMETER_REMOVED, integration, component, f"Parameter `{name}` was removed.{hint}", file=file
                )
            )
            continue
        line = head_param.line
        if not base_param.is_mandatory and head_param.is_mandatory:
            findings.append(
                Finding(
                    Rule.PARAMETER_MADE_MANDATORY,
                    integration,
                    component,
                    f"Parameter `{name}` changed from optional to mandatory.",
                    file=file,
                    line=line,
                )
            )
        base_type, head_type = normalize_type(kind, base_param.type), normalize_type(kind, head_param.type)
        if base_type is not None and head_type is not None and base_type != head_type:
            compatible = (base_type, head_type) in COMPATIBLE_TYPE_CHANGES
            findings.append(
                Finding(
                    Rule.PARAMETER_TYPE_MASKED if compatible else Rule.PARAMETER_TYPE_CHANGED,
                    integration,
                    component,
                    f"Parameter `{name}` type changed from `{base_param.type}` to `{head_param.type}`.",
                    file=file,
                    line=line,
                )
            )
        if normalize_scalar(base_param.default_value) != normalize_scalar(head_param.default_value):
            findings.append(
                Finding(
                    Rule.DEFAULT_VALUE_CHANGED,
                    integration,
                    component,
                    f"Parameter `{name}` default changed from `{display(base_param.default_value)}` to"
                    f" `{display(head_param.default_value)}`.",
                    file=file,
                    line=line,
                )
            )
        if base_param.optional_values and head_param.optional_values is not None:
            removed = [v for v in base_param.optional_values if v not in head_param.optional_values]
            if removed:
                findings.append(
                    Finding(
                        Rule.OPTIONAL_VALUE_REMOVED,
                        integration,
                        component,
                        f"Parameter `{name}` no longer offers option(s): {', '.join(f'`{v}`' for v in removed)}.",
                        file=file,
                        line=line,
                    )
                )

    for name, head_param in head_by_name.items():
        if name in base_by_name or not head_param.is_mandatory:
            continue
        if has_default(head_param.default_value):
            findings.append(
                Finding(
                    Rule.NEW_MANDATORY_PARAMETER_WITH_DEFAULT,
                    integration,
                    component,
                    f"New mandatory parameter `{name}` (default `{display(head_param.default_value)}`).",
                    file=file,
                    line=head_param.line,
                )
            )
        else:
            findings.append(
                Finding(
                    Rule.NEW_MANDATORY_PARAMETER,
                    integration,
                    component,
                    f"New parameter `{name}` is mandatory and has no default; existing configurations have no value"
                    " for it.",
                    file=file,
                    line=head_param.line,
                )
            )
    return findings


def result_shape(data: Any) -> tuple[str, frozenset[str]]:
    """Classify a JSON result example and collect its top-level keys.

    Lists are treated as the union of their items' keys. Items shaped like
    ``{"Entity": ..., "EntityResult": {...}}`` contribute the keys inside
    ``EntityResult`` instead, so entity enrichment results are compared by the
    fields customers actually read.
    """
    if isinstance(data, list):
        shape, items = "list", data
    elif isinstance(data, Mapping):
        shape, items = "object", [data]
    else:
        return "scalar", frozenset()
    keys: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        inner = item.get(ENTITY_RESULT_KEY)
        if ENTITY_RESULT_KEY in item and isinstance(inner, (Mapping, list)):
            _, inner_keys = result_shape(inner)
            keys.update(inner_keys)
        else:
            keys.update(str(k) for k in item)
    return shape, frozenset(keys)


def is_empty_example(data: Any) -> bool:
    """``{}`` / ``[]`` placeholders mean "no example" (``mp`` treats ``{}`` the same way): nothing to lose."""
    return isinstance(data, (Mapping, list)) and len(data) == 0


def compare_result_examples(base: Component, head: Component, *, integration: str) -> list[Finding]:
    findings: list[Finding] = []
    head_by_name = {r.result_name: r for r in head.result_examples}
    for base_result in base.result_examples:
        if base_result.error or base_result.data is None or is_empty_example(base_result.data):
            continue  # nothing reliable to compare against
        head_result = head_by_name.get(base_result.result_name)
        if head_result is None or head_result.error == "missing":
            findings.append(
                Finding(
                    Rule.RESULT_EXAMPLE_REMOVED,
                    integration,
                    base.label,
                    f"Result example `{base_result.result_name}` ({base_result.path}) is no longer present.",
                    file=head.file,
                    line=head.name_line,
                )
            )
            continue
        if head_result.error:
            findings.append(
                Finding(
                    Rule.PARSE_ERROR,
                    integration,
                    base.label,
                    f"Result example `{head_result.path}` could not be parsed ({head_result.error}).",
                    file=head_result.path,
                )
            )
            continue
        base_shape, base_keys = result_shape(base_result.data)
        head_shape, head_keys = result_shape(head_result.data)
        if base_shape != head_shape and {base_shape, head_shape} <= {"list", "object"}:
            findings.append(
                Finding(
                    Rule.RESULT_SHAPE_CHANGED,
                    integration,
                    base.label,
                    f"Result example `{base_result.result_name}` changed from {base_shape} to {head_shape}.",
                    file=head_result.path,
                )
            )
            continue
        removed = sorted(base_keys - head_keys)
        if removed:
            listed = ", ".join(f"`{k}`" for k in removed[:MAX_LISTED_KEYS])
            more = f" (+{len(removed) - MAX_LISTED_KEYS} more)" if len(removed) > MAX_LISTED_KEYS else ""
            findings.append(
                Finding(
                    Rule.RESULT_KEYS_REMOVED,
                    integration,
                    base.label,
                    f"Result example `{base_result.result_name}` lost top-level key(s): {listed}{more}.",
                    file=head_result.path,
                )
            )
    return findings


def match_components(
    base: IntegrationSnapshot, head: IntegrationSnapshot, kind: str
) -> tuple[list[tuple[Component, Component]], list[Finding]]:
    """Pair base components with their head counterparts (by ``name``, then by file) and report the unmatched."""
    integration = head.root
    pairs: list[tuple[Component, Component]] = []
    findings: list[Finding] = []
    head_components = head.components_of(kind)
    head_by_name = {c.name: c for c in head_components}
    head_by_file = {_relative_file(c, head.root): c for c in head_components}
    base_names = {c.name for c in base.components_of(kind)}
    renamed_files: list[str] = []

    for base_component in base.components_of(kind):
        relative_file = _relative_file(base_component, base.root)
        head_component = head_by_name.get(base_component.name)
        if head_component is not None:
            if _relative_file(head_component, head.root) != relative_file:
                renamed_files.append(f"`{relative_file}` -> `{_relative_file(head_component, head.root)}`")
            pairs.append((base_component, head_component))
            continue
        if relative_file in head.unparsed_files:
            continue  # the file is still there but broken; the parse-error warning already covers it
        same_file = head_by_file.get(relative_file)
        if same_file is not None and same_file.name not in base_names:
            hint = name_hint(base_component.name, [same_file.name])
            findings.append(
                Finding(
                    Rule.COMPONENT_NAME_CHANGED,
                    integration,
                    base_component.label,
                    f"`name` changed from `{base_component.name}` to `{same_file.name}` in `{same_file.file}`.{hint}",
                    file=same_file.file,
                    line=same_file.name_line,
                )
            )
            pairs.append((base_component, same_file))
        else:
            hint = name_hint(base_component.name, head_by_name)
            findings.append(
                Finding(
                    Rule.COMPONENT_REMOVED,
                    integration,
                    base_component.label,
                    f"`{base_component.file}` was removed.{hint}",
                    file=base_component.file,
                )
            )
    if renamed_files:
        listed = ", ".join(renamed_files[:MAX_LISTED_KEYS])
        more = f" (+{len(renamed_files) - MAX_LISTED_KEYS} more)" if len(renamed_files) > MAX_LISTED_KEYS else ""
        findings.append(
            Finding(
                Rule.COMPONENT_FILE_RENAMED,
                integration,
                f"{len(renamed_files)} {kind} file(s)",
                f"Renamed while `name` stayed the same: {listed}{more}.",
                file=f"{head.root}/{DEFINITION_FILE}",
            )
        )
    return pairs, findings


def compare_component_pair(
    base_component: Component, head_component: Component, *, kind: str, head: IntegrationSnapshot
) -> list[Finding]:
    """Findings for one component that exists in both revisions."""
    integration = head.root
    findings: list[Finding] = []
    base_link, head_link = base_component.integration_identifier, head_component.integration_identifier
    # A component may only point at its own integration. Fixing a wrong link so it matches the
    # integration identifier is not a break; pointing it somewhere else is.
    if base_link and head_link and base_link != head_link and head_link != (head.identifier or head_link):
        findings.append(
            Finding(
                Rule.COMPONENT_INTEGRATION_CHANGED,
                integration,
                base_component.label,
                f"Integration identifier changed from `{base_link}` to `{head_link}`"
                f" (the integration's identifier is `{head.identifier}`).",
                file=head_component.file,
                line=head_component.name_line,
            )
        )
    findings.extend(
        compare_parameters(
            base_component.parameters,
            head_component.parameters,
            kind=kind,
            integration=integration,
            component=base_component.label,
            file=head_component.file,
        )
    )
    if kind != "action":
        return findings
    findings.extend(compare_result_examples(base_component, head_component, integration=integration))
    base_result_name, head_result_name = base_component.script_result_name, head_component.script_result_name
    if base_result_name and head_result_name and base_result_name != head_result_name:
        findings.append(
            Finding(
                Rule.SCRIPT_RESULT_NAME_CHANGED,
                integration,
                base_component.label,
                f"`script_result_name` changed from `{base_result_name}` to `{head_result_name}`.",
                file=head_component.file,
                line=head_component.name_line,
            )
        )
    return findings


def compare_components(base: IntegrationSnapshot, head: IntegrationSnapshot) -> list[Finding]:
    findings: list[Finding] = []
    for kind in COMPONENT_DIRS.values():
        pairs, unmatched = match_components(base, head, kind)
        findings.extend(unmatched)
        for base_component, head_component in pairs:
            findings.extend(compare_component_pair(base_component, head_component, kind=kind, head=head))
    return findings


def _relative_file(component: Component, root: str) -> str:
    return str(PurePosixPath(component.file).relative_to(root))


def compare_integrations(base: IntegrationSnapshot, head: IntegrationSnapshot) -> list[Finding]:
    """All findings for one integration; ``base``/``head`` may live at different roots when moved."""
    if not base.exists:
        return list(head.warnings)  # brand-new integration: nothing can break
    if not head.exists:
        return [
            Finding(
                Rule.INTEGRATION_REMOVED,
                base.root,
                "integration",
                f"`{base.root}` no longer contains a `{DEFINITION_FILE}`.",
                file=f"{base.root}/{DEFINITION_FILE}",
            )
        ]
    findings: list[Finding] = list(head.warnings)
    integration = head.root
    definition_file = f"{integration}/{DEFINITION_FILE}"
    if base.root != head.root:
        findings.append(
            Finding(
                Rule.INTEGRATION_MOVED,
                integration,
                "integration",
                f"Integration moved from `{base.root}` to `{head.root}`.",
                file=definition_file,
            )
        )
    if base.identifier and head.identifier and base.identifier != head.identifier:
        findings.append(
            Finding(
                Rule.INTEGRATION_IDENTIFIER_CHANGED,
                integration,
                "integration",
                f"`identifier` changed from `{base.identifier}` to `{head.identifier}`.",
                file=definition_file,
            )
        )
    if base.name and head.name and base.name != head.name:
        findings.append(
            Finding(
                Rule.INTEGRATION_NAME_CHANGED,
                integration,
                "integration",
                f"`name` changed from `{base.name}` to `{head.name}`.",
                file=definition_file,
            )
        )
    if base.definition_parsed and head.definition_parsed:
        findings.extend(
            compare_parameters(
                base.parameters,
                head.parameters,
                kind="integration",
                integration=integration,
                component="integration",
                file=definition_file,
            )
        )
    findings.extend(compare_components(base, head))
    return findings


# --------------------------------------------------------------------------- #
# Escape hatches
# --------------------------------------------------------------------------- #
def has_breaking_label(labels: Iterable[str]) -> bool:
    return any(label.strip().casefold() == BREAKING_LABEL for label in labels)


def parse_labels(raw: str | None) -> list[str]:
    """Labels from a JSON list (``toJSON(github.event.pull_request.labels.*.name)``) or a comma-separated string."""
    if not raw or not raw.strip():
        return []
    if raw.lstrip().startswith("["):
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            return [str(label).strip() for label in parsed if str(label).strip()]
    return [part.strip() for part in raw.split(",") if part.strip()]


def mentions_breaking_change(description: str) -> bool:
    """``True`` when "regressive"/"breaking" occurs as a whole word that is not negated within its clause.

    "groundbreaking" and "unbreakingly" are different words; "non-breaking", "not a breaking change" and
    "no breaking changes" are negated. Sentence punctuation resets the negation window.
    """
    for clause in _CLAUSE_SPLIT_RE.split(description.casefold()):
        words = _WORD_RE.findall(clause)
        for index, word in enumerate(words):
            if word in BREAKING_WORDS and not NEGATION_WORDS & set(words[max(0, index - NEGATION_WINDOW) : index]):
                return True
    return False


def release_note_hatch(
    base_notes: Sequence[Mapping[str, Any]],
    head_notes: Sequence[Mapping[str, Any]],
) -> str | None:
    """Description of a release note added by the PR that declares a breaking change, else ``None``."""
    base_keys = {_note_key(n) for n in base_notes}
    added = [n for n in head_notes if _note_key(n) not in base_keys]
    for note in reversed(added):  # newest entries are appended last
        description = str(note.get("description") or "")
        if as_bool(note.get("regressive")) or mentions_breaking_change(description):
            return description.strip() or "regressive: true"
    return None


def _note_key(note: Mapping[str, Any]) -> str:
    """Identity of a release note; a PR that edits the description or the ``regressive`` flag "adds" a note."""
    keys = ("description", "version", "integration_version", "item_name", "publish_time", "regressive")
    return json.dumps({k: note.get(k) for k in keys}, sort_keys=True, default=str)


def apply_hatches(reports: list[IntegrationReport], *, label_hatch: bool) -> None:
    for report in reports:
        reason = None
        if label_hatch:
            reason = f"label `{BREAKING_LABEL}`"
        elif report.release_note_hatch:
            reason = "release note marked regressive"
        if reason:
            report.findings = [f.waived(reason) if f.severity is Severity.ERROR else f for f in report.findings]


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def pair_integrations(
    roots: Sequence[str], base_tree: Tree, head_tree: Tree
) -> list[tuple[IntegrationSnapshot, IntegrationSnapshot]]:
    """Load base/head snapshots and pair moved integrations by identifier."""
    pairs: list[tuple[IntegrationSnapshot, IntegrationSnapshot]] = []
    removed: list[IntegrationSnapshot] = []
    added: list[IntegrationSnapshot] = []
    for root in roots:
        base, head = load_snapshot(base_tree, root), load_snapshot(head_tree, root)
        if base.exists and not head.exists:
            removed.append(base)
        elif head.exists and not base.exists:
            added.append(head)
        else:
            pairs.append((base, head))
    for base in removed:
        match = next((h for h in added if h.identifier and h.identifier == base.identifier), None)
        if match is not None:
            added.remove(match)
            pairs.append((base, match))
        else:
            pairs.append((base, IntegrationSnapshot(root=base.root, exists=False)))
    pairs.extend((IntegrationSnapshot(root=head.root, exists=False), head) for head in added)
    return sorted(pairs, key=lambda pair: pair[1].root)


def run_check(
    changed_files: Iterable[str],
    base_tree: Tree,
    head_tree: Tree,
    *,
    labels: Iterable[str],
    base: str = "",
    head: str = "",
    merge_base: str = "",
) -> CheckResult:
    roots = touched_integrations(changed_files, base_tree, head_tree)
    reports: list[IntegrationReport] = []
    for base_snapshot, head_snapshot in pair_integrations(roots, base_tree, head_tree):
        reports.append(
            IntegrationReport(
                base_root=base_snapshot.root,
                head_root=head_snapshot.root,
                findings=compare_integrations(base_snapshot, head_snapshot),
                release_note_hatch=release_note_hatch(base_snapshot.release_notes, head_snapshot.release_notes),
            )
        )
    label_hatch = has_breaking_label(labels)
    apply_hatches(reports, label_hatch=label_hatch)
    return CheckResult(base=base, head=head, merge_base=merge_base, reports=reports, label_hatch=label_hatch)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    return _escape_data(text).replace(":", "%3A").replace(",", "%2C")


def annotation(finding: Finding) -> str:
    level = "error" if finding.is_blocking else "warning"
    title = f"Breaking change: {finding.rule.rule_id}" if finding.severity is Severity.ERROR else finding.rule.rule_id
    if finding.waived_by:
        title += f" (waived by {finding.waived_by})"
    properties = [f"title={_escape_property(title)}"]
    if finding.file:
        properties.insert(0, f"file={_escape_property(finding.file)},line={max(finding.line, 1)}")
    message = f"{finding.component}: {finding.detail} Fix: {finding.fix}"
    return f"::{level} {','.join(properties)}::{_escape_data(message)}"


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _verdict_line(result: CheckResult) -> str:
    blocking = len(result.blocking)
    waived = [f for f in result.findings if f.severity is Severity.ERROR and f.waived_by]
    warnings = sum(1 for f in result.findings if f.severity is Severity.WARNING)
    if blocking:
        return f"**Result: FAIL** - {blocking} breaking change(s), {warnings} warning(s)."
    if waived:
        return (
            f"**Result: PASS with waived breaking changes** - {len(waived)} breaking change(s) waived by"
            f" {waived[0].waived_by}, {warnings} warning(s)."
        )
    if warnings:
        return f"**Result: PASS** - no breaking changes, {warnings} warning(s)."
    return "**Result: PASS** - no breaking changes detected."


def _severity_cell(finding: Finding) -> str:
    if finding.is_blocking:
        return "FAIL"
    if finding.waived_by:
        return f"waived ({finding.waived_by})"
    return "warning"


def sorted_findings(result: CheckResult) -> list[Finding]:
    """Blocking findings first (GitHub shows at most 10 annotations per severity per step), then stable order."""
    return sorted(result.findings, key=lambda f: (not f.is_blocking, f.integration, f.component, f.rule.rule_id))


def summary_markdown(result: CheckResult) -> str:
    lines = ["## Response Integrations breaking-change check", "", _verdict_line(result)]
    if result.label_hatch:
        lines.append(f"- Escape hatch: PR label `{BREAKING_LABEL}` is set; failures are reported as warnings.")
    else:
        for report in result.reports:
            if report.release_note_hatch:
                note = _md(display(report.release_note_hatch))
                lines.append(f"- Escape hatch: `{report.root}` release note declares a breaking change: _{note}_")
    lines.append("")
    if result.reports:
        lines.append("Integrations compared: " + ", ".join(f"`{r.root}`" for r in result.reports))
    else:
        lines.append("No integration directories were touched by this change.")
    lines.append("")
    if result.findings:
        lines += [
            "| Integration | Component | Rule | Severity | Detail | How to fix |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        findings = sorted_findings(result)
        for finding in findings[:MAX_SUMMARY_ROWS]:
            cells = (
                f"`{_md(PurePosixPath(finding.integration).name)}`",
                _md(finding.component),
                f"`{finding.rule.rule_id}`",
                _md(_severity_cell(finding)),
                _md(finding.detail),
                _md(finding.fix),
            )
            lines.append("| " + " | ".join(cells) + " |")
        if len(findings) > MAX_SUMMARY_ROWS:
            lines += ["", f"... and {len(findings) - MAX_SUMMARY_ROWS} more finding(s); see the workflow log."]
        lines.append("")
    lines += [
        "<details><summary>What this check is and how to fix findings</summary>",
        "",
        "This check compares the integration metadata (`definition.yaml`, `actions/*.yaml`, `connectors/*.yaml`,",
        "`jobs/*.yaml` and the JSON result examples) between the PR merge base and the PR head. It fails on changes",
        "that break customers who already use the integration in playbooks, connectors or jobs:",
        "",
        "- a component (action/connector/job) removed or renamed, or the integration identifier/name changed;",
        "- a parameter removed, made mandatory, changed type, or a new mandatory parameter added without a default;",
        "- top-level keys removed from an action's JSON result example, or the result changing list <-> object.",
        "",
        "Warnings (non-blocking) cover changed defaults, removed options, renamed files, a `string` parameter hardened",
        "to `password`, a new mandatory parameter that has a default, and files the check could not parse.",
        "",
        "How to fix:",
        "",
        "- keep the old parameter and make it optional (`is_mandatory: false`);",
        "- add the new parameter as optional with a `default_value`;",
        "- keep the old result key alongside the new one;",
        "- if the break is intentional, mark the `release_notes.yaml` entry you add `regressive: true` (or mention",
        f'  "regressive"/"breaking" in its description) or add the `{BREAKING_LABEL}` label, and call it out in',
        "  the PR description. The check then passes with warnings.",
        "",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def json_report(result: CheckResult) -> dict[str, Any]:
    return {
        "base": result.base,
        "head": result.head,
        "merge_base": result.merge_base,
        "label_hatch": result.label_hatch,
        "exit_code": result.exit_code,
        "integrations": [
            {"root": r.root, "base_root": r.base_root, "release_note_hatch": r.release_note_hatch}
            for r in result.reports
        ],
        "findings": [
            {
                "rule": f.rule.rule_id,
                "severity": f.severity.value,
                "blocking": f.is_blocking,
                "waived_by": f.waived_by,
                "integration": f.integration,
                "component": f.component,
                "detail": f.detail,
                "file": f.file,
                "line": f.line,
            }
            for f in result.findings
        ],
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--base", required=True, help="Base commit of the pull request (github.event.pull_request.base.sha)"
    )
    parser.add_argument("--head", required=True, help="Head commit of the pull request")
    parser.add_argument("--labels", default="", help="Comma-separated PR labels")
    parser.add_argument("--repo-root", default=".", help="Path to the repository checkout")
    parser.add_argument(
        "--summary-file",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="Markdown file to append the summary to (defaults to $GITHUB_STEP_SUMMARY)",
    )
    parser.add_argument("--json", dest="json_path", default=None, help="Write a machine-readable report to this path")
    parser.add_argument("--no-annotations", action="store_true", help="Do not print GitHub workflow annotations")
    return parser.parse_args(argv)


def write_output(path: str, text: str, *, append: bool) -> bool:
    """Write ``text`` to ``path``; on failure print a warning annotation and return ``False`` instead of crashing."""
    try:
        with open(path, "a" if append else "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        print(f"::warning::Could not write {path}: {exc}")
        return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = GitRepo(args.repo_root)
    for label, rev in (("base", args.base), ("head", args.head)):
        if not repo.rev_exists(rev):
            print(f"::error::{label} commit {rev} is not available in this checkout (use fetch-depth: 0).")
            return 2
    merge_base = repo.merge_base(args.base, args.head) or args.base
    changed = repo.changed_files(merge_base, args.head, RI_ROOT)
    try:
        result = run_check(
            changed,
            GitTree(repo, merge_base),
            GitTree(repo, args.head),
            labels=parse_labels(args.labels),
            base=args.base,
            head=args.head,
            merge_base=merge_base,
        )
    finally:
        repo.close()

    print(f"Comparing {merge_base[:12]} (merge base) .. {args.head[:12]} (head); {len(changed)} changed file(s).")
    for report in result.reports:
        print(f"- {report.root}: {len(report.findings)} finding(s)")
    for finding in sorted_findings(result):
        if not args.no_annotations:
            print(annotation(finding))
        else:
            print(f"[{finding.rule.rule_id}] {finding.integration} {finding.component}: {finding.detail}")
    markdown = summary_markdown(result)
    if not args.summary_file or not write_output(args.summary_file, markdown, append=True):
        print(markdown)
    if args.json_path:
        write_output(args.json_path, json.dumps(json_report(result), indent=2), append=False)
    if result.exit_code:
        print(f"::error::{len(result.blocking)} breaking change(s) found. See the job summary for details and fixes.")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
