# Copyright 2025 Google LLC
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

from __future__ import annotations

import pathlib
import tarfile
import zipfile
from collections.abc import Callable

import pytest
from file_utilities.actions import ExtractArchive
from file_utilities.actions.ExtractArchive import (
    path_to_dict,
    safe_extract_tar,
    safe_extract_zip,
    safe_unpack_archive,
    validate_destination_path,
)
from file_utilities.tests.common import EXPECTED_EXTRACT_SUCCESS_MESSAGE
from file_utilities.tests.core.product import FileUtilitiesProduct
from file_utilities.tests.core.session import FileUtilitiesMockSession
from integration_testing.platform.script_output import MockActionOutput
from TIPCommon.base.action import ExecutionState


def test_validate_destination_path_safe(tmp_path: pathlib.Path) -> None:
    """Validate that safe relative paths resolve correctly inside output_dir."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = validate_destination_path("safe/nested/file.txt", output_dir)
    expected = (output_dir / "safe/nested/file.txt").resolve()
    assert result == expected


def test_validate_destination_path_traversal_double_dot(
    tmp_path: pathlib.Path,
) -> None:
    """Validate that '..' path components raise a ValueError."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="traversal components"):
        validate_destination_path("../escaped.txt", output_dir)

    with pytest.raises(ValueError, match="traversal components"):
        validate_destination_path("sub/../../escaped.txt", output_dir)

    with pytest.raises(ValueError, match="traversal components"):
        validate_destination_path("..\\escaped.txt", output_dir)

    with pytest.raises(ValueError, match="traversal components"):
        validate_destination_path("sub\\..\\..\\escaped.txt", output_dir)


def test_validate_destination_path_absolute(tmp_path: pathlib.Path) -> None:
    """Validate that absolute paths raise a ValueError."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="traversal components"):
        validate_destination_path("/etc/passwd", output_dir)


def test_safe_extract_tar_valid(
    tmp_path: pathlib.Path,
    valid_tar_path: pathlib.Path,
) -> None:
    """Ensure safe extraction works as expected for benign TAR archives."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_extract_tar(valid_tar_path, output_dir)

    assert (output_dir / "hello.txt").is_file()
    assert (output_dir / "hello.txt").read_bytes() == b"Hello World!"
    assert (output_dir / "nested" / "inner.txt").is_file()
    assert (output_dir / "nested" / "inner.txt").read_bytes() == b"Inside subfolder"


def test_safe_extract_tar_traversal_rejected(
    tmp_path: pathlib.Path,
    traversal_tar_path: pathlib.Path,
) -> None:
    """Ensure TAR archives with traversal members are rejected."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)
    outside_file = tmp_path / "escaped.txt"

    with pytest.raises(ValueError, match="traversal components"):
        safe_extract_tar(traversal_tar_path, output_dir)

    assert not outside_file.exists()


def test_safe_extract_tar_symlink_rejected(tmp_path: pathlib.Path) -> None:
    """Ensure TAR archives with symlinks are rejected."""
    archive_path = tmp_path / "symlink.tar"
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "w") as tar:
        link_member = tarfile.TarInfo(name="link_to_etc")
        link_member.type = tarfile.SYMTYPE
        link_member.linkname = "/etc/passwd"
        tar.addfile(link_member)

    with pytest.raises(ValueError, match="Archive links are not allowed"):
        safe_extract_tar(archive_path, output_dir)


def test_safe_extract_tar_hardlink_rejected(tmp_path: pathlib.Path) -> None:
    """Ensure TAR archives with hardlinks are rejected."""
    archive_path = tmp_path / "hardlink.tar"
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "w") as tar:
        link_member = tarfile.TarInfo(name="hardlink_entry")
        link_member.type = tarfile.LNKTYPE
        link_member.linkname = "/bin/bash"
        tar.addfile(link_member)

    with pytest.raises(ValueError, match="Archive links are not allowed"):
        safe_extract_tar(archive_path, output_dir)


def test_safe_extract_tar_special_file_rejected(
    tmp_path: pathlib.Path,
) -> None:
    """Ensure TAR archives with special devices/FIFOs are rejected."""
    archive_path = tmp_path / "fifo.tar"
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "w") as tar:
        fifo_member = tarfile.TarInfo(name="fifo_entry")
        fifo_member.type = tarfile.FIFOTYPE
        tar.addfile(fifo_member)

    with pytest.raises(ValueError, match="Special archive members are not allowed"):
        safe_extract_tar(archive_path, output_dir)


def test_safe_extract_zip_valid(
    tmp_path: pathlib.Path,
    valid_zip_path: pathlib.Path,
) -> None:
    """Ensure safe extraction works as expected for benign ZIP archives."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_extract_zip(valid_zip_path, output_dir)

    assert (output_dir / "doc.txt").is_file()
    assert (output_dir / "doc.txt").read_bytes() == b"Zip file documentation"
    assert (output_dir / "folder" / "nested.txt").is_file()


