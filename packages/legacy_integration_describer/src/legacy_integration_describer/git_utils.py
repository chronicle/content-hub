from __future__ import annotations

import json
import logging
import shutil
import subprocess  # noqa: S404
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from legacy_integration_describer.models import AppConfig, IntegrationRequest

logger = logging.getLogger(__name__)


def find_integration_path(
    identifier: str, repos_config: list[tuple[Path, str]]
) -> tuple[Path | None, str | None, Path | None]:
    """Find the full path to a given integration across configured repositories.

    Returns:
        tuple: Res.

    """
    for repo_dir, rel_base in repos_config:
        rel_path = f"{rel_base}/{identifier}"
        full_path = repo_dir / rel_path
        if full_path.exists():
            return repo_dir, rel_path, full_path
    return None, None, None


def _check_integration_def(
    cwd: Path, commit: str, rel_path: str, identifier: str, version: str
) -> bool:
    """Check if the specific Integration-.def file matches the target version.

    Returns:
        bool: True if matched.

    """
    show_def = subprocess.run(  # noqa: S603
        ["git", "show", f"{commit}:{rel_path}/Integration-{identifier}.def"],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if show_def.returncode == 0:
        try:
            data = json.loads(show_def.stdout)
            if _normalize_version(data.get("Version")) == _normalize_version(version):
                return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Skipping invalid .def file resolving integration version")
    return False


def _check_ls_tree_def(
    cwd: Path, commit: str, rel_path: str, identifier: str, version: str
) -> bool:
    """Search the git history tree for a renamed .def file matching the target version.

    Returns:
        bool: True if matched.

    """
    res_tree = subprocess.run(  # noqa: S603
        ["git", "ls-tree", "-r", "--name-only", commit, rel_path],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if res_tree.returncode != 0:
        return False

    definition_match = None
    for file in res_tree.stdout.splitlines():
        if file.endswith(f"Integration-{identifier}.def"):
            definition_match = file
            break
        if file.endswith(".def"):
            definition_match = file

    if definition_match:
        show_def2 = subprocess.run(  # noqa: S603
            ["git", "show", f"{commit}:{definition_match}"],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if show_def2.returncode == 0:
            try:
                data = json.loads(show_def2.stdout)
                if _normalize_version(data.get("Version")) == _normalize_version(version):
                    return True
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug("Skipping invalid .def file backup")

    return False


def _check_pyproject_toml(cwd: Path, commit: str, rel_path: str, version: str) -> bool:
    """Check if the pyproject.toml matches the target version.

    Returns:
        bool: True if matched.

    """
    show_toml = subprocess.run(  # noqa: S603
        ["git", "show", f"{commit}:{rel_path}/pyproject.toml"],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if show_toml.returncode == 0:
        for line in show_toml.stdout.split("\n"):
            if line.startswith("version = "):
                v = line.split("=")[1].strip().strip('"').strip("'")
                if _normalize_version(v) == _normalize_version(version):
                    return True
    return False


def resolve_commit_for_version(
    cwd: Path, rel_path: str, identifier: str, version: str
) -> str | None:
    """Search deeply through git history retrieving the exact matched source version commit.

    Returns:
        str | None: Commit hash.

    """
    res = subprocess.run(  # noqa: S603
        ["git", "log", "--format=%H", "--", rel_path],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    commits = res.stdout.strip().split("\n")
    for commit in commits:
        if not commit:
            continue

        if _check_integration_def(cwd, commit, rel_path, identifier, version):
            return commit

        if _check_ls_tree_def(cwd, commit, rel_path, identifier, version):
            return commit

        if _check_pyproject_toml(cwd, commit, rel_path, version):
            return commit

    return None


def _normalize_version(v: Any) -> str:  # noqa: ANN401
    v_str = str(v).strip()
    if v_str.endswith(".0"):
        return v_str[:-2]
    return v_str


def read_current_version(pyproject_file: Path, def_file: Path, identifier: str) -> str | None:
    """Parse the active directory's exact version to prevent unnecessary git extraction.

    Returns:
        str | None: Current loc version.

    """
    current_version = None
    if pyproject_file.exists():
        with pyproject_file.open(encoding="utf-8") as f:
            for line in f:
                if line.startswith("version = "):
                    current_version = line.split("=")[1].strip().strip('"').strip("'")
                    break
    elif def_file.exists():
        try:
            with def_file.open(encoding="utf-8") as f:
                data = json.load(f)
                current_version = str(data.get("Version"))
        except Exception as e:  # noqa: F841
            logger.exception("Error reading .def for %s", identifier)

    return current_version


def checkout_integration_version(
    request: IntegrationRequest, dest_dir: Path, config: AppConfig, errors: list[str]
) -> bool:
    """Verify a code source against a destination matching the expected version securely.

    Returns:
        bool: True if completed natively.

    """
    # DOC201
    identifier = request.identifier
    version = request.version
    cwd, rel_path, full_path = find_integration_path(identifier, config.repos_config)

    if not full_path or not cwd or not rel_path:
        msg = f"{identifier}: Integration not found in any specified repository."
        logger.warning(msg)
        errors.append(msg)
        return False

    def_file = full_path / f"Integration-{identifier}.def"
    pyproject_file = full_path / "pyproject.toml"

    current_version = read_current_version(pyproject_file, def_file, identifier)

    logger.info(
        "[%s] Target version: %s, Current version: %s", identifier, version, current_version
    )

    if _normalize_version(current_version) == _normalize_version(version):
        logger.info("[%s] Version matches active tree in %s. Copying.", identifier, full_path)
        shutil.copytree(full_path, dest_dir, dirs_exist_ok=True)
        return True

    logger.info(
        "[%s] Version mismatch. Searching history in %s for exact version %s...",
        identifier,
        cwd,
        version,
    )
    target_commit = resolve_commit_for_version(cwd, rel_path, identifier, version)

    if not target_commit:
        msg = f"{identifier}: Requested version {version} could not be found in git history."
        logger.warning(msg)
        errors.append(msg)
        return False

    logger.info("[%s] Found commit %s. Extracting...", identifier, target_commit)

    Path(dest_dir).mkdir(exist_ok=True, parents=True)
    p1 = subprocess.Popen(  # noqa: S603
        [shutil.which("git") or "git", "archive", target_commit, rel_path],
        cwd=cwd,
        stdout=subprocess.PIPE,
    )
    strip_count = len(rel_path.split("/"))
    p2 = subprocess.Popen(  # noqa: S603
        [
            shutil.which("tar") or "tar",
            "-xf",
            "-",
            "-C",
            str(dest_dir),
            "--strip-components",
            str(strip_count),
        ],
        stdin=p1.stdout,
    )
    if p1.stdout:
        p1.stdout.close()
    p2.communicate()

    if p2.returncode != 0:
        msg = f"{identifier}: Extraction failed at commit {target_commit} for version {version}"
        logger.error(msg)
        errors.append(msg)
        return False

    return True
