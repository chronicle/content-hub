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

"""Secret and sensitive-data scanner for chronicle/content-hub.

Supports four scanning modes:
- staged: Scans staged changes in the git index (used by pre-commit).
- pre-push: Scans every commit and blob being pushed (used by pre-push),
  catching secrets even if deleted in a later local commit before pushing.
- commits: Scans every commit and blob in a revision range plus any extra
  commit SHAs (used by GitHub Actions PR/push gates, including force-pushes).
- full-repo: Scans all reachable git blobs across all refs (used by full-repo
  CI audits and scheduled scans).
"""

from __future__ import annotations

import argparse
import base64
import binascii
import dataclasses
import gzip
import hashlib
import io
import json
import math
import pathlib
import re
import stat
import subprocess
import sys
import tarfile
import tomllib
import zipfile

MAX_BLOB_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 250
ZERO_SHA = "0" * 40
INLINE_ALLOW_MARKERS = ("gitleaks:allow", "nosec", "pragma: allowlist secret")
ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".gz", ".zip", ".whl", ".tar")
BASE64_SCAN_SUFFIXES = (".py", ".json", ".yaml", ".yml", ".mock", ".txt", ".cfg", ".ini")
BASE64_LITERAL_RE = re.compile(r"""["']([A-Za-z0-9+/]{64,}={0,2})["']""")
HASH_PREFIX_RE = re.compile(r"(?i)(?:sha(?:256|384|512)\s*[:=-]|integrity\s*[:=])\s*$")


@dataclasses.dataclass(frozen=True)
class RuleAllowlist:
    """Allowlist configuration attached to a rule or globally."""

    path_patterns: tuple[re.Pattern[str], ...]
    regex_patterns: tuple[re.Pattern[str], ...]
    regex_target: str = "secret"


@dataclasses.dataclass(frozen=True)
class ScanRule:
    """Compiled detection rule loaded from .gitleaks.toml."""

    rule_id: str
    description: str
    pattern: re.Pattern[str]
    secret_group: int
    entropy: float
    keywords: tuple[str, ...]
    severity: str
    category: str
    allowlists: tuple[RuleAllowlist, ...]


@dataclasses.dataclass(frozen=True)
class Finding:
    """A redacted security finding discovered in a blob or commit."""

    rule_id: str
    severity: str
    category: str
    description: str
    file_path: str
    line_number: int
    commit_sha: str
    redacted_secret: str
    secret_sha256: str

    def fingerprint(self) -> str:
        """Return a deterministic, secret-safe, path-independent fingerprint for baselining.

        The path is deliberately excluded: `git rev-list --objects` reports each blob under the
        first path it encounters, which varies with the set of fetched refs.
        """
        return f"{self.rule_id}:{self.secret_sha256}"

    def to_dict(self) -> dict[str, str | int]:
        """Serialize the finding without exposing raw secret material."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "commit_sha": self.commit_sha,
            "redacted_secret": self.redacted_secret,
            "secret_sha256": self.secret_sha256,
            "fingerprint": self.fingerprint(),
        }


@dataclasses.dataclass(frozen=True)
class BlobTarget:
    """A git blob or staged file queued for scanning."""

    blob_sha: str
    file_path: str
    commit_sha: str


def run_scan(args: argparse.Namespace) -> int:
    """Execute the requested scan workflow and emit reports."""
    repo_root = pathlib.Path(args.repo_root).resolve()
    if args.install_hooks:
        return install_git_hooks(repo_root)

    config_path = pathlib.Path(args.config) if args.config else repo_root / ".gitleaks.toml"
    global_allowlist, rules = load_rules_from_toml(config_path)
    baseline_fingerprints = load_baseline(pathlib.Path(args.baseline)) if args.baseline else set()

    findings = execute_scan_mode(args, repo_root, global_allowlist, rules)
    if args.write_baseline:
        write_baseline_file(pathlib.Path(args.write_baseline), findings)

    active_findings = [f for f in findings if f.fingerprint() not in baseline_fingerprints]
    deduped_findings = deduplicate_findings(active_findings)

    emit_outputs(args, deduped_findings, len(findings) - len(active_findings))
    return 1 if deduped_findings else 0


def execute_scan_mode(
    args: argparse.Namespace,
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Dispatch to the selected scan mode."""
    if args.mode == "staged":
        return scan_staged_changes(repo_root, global_allowlist, rules)
    if args.mode == "pre-push":
        return scan_pre_push_ranges(repo_root, global_allowlist, rules, args.pre_push_stdin)
    if args.mode == "commits":
        return scan_commit_range(
            repo_root=repo_root,
            global_allowlist=global_allowlist,
            rules=rules,
            base_ref=args.base,
            head_ref=args.head,
            extra_commits=tuple(args.extra_commit or ()),
        )
    if args.mode == "full-repo":
        return scan_full_repository(
            repo_root=repo_root,
            global_allowlist=global_allowlist,
            rules=rules,
            working_tree_only=args.working_tree,
        )
    msg = f"Unsupported scan mode: {args.mode}"
    raise ValueError(msg)


