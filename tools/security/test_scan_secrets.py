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

"""Tests for tools/security/scan_secrets.py."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import pathlib
import subprocess
import uuid
import zipfile

import scan_secrets

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GITLEAKS_TOML = REPO_ROOT / ".gitleaks.toml"


def _load_test_rules() -> tuple[scan_secrets.RuleAllowlist, tuple[scan_secrets.ScanRule, ...]]:
    """Load the repository's .gitleaks.toml rules for testing."""
    return scan_secrets.load_rules_from_toml(GITLEAKS_TOML)


def _generate_system_soar_key() -> str:
    """Generate a realistic 44-char Base64 SHA-256 SOAR System AppKey."""
    digest = hashlib.sha256(uuid.UUID("8f5c2b91-4d3e-4a12-9c88-7b6a5d4e3f21").bytes).digest()
    return base64.b64encode(digest).decode("ascii")


def _init_git_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """Initialize a temporary git repo with a clean initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Dev"], cwd=repo, check=True, capture_output=True)
    readme = repo / "README.md"
    readme.write_text("# Clean Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)
    return repo


def _git_head(repo: pathlib.Path) -> str:
    """Return the current HEAD commit SHA of repo."""
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def test_detects_both_soar_app_key_formats_and_redacts() -> None:
    """Verify both 44-char Base64 system AppKeys and UUIDv4 user AppKeys are caught and redacted."""
    global_al, rules = _load_test_rules()
    system_key = _generate_system_soar_key()
    user_uuid_key = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    sample_code = (
        f'SIEMPLIFY_APP_KEY = "{system_key}"\n'
        f'headers = {{"X-Siemplify-App-Key": "{user_uuid_key}"}}\n'
        'SOAR_URL = "https://acme-prod.siemplify-soar.com/api/external/v1"\n'
    )

    findings = scan_secrets.scan_blob_bytes(
        data=sample_code.encode("utf-8"),
        file_path="content/response_integrations/third_party/acme/test_acme.py",
        commit_sha="deadbeef12345678",
        global_allowlist=global_al,
        rules=rules,
    )
    rule_ids = {f.rule_id for f in findings}
    assert "soar-app-key" in rule_ids
    assert "soar-app-key-uuid" in rule_ids
    assert "siemplify-tenant-url" in rule_ids

    report = scan_secrets.format_markdown_report(findings, "commits")
    assert system_key not in report
    assert user_uuid_key not in report
    for finding in findings:
        serialized = str(finding.to_dict())
        assert system_key not in serialized
        assert user_uuid_key not in serialized


def test_catches_secret_added_then_deleted_in_later_commit(tmp_path: pathlib.Path) -> None:
    """Regression test for PR #427: secret added in Commit 1 and removed in Commit 2 must fail."""
    global_al, rules = _load_test_rules()
    repo = _init_git_repo(tmp_path)
    base_sha = _git_head(repo)

    user_uuid_key = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
    script_file = repo / "integration.py"

    # Commit 1: Developer accidentally commits real UUID AppKey and SOAR tenant URL.
    script_file.write_text(
        f'EVAL_SDK_APP_KEY = "{user_uuid_key}"\nHOST = "https://customer-soar.siemplify-soar.com"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "integration.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add integration"], cwd=repo, check=True, capture_output=True)
    leaked_commit_sha = _git_head(repo)

    # Commit 2: Developer deletes the secret in a follow-up commit (final tree is clean!).
    script_file.write_text(
        'import os\nEVAL_SDK_APP_KEY = os.environ["EVAL_SDK_APP_KEY"]\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "integration.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Remove hardcoded key"], cwd=repo, check=True, capture_output=True)
    head_sha = _git_head(repo)

    # 1. Commit-range scan (CI PR/push check) MUST catch the secret in Commit 1.
    commit_findings = scan_secrets.scan_commit_range(
        repo_root=repo,
        global_allowlist=global_al,
        rules=rules,
        base_ref=base_sha,
        head_ref=head_sha,
        extra_commits=(),
    )
    assert any(f.rule_id == "soar-app-key-uuid" and f.commit_sha == leaked_commit_sha for f in commit_findings)
    assert any(f.rule_id == "siemplify-tenant-url" and f.commit_sha == leaked_commit_sha for f in commit_findings)

    # 2. Pre-push scan MUST also catch the secret in Commit 1 before it leaves the workstation.
    stdin_line = f"refs/heads/main {head_sha} refs/heads/main {base_sha}\n"
    pre_push_findings = scan_secrets.scan_pre_push_ranges(
        repo_root=repo,
        global_allowlist=global_al,
        rules=rules,
        stdin_text=stdin_line,
    )
    assert any(f.rule_id == "soar-app-key-uuid" and f.commit_sha == leaked_commit_sha for f in pre_push_findings)

    # 3. Full-repo scan MUST catch the historical git blob even though HEAD is clean.
    full_repo_findings = scan_secrets.scan_full_repository(
        repo_root=repo,
        global_allowlist=global_al,
        rules=rules,
    )
    assert any(f.rule_id == "soar-app-key-uuid" for f in full_repo_findings)


def test_catches_secret_inside_gzip_and_base64_mocks(tmp_path: pathlib.Path) -> None:
    """Regression test for PR #1060: secrets inside .gz archives and Base64+gzip mocks are caught."""
    global_al, rules = _load_test_rules()
    repo = _init_git_repo(tmp_path)
    base_sha = _git_head(repo)

    system_key = _generate_system_soar_key()
    mock_json = (
        '{"url": "https://partner-dev.siemplify-soar.com/api/external/v1/GetConnectorsData", '
        f'"headers": {{"AppKey": "{system_key}"}}}}'
    ).encode("utf-8")

    # Write a .gz file in Commit 1 and delete it in Commit 2.
    gz_path = repo / "Connector.json.gz"
    with gzip.open(gz_path, "wb") as gz_file:
        gz_file.write(mock_json)
    subprocess.run(["git", "add", "Connector.json.gz"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add gzipped mock"], cwd=repo, check=True, capture_output=True)

    gz_path.unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Delete gzipped mock"], cwd=repo, check=True, capture_output=True)
    head_sha = _git_head(repo)

    findings = scan_secrets.scan_commit_range(
        repo_root=repo,
        global_allowlist=global_al,
        rules=rules,
        base_ref=base_sha,
        head_ref=head_sha,
        extra_commits=(),
    )
    rule_ids = {f.rule_id for f in findings}
    assert "soar-app-key" in rule_ids
    assert "siemplify-tenant-url" in rule_ids
    assert any("Connector.json.gz!Connector.json" in f.file_path for f in findings)

    # Also verify Base64+gzip embedded literal inside a Python test file.
    compressed_b64 = base64.b64encode(gzip.compress(mock_json)).decode("ascii")
    py_mock = f'MOCK_PAYLOAD = "{compressed_b64}"\n'
    b64_findings = scan_secrets.scan_blob_bytes(
        data=py_mock.encode("utf-8"),
        file_path="tests/test_mock.py",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    assert any(f.rule_id == "soar-app-key" and "#base64@" in f.file_path for f in b64_findings)


def test_catches_force_pushed_extra_commit(tmp_path: pathlib.Path) -> None:
    """Verify --extra-commit catches a secret in an overwritten/force-pushed commit SHA."""
    global_al, rules = _load_test_rules()
    repo = _init_git_repo(tmp_path)
    base_sha = _git_head(repo)

    # Create a commit with a secret, record its SHA, then reset back to base_sha and make a clean commit.
    secret_file = repo / "config.py"
    secret_file.write_text(
        'ACCESS_ID = "p-9876543210fedcba"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "config.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Leaked akeyless id"], cwd=repo, check=True, capture_output=True)
    force_pushed_before_sha = _git_head(repo)

    subprocess.run(["git", "reset", "--hard", base_sha], cwd=repo, check=True, capture_output=True)
    secret_file.write_text('ACCESS_ID = ""\n', encoding="utf-8")
    subprocess.run(["git", "add", "config.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Clean commit after force push"], cwd=repo, check=True, capture_output=True)
    new_head_sha = _git_head(repo)

    findings = scan_secrets.scan_commit_range(
        repo_root=repo,
        global_allowlist=global_al,
        rules=rules,
        base_ref=base_sha,
        head_ref=new_head_sha,
        extra_commits=(force_pushed_before_sha,),
    )
    assert any(f.rule_id == "akeyless-access-credentials" and f.commit_sha == force_pushed_before_sha for f in findings)


def test_detects_exported_playbook_encrypted_password() -> None:
    """Verify encrypted step passwords in exported playbook YAML (IV.ciphertext) are detected."""
    global_al, rules = _load_test_rules()
    iv = base64.b64encode(bytes(range(16))).decode("ascii")
    ciphertext = base64.b64encode(bytes(range(100, 148))).decode("ascii")
    step_yaml = f"""- name: Parameters\n    value: '{{"Archive Password":"{iv}.{ciphertext}","Check":"true"}}'\n"""
    findings = scan_secrets.scan_blob_bytes(
        data=step_yaml.encode("utf-8"),
        file_path="content/playbooks/third_party/community/sample/steps/submit_file_1642e.yaml",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    assert [f.rule_id for f in findings] == ["playbook-encrypted-password"]


def test_pre_push_multi_ref_push_scans_every_ref(tmp_path: pathlib.Path) -> None:
    """Verify a push of a new branch plus an existing branch scans both ranges.

    Regression: `--not` negates every following git revision, so emitting it per new-branch ref
    silently excluded the next ref's commits.
    """
    global_al, rules = _load_test_rules()
    repo = _init_git_repo(tmp_path)
    base_sha = _git_head(repo)

    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True, capture_output=True)
    (repo / "feature.py").write_text('HOST = "https://feature-tenant.siemplify-soar.com"\n', encoding="utf-8")
    subprocess.run(["git", "add", "feature.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature"], cwd=repo, check=True, capture_output=True)
    feature_sha = _git_head(repo)

    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "main.py").write_text('HOST = "https://main-tenant.siemplify-soar.com"\n', encoding="utf-8")
    subprocess.run(["git", "add", "main.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "main"], cwd=repo, check=True, capture_output=True)
    main_sha = _git_head(repo)

    zero = scan_secrets.ZERO_SHA
    stdin_lines = (
        f"refs/heads/feature {feature_sha} refs/heads/feature {zero}\n"
        f"refs/heads/main {main_sha} refs/heads/main {base_sha}\n"
    )
    findings = scan_secrets.scan_pre_push_ranges(repo, global_al, rules, stdin_text=stdin_lines)
    flagged_commits = {f.commit_sha for f in findings if f.rule_id == "siemplify-tenant-url"}
    assert flagged_commits == {feature_sha, main_sha}


def test_detects_encrypted_playbook_zip_and_internal_refs() -> None:
    """Verify encrypted playbook ZIPs and Google-internal references are detected."""
    global_al, rules = _load_test_rules()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("playbook.json", b"{}")
    raw_zip = bytearray(buf.getvalue())
    cd_pos = raw_zip.find(b"PK\x01\x02")
    raw_zip[cd_pos + 8] |= 0x1  # Set ZIP general-purpose encryption bit in central directory

    zip_findings = scan_secrets.scan_blob_bytes(
        data=bytes(raw_zip),
        file_path="content/playbooks/third_party/sample_playbook.zip",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    assert any(f.rule_id == "encrypted-playbook-archive" for f in zip_findings)

    internal_doc = (
        "# Internal reference check\n"
        "# See go/chronicle-secops-design and cl/993203620 and b/501134073\n"
        "# Source: //depot/google3/security/chronicle/handler.py\n"
        "# Host: dev-instance.corp.google.com\n"
        "# Contact: researcher@google.com\n"
    )
    ref_findings = scan_secrets.scan_blob_bytes(
        data=internal_doc.encode("utf-8"),
        file_path="content/response_integrations/google/sample/Manager.py",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    found_rules = {f.rule_id for f in ref_findings}
    assert "google-internal-golink" in found_rules
    assert "google-internal-cl-ref" in found_rules
    assert "google-internal-bug-ref" in found_rules
    assert "google-internal-depot-path" in found_rules
    assert "google-internal-hostname" in found_rules
    assert "google-internal-email" in found_rules


def test_ignores_safe_placeholders_and_allowlisted_files() -> None:
    """Verify zero false positives on placeholders, SHA-256 prefixes, and allowlisted paths."""
    global_al, rules = _load_test_rules()
    ascii_b64 = base64.b64encode(b"abcdefghijklmnopqrstuvwxyz123456").decode("ascii")
    system_key = _generate_system_soar_key()

    safe_content = (
        'API_KEY = "00000000-0000-0000-0000-000000000000"\n'
        'APP_KEY = "YOUR_API_KEY"\n'
        f' ASCII_TEXT_B64 = "{ascii_b64}"\n'
        f'INTEGRITY = "sha256:{system_key}"\n'
        f'SUPPRESSED_KEY = "{system_key}"  # gitleaks:allow\n'
        'URL = "https://example.siemplify-soar.com"\n'
        'CHRONICLE_URL = "https://eu-backstory.backstory.chronicle.security"\n'
        "# Standard Go stdlib import: go/parser and go/ast\n"
    )
    findings = scan_secrets.scan_blob_bytes(
        data=safe_content.encode("utf-8"),
        file_path="content/response_integrations/third_party/safe/client.py",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    assert findings == []

    # Verify @google.com in pyproject.toml is allowlisted per support_email_validation.py.
    pyproject_findings = scan_secrets.scan_blob_bytes(
        data=b'[project]\nauthors = [{email = "maintainer@google.com"}]\n',
        file_path="packages/mp/pyproject.toml",
        commit_sha="HEAD",
        global_allowlist=global_al,
        rules=rules,
    )
    assert pyproject_findings == []


def test_staged_and_install_hooks(tmp_path: pathlib.Path) -> None:
    """Verify --mode staged catches staged secrets and --install-hooks configures core.hooksPath."""
    global_al, rules = _load_test_rules()
    repo = _init_git_repo(tmp_path)

    hooks_dir = repo / ".githooks"
    hooks_dir.mkdir()
    (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (hooks_dir / "pre-push").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    rc = scan_secrets.install_git_hooks(repo)
    assert rc == 0
    hooks_path = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert hooks_path == ".githooks"

    staged_file = repo / "staged_leak.py"
    staged_file.write_text(
        'SOAR_API_KEY = "7c9e6679-7425-40de-944b-e07fc1f90ae7"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "staged_leak.py"], cwd=repo, check=True, capture_output=True)
    staged_findings = scan_secrets.scan_staged_changes(repo, global_al, rules)
    assert len(staged_findings) == 1
    assert staged_findings[0].rule_id == "soar-app-key-uuid"
    assert staged_findings[0].commit_sha == "STAGED"