def test_safe_extract_zip_traversal_rejected(
    tmp_path: pathlib.Path,
    traversal_zip_path: pathlib.Path,
) -> None:
    """Ensure ZIP archives with traversal members are rejected."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)
    outside_file = tmp_path / "pwned.txt"

    with pytest.raises(ValueError, match="traversal components"):
        safe_extract_zip(traversal_zip_path, output_dir)

    assert not outside_file.exists()


def test_safe_extract_zip_symlink_rejected(tmp_path: pathlib.Path) -> None:
    """Ensure ZIP archives with UNIX symlink attributes are rejected."""
    archive_path = tmp_path / "symlink.zip"
    output_dir = tmp_path / "extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "w") as zf:
        zi = zipfile.ZipInfo("symlink_entry")
        zi.external_attr = 0o120777 << 16
        zf.writestr(zi, "/etc/shadow")

    with pytest.raises(ValueError, match="Archive links are not allowed"):
        safe_extract_zip(archive_path, output_dir)


def test_safe_unpack_archive_tar_and_zip(
    tmp_path: pathlib.Path,
    tar_archive_factory: Callable[[pathlib.Path, dict[str, bytes]], pathlib.Path],
    zip_archive_factory: Callable[[pathlib.Path, dict[str, bytes]], pathlib.Path],
) -> None:
    """Ensure safe_unpack_archive transparently handles both TAR and ZIP."""
    tar_path = tar_archive_factory(
        tmp_path / "sample.tar.gz",
        {"from_tar.txt": b"tar_ok"},
    )
    assert tar_path.read_bytes()[:2] == b"\x1f\x8b"
    zip_path = zip_archive_factory(
        tmp_path / "sample.zip",
        {"from_zip.txt": b"zip_ok"},
    )

    tar_out = tmp_path / "tar_out"
    zip_out = tmp_path / "zip_out"
    tar_out.mkdir()
    zip_out.mkdir()

    safe_unpack_archive(tar_path, tar_out)
    safe_unpack_archive(zip_path, zip_out)

    assert (tar_out / "from_tar.txt").read_bytes() == b"tar_ok"
    assert (zip_out / "from_zip.txt").read_bytes() == b"zip_ok"


def test_safe_unpack_archive_unsupported_format(
    tmp_path: pathlib.Path,
) -> None:
    """Ensure non-archive files raise a ValueError."""
    dummy_file = tmp_path / "plain.txt"
    dummy_file.write_text("not an archive")

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="Unsupported or invalid archive"):
        safe_unpack_archive(dummy_file, output_dir)


def test_path_to_dict_structure(tmp_path: pathlib.Path) -> None:
    """Validate structured dictionary representation of directory tree."""
    base = tmp_path / "tree"
    base.mkdir()
    (base / "file1.txt").write_text("content1")
    sub = base / "subdir"
    sub.mkdir()
    (sub / "file2.json").write_text("{}")

    tree = path_to_dict(base)

    assert tree["name"] == "tree"
    assert tree["type"] == "directory"
    assert len(tree["children"]) == 2
    child_names = [child["name"] for child in tree["children"]]
    assert "file1.txt" in child_names
    assert "subdir" in child_names


def test_main_extract_archive_success(
    mock_extract_archive_context: Callable[[str], pathlib.Path],
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    action_output: MockActionOutput,
    valid_tar_path: pathlib.Path,
) -> None:
    """Test full main() execution with product simulator and session."""
    dest_base = mock_extract_archive_context(str(valid_tar_path))

    ExtractArchive.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert EXPECTED_EXTRACT_SUCCESS_MESSAGE in action_output.results.output_message
    assert (dest_base / "valid_sample" / "hello.txt").is_file()
    assert (
        product.get_attachment_blob("valid_sample.tar") == valid_tar_path.read_bytes()
    )
    assert script_session._product is product


def test_main_extract_archive_traversal_fails(
    mock_extract_archive_context: Callable[[str], pathlib.Path],
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    action_output: MockActionOutput,
    traversal_tar_path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    """Test full main() execution fails cleanly on traversal attempt."""
    mock_extract_archive_context(str(traversal_tar_path))

    ExtractArchive.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value == "Failed"
    assert "traversal components" in action_output.results.output_message
    assert not (tmp_path / "escaped.txt").exists()
    assert script_session._product is product


def test_main_extract_archive_dot_stem_escape_fails(
    mock_extract_archive_context: Callable[[str], pathlib.Path],
    tar_archive_factory: Callable[..., pathlib.Path],
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    action_output: MockActionOutput,
    tmp_path: pathlib.Path,
) -> None:
    """Ensure archive named '...tar' cannot escape DEST_DIR via stem '..'."""
    dot_tar_path = tar_archive_factory(
        tmp_path / "...tar",
        {"escaped.txt": b"should never escape"},
    )
    dest_base = mock_extract_archive_context(str(dot_tar_path))

    ExtractArchive.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value == "Failed"
    assert "traversal components" in action_output.results.output_message
    assert not (dest_base.parent / "escaped.txt").exists()
    assert not (dest_base / "escaped.txt").exists()
    assert script_session._product is product


def test_main_extract_archive_dot_stem_equals_root_fails(
    mock_extract_archive_context: Callable[[str], pathlib.Path],
    tar_archive_factory: Callable[..., pathlib.Path],
    product: FileUtilitiesProduct,
    script_session: FileUtilitiesMockSession,
    action_output: MockActionOutput,
    tmp_path: pathlib.Path,
) -> None:
    """Ensure archive named '..tar' (stem '.') cannot target dest_root."""
    dot_tar_path = tar_archive_factory(
        tmp_path / "..tar",
        {"escaped.txt": b"should never extract directly to root"},
    )
    dest_base = mock_extract_archive_context(str(dot_tar_path))

    ExtractArchive.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value == "Failed"
    assert "Invalid archive destination directory name" in (
        action_output.results.output_message
    )
    assert not (dest_base / "escaped.txt").exists()
    assert script_session._product is product