def scan_staged_changes(
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Scan all files currently staged in the git index."""
    output = run_git_bytes(repo_root, ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"])
    paths = [p.decode("utf-8", errors="replace") for p in output.split(b"\x00") if p]
    findings: list[Finding] = []
    for rel_path in paths:
        if is_path_allowlisted(rel_path, global_allowlist):
            continue
        blob_bytes = read_staged_file_bytes(repo_root, rel_path)
        if blob_bytes is None:
            continue
        findings.extend(
            scan_blob_bytes(
                data=blob_bytes,
                file_path=rel_path,
                commit_sha="STAGED",
                global_allowlist=global_allowlist,
                rules=rules,
            )
        )
    return findings


def read_staged_file_bytes(repo_root: pathlib.Path, rel_path: str) -> bytes | None:
    """Read staged file content from the git index, falling back to working tree."""
    proc = subprocess.run(
        ["git", "show", f":{rel_path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout
    candidate = repo_root / rel_path
    if candidate.is_file():
        return candidate.read_bytes()
    return None


def scan_pre_push_ranges(
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    stdin_text: str | None = None,
) -> list[Finding]:
    """Scan all unpushed commits and blobs being sent during git push."""
    raw_lines = stdin_text if stdin_text is not None else read_nonblocking_stdin()
    rev_specs = build_pre_push_rev_specs(repo_root, raw_lines)
    if not rev_specs:
        return []
    targets = collect_targets_for_revs(repo_root, rev_specs, global_allowlist)
    findings = scan_blob_targets_batch(repo_root, targets, global_allowlist, rules)
    findings.extend(scan_commit_messages(repo_root, rev_specs, global_allowlist, rules))
    return findings


def read_nonblocking_stdin() -> str:
    """Read stdin if piped from git pre-push hook."""
    if sys.stdin is None or sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def build_pre_push_rev_specs(repo_root: pathlib.Path, raw_stdin: str) -> list[str]:
    """Translate git pre-push stdin lines into git rev-list revision specifications.

    New branches (remote SHA is all zeros or unknown locally) are scanned as every commit
    not yet on any origin ref. `--not` negates every revision that follows it, so it is
    appended exactly once at the end, after all positive revisions.
    """
    rev_specs: list[str] = []
    has_new_branch = False
    for line in raw_stdin.splitlines():
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA:
            continue
        if remote_sha == ZERO_SHA or not commit_exists(repo_root, remote_sha):
            rev_specs.append(local_sha)
            has_new_branch = True
        else:
            rev_specs.append(f"{remote_sha}..{local_sha}")

    if has_new_branch:
        rev_specs.extend(["--not", "--remotes=origin"])
    if not rev_specs and commit_exists(repo_root, "origin/main"):
        rev_specs.append("origin/main..HEAD")
    return rev_specs


def scan_commit_range(
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    base_ref: str | None,
    head_ref: str,
    extra_commits: tuple[str, ...],
) -> list[Finding]:
    """Scan every individual commit and blob in a range plus any extra commits."""
    rev_specs: list[str] = []
    if base_ref and base_ref != ZERO_SHA and commit_exists(repo_root, base_ref):
        rev_specs.append(f"{base_ref}..{head_ref}")
    elif commit_exists(repo_root, head_ref):
        rev_specs.append(head_ref)

    for extra_sha in extra_commits:
        if extra_sha and extra_sha != ZERO_SHA and commit_exists(repo_root, extra_sha):
            if base_ref and base_ref != ZERO_SHA and commit_exists(repo_root, base_ref):
                rev_specs.append(f"{base_ref}..{extra_sha}")
            else:
                rev_specs.append(extra_sha)

    if not rev_specs:
        return []
    targets = collect_targets_for_revs(repo_root, rev_specs, global_allowlist)
    findings = scan_blob_targets_batch(repo_root, targets, global_allowlist, rules)
    findings.extend(scan_commit_messages(repo_root, rev_specs, global_allowlist, rules))
    return findings


def scan_commit_messages(
    repo_root: pathlib.Path,
    rev_specs: list[str],
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Scan commit messages in rev_specs (excluding bug refs permitted in commit titles)."""
    msg_rules = tuple(r for r in rules if r.rule_id != "google-internal-bug-ref")
    raw_out = run_git_bytes(
        repo_root,
        ["log", "-z", "--pretty=format:%H%x01%B", *rev_specs],
    ).decode("utf-8", errors="replace")
    findings: list[Finding] = []
    for entry in raw_out.split("\x00"):
        commit_sha, sep, body = entry.strip().partition("\x01")
        if not sep or not body:
            continue
        findings.extend(
            scan_text_content(
                text=body,
                file_path="<commit-message>",
                commit_sha=commit_sha,
                global_allowlist=global_allowlist,
                rules=msg_rules,
            )
        )
    return findings


def collect_targets_for_revs(
    repo_root: pathlib.Path,
    rev_specs: list[str],
    global_allowlist: RuleAllowlist,
) -> list[BlobTarget]:
    """Collect every blob added or modified across all commits matching rev_specs."""
    cmd = [
        "log",
        "--raw",
        "--no-abbrev",
        "-z",
        "--diff-filter=AMRT",
        "--pretty=format:__COMMIT__%H",
        *rev_specs,
    ]
    raw_out = run_git_bytes(repo_root, cmd).decode("utf-8", errors="replace")
    return parse_git_log_raw_targets(raw_out, global_allowlist)


def parse_git_log_raw_targets(
    raw_out: str,
    global_allowlist: RuleAllowlist,
) -> list[BlobTarget]:
    """Parse git log --raw -z output into deduplicated BlobTarget entries."""
    targets: list[BlobTarget] = []
    seen_blobs: set[tuple[str, str]] = set()
    current_commit = "UNKNOWN"
    tokens = raw_out.split("\x00")
    idx = 0

    while idx < len(tokens):
        token = tokens[idx].lstrip("\n")
        if token.startswith("__COMMIT__"):
            header, _, remainder = token.partition("\n")
            current_commit = header.removeprefix("__COMMIT__").strip()
            token = remainder.lstrip("\n")
        if not token.startswith(":"):
            idx += 1
            continue
        blob_sha, status = extract_blob_from_raw_header(token)
        idx += 1
        file_path = tokens[idx] if idx < len(tokens) else ""
        if status.startswith(("R", "C")) and idx + 1 < len(tokens):
            idx += 1
            file_path = tokens[idx]
        idx += 1
        if not blob_sha or blob_sha == ZERO_SHA or not file_path:
            continue
        if is_path_allowlisted(file_path, global_allowlist):
            continue
        key = (blob_sha, file_path)
        if key not in seen_blobs:
            seen_blobs.add(key)
            targets.append(BlobTarget(blob_sha=blob_sha, file_path=file_path, commit_sha=current_commit))
    return targets


def extract_blob_from_raw_header(header_token: str) -> tuple[str, str]:
    """Extract (new_blob_sha, status) from a git --raw diff header token."""
    parts = header_token.split()
    if len(parts) < 5:
        return ("", "")
    return (parts[3], parts[4])


def scan_full_repository(
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    working_tree_only: bool = False,
) -> list[Finding]:
    """Scan all reachable git blobs across all refs or all tracked working-tree files."""
    if working_tree_only:
        return scan_working_tree(repo_root, global_allowlist, rules)

    raw_objects = run_git_bytes(repo_root, ["rev-list", "--all", "--objects"]).decode("utf-8", errors="replace")
    targets: list[BlobTarget] = []
    seen_shas: set[str] = set()
    for line in raw_objects.splitlines():
        sha, sep, path = line.partition(" ")
        if not sep or not path or sha in seen_shas:
            continue
        if is_path_allowlisted(path, global_allowlist):
            continue
        seen_shas.add(sha)
        targets.append(BlobTarget(blob_sha=sha, file_path=path, commit_sha="ALL_REFS"))
    return scan_blob_targets_batch(repo_root, targets, global_allowlist, rules)


def scan_working_tree(
    repo_root: pathlib.Path,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Scan all git-tracked files currently present in the working tree."""
    output = run_git_bytes(repo_root, ["ls-files", "-z"])
    paths = [p.decode("utf-8", errors="replace") for p in output.split(b"\x00") if p]
    findings: list[Finding] = []
    for rel_path in paths:
        if is_path_allowlisted(rel_path, global_allowlist):
            continue
        full_path = repo_root / rel_path
        if not full_path.is_file():
            continue
        findings.extend(
            scan_blob_bytes(
                data=full_path.read_bytes(),
                file_path=rel_path,
                commit_sha="HEAD",
                global_allowlist=global_allowlist,
                rules=rules,
            )
        )
    return findings


def scan_blob_targets_batch(
    repo_root: pathlib.Path,
    targets: list[BlobTarget],
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Stream and scan git blobs in bulk using git cat-file --batch."""
    if not targets:
        return []
    target_by_sha: dict[str, list[BlobTarget]] = {}
    for target in targets:
        target_by_sha.setdefault(target.blob_sha, []).append(target)

    stdin_payload = "".join(f"{sha}\n" for sha in target_by_sha).encode("utf-8")
    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        input=stdin_payload,
        capture_output=True,
        check=True,
    )
    return parse_cat_file_batch_stream(proc.stdout, target_by_sha, global_allowlist, rules)


def parse_cat_file_batch_stream(
    stream: bytes,
    target_by_sha: dict[str, list[BlobTarget]],
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Parse git cat-file --batch binary stream and scan each blob."""
    findings: list[Finding] = []
    offset = 0
    total_len = len(stream)

    while offset < total_len:
        newline_idx = stream.find(b"\n", offset)
        if newline_idx == -1:
            break
        header = stream[offset:newline_idx].decode("utf-8", errors="replace")
        offset = newline_idx + 1
        parts = header.split()
        if len(parts) < 3 or parts[1] == "missing":
            continue
        sha, obj_type, size_str = parts[0], parts[1], parts[2]
        size = int(size_str)
        data = stream[offset : offset + size]
        offset += size + 1
        if obj_type != "blob" or size > MAX_BLOB_BYTES:
            continue
        for target in target_by_sha.get(sha, ()):
            findings.extend(
                scan_blob_bytes(
                    data=data,
                    file_path=target.file_path,
                    commit_sha=target.commit_sha,
                    global_allowlist=global_allowlist,
                    rules=rules,
                )
            )
    return findings


def scan_blob_bytes(
    data: bytes,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int = 0,
) -> list[Finding]:
    """Scan raw blob bytes, including archives, playbook zips, and Base64 payloads."""
    if not data or len(data) > MAX_BLOB_BYTES or depth > 2:
        return []
    if is_path_allowlisted(file_path, global_allowlist):
        return []

    findings: list[Finding] = []
    lower_path = file_path.lower()
    if lower_path.endswith(ARCHIVE_SUFFIXES):
        findings.extend(
            scan_archive_bytes(
                data=data,
                file_path=file_path,
                commit_sha=commit_sha,
                global_allowlist=global_allowlist,
                rules=rules,
                depth=depth,
            )
        )
        return findings

    if b"\x00" in data[:4096]:
        return findings

    text = data.decode("utf-8", errors="replace")
    findings.extend(scan_text_content(text, file_path, commit_sha, global_allowlist, rules))
    if depth == 0 and lower_path.endswith(BASE64_SCAN_SUFFIXES):
        findings.extend(scan_embedded_base64_literals(text, file_path, commit_sha, global_allowlist, rules, depth))
    return findings


def scan_archive_bytes(
    data: bytes,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int,
) -> list[Finding]:
    """Extract and scan .gz, .zip, .whl, .tar, and .tar.gz archives in memory."""
    lower_path = file_path.lower()
    if lower_path.endswith((".zip", ".whl")):
        return scan_zip_bytes(data, file_path, commit_sha, global_allowlist, rules, depth)
    if lower_path.endswith((".tar.gz", ".tgz", ".tar")):
        return scan_tar_bytes(data, file_path, commit_sha, global_allowlist, rules, depth)
    if lower_path.endswith(".gz"):
        return scan_gzip_bytes(data, file_path, commit_sha, global_allowlist, rules, depth)
    return []


def scan_zip_bytes(
    data: bytes,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int,
) -> list[Finding]:
    """Scan members of a ZIP archive and check for encrypted playbook archives."""
    findings: list[Finding] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()[:MAX_ARCHIVE_MEMBERS]
            if is_encrypted_playbook_zip(file_path, infos):
                findings.append(build_encrypted_playbook_finding(file_path, commit_sha))
                return findings
            for zinfo in infos:
                if zinfo.is_dir() or (zinfo.flag_bits & 0x1) or zinfo.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                    continue
                inner_path = f"{file_path}!{zinfo.filename}"
                member_bytes = zf.read(zinfo.filename)
                findings.extend(
                    scan_blob_bytes(
                        data=member_bytes,
                        file_path=inner_path,
                        commit_sha=commit_sha,
                        global_allowlist=global_allowlist,
                        rules=rules,
                        depth=depth + 1,
                    )
                )
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError):
        return findings
    return findings


def is_encrypted_playbook_zip(file_path: str, infos: list[zipfile.ZipInfo]) -> bool:
    """Return True when a playbook ZIP archive contains password-encrypted entries."""
    normalized = file_path.replace("\\", "/")
    if "content/playbooks/" not in normalized and not normalized.startswith("playbooks/"):
        return False
    return any(bool(zinfo.flag_bits & 0x1) for zinfo in infos)


def build_encrypted_playbook_finding(file_path: str, commit_sha: str) -> Finding:
    """Create a finding for an uninspected password-encrypted playbook ZIP archive."""
    digest = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:12]
    return Finding(
        rule_id="encrypted-playbook-archive",
        severity="MEDIUM",
        category="encrypted-archive",
        description="Password-encrypted playbook ZIP archive cannot be audited for embedded credentials",
        file_path=file_path,
        line_number=1,
        commit_sha=commit_sha,
        redacted_secret=f"encrypted-zip (sha256:{digest})",
        secret_sha256=digest,
    )


def scan_tar_bytes(
    data: bytes,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int,
) -> list[Finding]:
    """Scan members of a TAR or TAR.GZ archive in memory."""
    findings: list[Finding] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            for member in tf.getmembers()[:MAX_ARCHIVE_MEMBERS]:
                if not member.isfile() or member.size > MAX_ARCHIVE_MEMBER_BYTES:
                    continue
                extracted = tf.extractfile(member)
                if extracted is None:
                    continue
                findings.extend(
                    scan_blob_bytes(
                        data=extracted.read(MAX_ARCHIVE_MEMBER_BYTES),
                        file_path=f"{file_path}!{member.name}",
                        commit_sha=commit_sha,
                        global_allowlist=global_allowlist,
                        rules=rules,
                        depth=depth + 1,
                    )
                )
    except (tarfile.TarError, OSError, EOFError):
        return findings
    return findings


def scan_gzip_bytes(
    data: bytes,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int,
) -> list[Finding]:
    """Decompress and scan a .gz file in memory."""
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            decompressed = gz.read(MAX_ARCHIVE_MEMBER_BYTES)
    except (OSError, EOFError):
        return []
    inner_name = file_path.removesuffix(".gz")
    return scan_blob_bytes(
        data=decompressed,
        file_path=f"{file_path}!{pathlib.Path(inner_name).name}",
        commit_sha=commit_sha,
        global_allowlist=global_allowlist,
        rules=rules,
        depth=depth + 1,
    )


def scan_embedded_base64_literals(
    text: str,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
    depth: int,
) -> list[Finding]:
    """Decode and scan Base64 or Base64+gzip string literals embedded in code/mocks."""
    findings: list[Finding] = []
    for match in BASE64_LITERAL_RE.finditer(text):
        candidate = match.group(1)
        decoded = decode_base64_or_gzip(candidate)
        if not decoded:
            continue
        line_no = text.count("\n", 0, match.start()) + 1
        sub_findings = scan_blob_bytes(
            data=decoded,
            file_path=f"{file_path}#base64@L{line_no}",
            commit_sha=commit_sha,
            global_allowlist=global_allowlist,
            rules=rules,
            depth=depth + 1,
        )
        findings.extend(sub_findings)
    return findings


def decode_base64_or_gzip(candidate: str) -> bytes | None:
    """Decode a Base64 string, decompressing if it starts with the gzip magic header."""
    if len(candidate) % 4 != 0:
        return None
    try:
        raw = base64.b64decode(candidate, validate=True)
    except (binascii.Error, ValueError):
        return None
    if raw.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                return gz.read(MAX_ARCHIVE_MEMBER_BYTES)
        except (OSError, EOFError):
            return None
    if is_mostly_printable_utf8(raw):
        return raw
    return None


def is_mostly_printable_utf8(raw: bytes) -> bool:
    """Check whether decoded bytes represent valid printable UTF-8 text."""
    if not raw or b"\x00" in raw:
        return False
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    printable = sum(1 for ch in decoded if ch.isprintable() or ch in "\r\n\t")
    return (printable / len(decoded)) >= 0.90


def scan_text_content(
    text: str,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rules: tuple[ScanRule, ...],
) -> list[Finding]:
    """Evaluate all compiled rules against a UTF-8 text document."""
    findings: list[Finding] = []
    lower_text = text.lower()
    base_file_path = file_path.split("!", 1)[0].split("#", 1)[0]

    for rule in rules:
        if not text_has_rule_keywords(lower_text, rule):
            continue
        if is_rule_path_allowlisted(base_file_path, rule):
            continue
        findings.extend(apply_rule_to_text(text, file_path, commit_sha, global_allowlist, rule))
    return findings


def text_has_rule_keywords(lower_text: str, rule: ScanRule) -> bool:
    """Fast pre-check: verify at least one rule keyword appears in the text."""
    if not rule.keywords:
        return True
    return any(kw in lower_text for kw in rule.keywords)


def apply_rule_to_text(
    text: str,
    file_path: str,
    commit_sha: str,
    global_allowlist: RuleAllowlist,
    rule: ScanRule,
) -> list[Finding]:
    """Find and validate all regex matches for a single rule in text."""
    findings: list[Finding] = []
    lines = text.splitlines()

    for match in rule.pattern.finditer(text):
        secret = extract_secret_from_match(match, rule.secret_group)
        if not secret:
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        line_text = lines[line_number - 1] if 1 <= line_number <= len(lines) else ""
        if should_suppress_match(secret, line_text, match, text, global_allowlist, rule):
            continue
        redacted, sha_prefix = redact_secret(secret)
        findings.append(
            Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                category=rule.category,
                description=rule.description,
                file_path=file_path,
                line_number=line_number,
                commit_sha=commit_sha,
                redacted_secret=redacted,
                secret_sha256=sha_prefix,
            )
        )
    return findings


def extract_secret_from_match(match: re.Match[str], secret_group: int) -> str:
    """Extract the captured secret group from a regex match."""
    if secret_group and secret_group <= (match.lastindex or 0):
        val = match.group(secret_group)
        if val:
            return val.strip()
    if match.lastindex:
        for idx in range(1, match.lastindex + 1):
            val = match.group(idx)
            if val:
                return val.strip()
    return match.group(0).strip()


def should_suppress_match(
    secret: str,
    line_text: str,
    match: re.Match[str],
    full_text: str,
    global_allowlist: RuleAllowlist,
    rule: ScanRule,
) -> bool:
    """Return True if a match is allowlisted, low-entropy, or fails structural verification."""
    lower_line = line_text.lower()
    if any(marker in lower_line for marker in INLINE_ALLOW_MARKERS):
        return True
    if matches_allowlist_regex(secret, line_text, global_allowlist):
        return True
    if any(matches_allowlist_regex(secret, line_text, al) for al in rule.allowlists):
        return True
    if rule.entropy > 0.0 and shannon_entropy(secret) < rule.entropy:
        return True
    return not verify_rule_specific_constraints(rule.rule_id, secret, line_text, match, full_text)


def verify_rule_specific_constraints(
    rule_id: str,
    secret: str,
    line_text: str,
    match: re.Match[str],
    full_text: str,
) -> bool:
    """Run structural verifiers for SOAR AppKeys and CLI credentials."""
    if rule_id in ("soar-app-key", "soar-app-key-context"):
        prefix = full_text[max(0, match.start() - 32) : match.start()]
        if HASH_PREFIX_RE.search(prefix):
            return False
        return is_valid_soar_base64_digest(secret)
    if rule_id == "soar-app-key-uuid":
        return not is_placeholder_uuid(secret)
    if rule_id in ("soar-cli-credentials", "akeyless-access-credentials"):
        return not is_placeholder_credential(secret, line_text)
    return True


def is_valid_soar_base64_digest(secret: str) -> bool:
    """Verify a 44-char string is a 32-byte binary digest (not encoded ASCII text)."""
    if len(secret) != 44 or not secret.endswith("="):
        return False
    try:
        raw = base64.b64decode(secret, validate=True)
    except (binascii.Error, ValueError):
        return False
    if len(raw) != 32 or len(set(raw)) < 8:
        return False
    # Real SHA-256 digests of UUID bytes contain non-printable binary bytes;
    # 100% printable ASCII bytes indicate a base64-encoded 32-char text string.
    return not all(0x20 <= b <= 0x7E for b in raw)


def is_placeholder_uuid(secret: str) -> bool:
    """Return True if a UUID consists of trivial repeating characters or sequence digits."""
    compact = secret.replace("-", "").lower()
    if len(set(compact)) <= 2:
        return True
    return compact in ("12345678123412341234123456789012", "0123456789abcdef0123456789abcdef")


def is_placeholder_credential(secret: str, line_text: str) -> bool:
    """Return True if a CLI or Akeyless credential value is a variable or documentation placeholder."""
    stripped = secret.strip("\"'`")
    if stripped.startswith(("$", "<", "{", "%", "--")) or stripped.endswith((">", "}")):
        return True
    lower = stripped.lower()
    placeholder_tokens = (
        "your_",
        "your-",
        "example",
        "placeholder",
        "changeme",
        "password",
        "api_key",
        "apikey",
        "xxx",
    )
    if any(tok in lower for tok in placeholder_tokens):
        return True
    return "pytest" in line_text.lower() and "monkeypatch" in line_text.lower()


def shannon_entropy(value: str) -> float:
    """Calculate the Shannon entropy (in bits per character) of a string."""
    if not value:
        return 0.0
    length = len(value)
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def redact_secret(secret: str) -> tuple[str, str]:
    """Redact a raw secret into a safe preview and 12-char SHA-256 prefix."""
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]
    if len(secret) <= 8:
        return (f"*** (sha256:{digest})", digest)
    return (f"{secret[:3]}***{secret[-2:]} (sha256:{digest})", digest)


def load_rules_from_toml(config_path: pathlib.Path) -> tuple[RuleAllowlist, tuple[ScanRule, ...]]:
    """Parse .gitleaks.toml into a global allowlist and compiled ScanRule objects."""
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    global_al = compile_allowlist(raw.get("allowlist", {}))
    rules: list[ScanRule] = []
    for entry in raw.get("rules", []):
        tags = tuple(entry.get("tags", ()))
        severity = extract_tag_value(tags, "severity:", "HIGH")
        category = extract_tag_value(tags, "category:", "secret")
        rule_als = tuple(compile_allowlist(al) for al in entry.get("allowlists", ()))
        rules.append(
            ScanRule(
                rule_id=entry["id"],
                description=entry.get("description", entry["id"]),
                pattern=re.compile(entry["regex"], re.MULTILINE),
                secret_group=int(entry.get("secretGroup", 0)),
                entropy=float(entry.get("entropy", 0.0)),
                keywords=tuple(kw.lower() for kw in entry.get("keywords", ())),
                severity=severity,
                category=category,
                allowlists=rule_als,
            )
        )
    return (global_al, tuple(rules))


def compile_allowlist(raw_al: dict[str, object]) -> RuleAllowlist:
    """Compile path and regex patterns for an allowlist block."""
    raw_paths = raw_al.get("paths")
    raw_regexes = raw_al.get("regexes")
    paths = tuple(re.compile(str(p)) for p in raw_paths) if isinstance(raw_paths, list) else ()
    regexes = tuple(re.compile(str(r)) for r in raw_regexes) if isinstance(raw_regexes, list) else ()
    target = str(raw_al.get("regexTarget", "secret"))
    return RuleAllowlist(path_patterns=paths, regex_patterns=regexes, regex_target=target)


def extract_tag_value(tags: tuple[str, ...], prefix: str, default: str) -> str:
    """Extract a structured tag value such as severity:CRITICAL from rule tags."""
    for tag in tags:
        if tag.startswith(prefix):
            return tag.removeprefix(prefix)
    return default


def is_path_allowlisted(file_path: str, allowlist: RuleAllowlist) -> bool:
    """Return True if the normalized path matches any allowlist path regex."""
    normalized = file_path.replace("\\", "/").split("!", 1)[0].split("#", 1)[0]
    return any(pattern.search(normalized) is not None for pattern in allowlist.path_patterns)


def is_rule_path_allowlisted(file_path: str, rule: ScanRule) -> bool:
    """Return True if the file path is allowlisted for a specific rule."""
    return any(is_path_allowlisted(file_path, al) for al in rule.allowlists)


def matches_allowlist_regex(secret: str, line_text: str, allowlist: RuleAllowlist) -> bool:
    """Return True if the secret or line matches an allowlist regex."""
    candidate = line_text if allowlist.regex_target in ("line", "match") else secret
    return any(pattern.search(candidate) is not None for pattern in allowlist.regex_patterns)


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Deduplicate findings by (rule_id, file_path, line_number, secret_sha256)."""
    seen: set[tuple[str, str, int, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.file_path, finding.line_number, finding.secret_sha256)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return unique


def load_baseline(baseline_path: pathlib.Path) -> set[str]:
    """Load baselined finding fingerprints from a JSON file."""
    if not baseline_path.is_file():
        return set()
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    return set(payload.get("fingerprints", ()))


def write_baseline_file(baseline_path: pathlib.Path, findings: list[Finding]) -> None:
    """Write secret-safe finding fingerprints to a JSON baseline file."""
    fingerprints = sorted({f.fingerprint() for f in findings})
    payload = {
        "description": "Baselined historical findings tracked by secret-safe SHA-256 fingerprint.",
        "fingerprints": fingerprints,
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def emit_outputs(args: argparse.Namespace, findings: list[Finding], suppressed_count: int) -> None:
    """Write console summary, optional JSON/Markdown reports, and GitHub annotations."""
    if args.json_out:
        out_path = pathlib.Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps([f.to_dict() for f in findings], indent=2) + "\n",
            encoding="utf-8",
        )
    if args.markdown_out:
        md_path = pathlib.Path(args.markdown_out)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(format_markdown_report(findings, args.mode), encoding="utf-8")
    if args.github_annotations:
        for finding in findings:
            base_path = finding.file_path.split("!", 1)[0].split("#", 1)[0]
            print(
                f"::error file={base_path},line={finding.line_number},"
                f"title=Secret Scan ({finding.rule_id})::"
                f"[{finding.severity}] {finding.description} in {finding.file_path} "
                f"(commit {finding.commit_sha[:12]}): {finding.redacted_secret}"
            )
    print_console_summary(findings, args.mode, suppressed_count)


def format_markdown_report(findings: list[Finding], mode: str) -> str:
    """Render a redacted Markdown table suitable for PR comments and alert issues."""
    if not findings:
        return f"✅ **Secret & Sensitive Data Scan (`{mode}`)** passed with 0 findings.\n"
    lines = [
        f"### 🚨 Secret & Sensitive Data Scan Alert (`{mode}`)",
        "",
        "One or more commits or repository blobs contain a potential secret, tenant URL, or internal Google reference.",
        "**Important:** Even if a secret was removed in a follow-up commit, git history retains the exposed blob.",
        "Any exposed credential must be **rotated/revoked immediately** and purged from commit history.",
        "",
        "| Severity | Rule | File / Archive Member | Line | Commit | Redacted Match |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for f in findings:
        short_sha = f.commit_sha[:12]
        lines.append(
            f"| **{f.severity}** | `{f.rule_id}` | `{f.file_path}` | {f.line_number} | "
            f"`{short_sha}` | `{f.redacted_secret}` |"
        )
    lines.append("")
    return "\n".join(lines)


def print_console_summary(findings: list[Finding], mode: str, suppressed_count: int) -> None:
    """Print a human-readable, redacted summary to stderr/stdout."""
    if not findings:
        extra = f" ({suppressed_count} baselined)" if suppressed_count else ""
        print(f"[scan_secrets] OK ({mode}): 0 active findings{extra}.")
        return
    print(
        f"[scan_secrets] FAILED ({mode}): {len(findings)} finding(s) detected!",
        file=sys.stderr,
    )
    for f in findings:
        print(
            f"  - [{f.severity}] {f.rule_id} at {f.file_path}:{f.line_number} "
            f"(commit {f.commit_sha[:12]}): {f.redacted_secret} — {f.description}",
            file=sys.stderr,
        )
    print(
        "\nRemediation:\n"
        "  1. If a real credential was committed, ROTATE/REVOKE it immediately.\n"
        "  2. Remove the secret from the commit history (e.g. git reset / git commit --amend / interactive rebase)\n"
        "     — deleting a secret in a second commit does NOT remove it from git history!\n"
        "  3. For verified false positives in test fixtures, use a clear placeholder or add '# gitleaks:allow'.",
        file=sys.stderr,
    )


def install_git_hooks(repo_root: pathlib.Path) -> int:
    """Configure git core.hooksPath to .githooks and ensure hooks are executable."""
    hooks_dir = repo_root / ".githooks"
    if not hooks_dir.is_dir():
        print(f"Error: {hooks_dir} does not exist.", file=sys.stderr)
        return 1
    for hook_name in ("pre-commit", "pre-push"):
        hook_file = hooks_dir / hook_name
        if hook_file.is_file():
            current_mode = hook_file.stat().st_mode
            hook_file.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks"],
        cwd=repo_root,
        check=True,
    )
    print(f"Configured git core.hooksPath -> {hooks_dir}")
    return 0


def commit_exists(repo_root: pathlib.Path, rev: str) -> bool:
    """Return True if a revision/commit exists in the local git object database."""
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{rev}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def run_git_bytes(repo_root: pathlib.Path, git_args: list[str]) -> bytes:
    """Run a git command and return stdout bytes."""
    proc = subprocess.run(
        ["git", *git_args],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Scan chronicle/content-hub for secrets and sensitive references.")
    parser.add_argument(
        "--mode",
        choices=("staged", "pre-push", "commits", "full-repo"),
        default="staged",
        help="Scanning mode to execute.",
    )
    parser.add_argument("--repo-root", default=".", help="Path to the git repository root.")
    parser.add_argument("--config", default=None, help="Path to .gitleaks.toml configuration.")
    parser.add_argument("--base", default=None, help="Base commit/ref for --mode commits.")
    parser.add_argument("--head", default="HEAD", help="Head commit/ref for --mode commits.")
    parser.add_argument(
        "--extra-commit",
        action="append",
        default=[],
        help="Additional commit SHA(s) to scan (e.g., force-pushed event.before SHAs).",
    )
    parser.add_argument("--pre-push-stdin", default=None, help="Override pre-push stdin lines for testing.")
    parser.add_argument(
        "--working-tree", action="store_true", help="Scan tracked working tree files in full-repo mode."
    )
    parser.add_argument("--baseline", default=None, help="Path to baseline JSON file of known historical fingerprints.")
    parser.add_argument("--write-baseline", default=None, help="Write detected fingerprints to a baseline JSON file.")
    parser.add_argument("--json-out", default=None, help="Write redacted findings JSON to path.")
    parser.add_argument("--markdown-out", default=None, help="Write redacted Markdown summary to path.")
    parser.add_argument("--github-annotations", action="store_true", help="Emit GitHub Actions error annotations.")
    parser.add_argument("--install-hooks", action="store_true", help="Install .githooks into local git config.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return run_scan(args)


if __name__ == "__main__":
    sys.exit(main())
