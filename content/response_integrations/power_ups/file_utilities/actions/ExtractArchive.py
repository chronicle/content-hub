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

import os
import pathlib
import tarfile
import zipfile
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

DEST_DIR = "/opt/siemplify/siemplify_server/Scripting/FileUtilities/Extract"


def validate_destination_path(
    member_path: str,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    """Validate that an archive member resolves strictly within output_dir.

    Args:
        member_path: Relative path of the archive member.
        output_dir: Canonical base extraction directory.

    Returns:
        Resolved absolute destination Path.

    Raises:
        ValueError: If member_path contains directory traversal or escapes
            output_dir.
    """
    root = output_dir.resolve()
    normalized_path = pathlib.PurePath(member_path.replace("\\", "/"))

    if ".." in normalized_path.parts or member_path.startswith(("/", "\\")):
        raise ValueError(
            f"Archive member contains traversal components: '{member_path}'"
        )

    destination = (root / member_path).resolve()
    if os.path.commonpath([str(root), str(destination)]) != str(root):
        raise ValueError(
            f"Archive member escapes extraction directory: '{member_path}'"
        )

    return destination


def safe_extract_tar(
    archive_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
) -> None:
    """Safely extracts a TAR archive after validating all members.

    Args:
        archive_path: Path to the TAR archive.
        output_dir: Target directory for extraction.

    Raises:
        ValueError: If any member escapes destination or contains links/special
            files.
    """
    root = pathlib.Path(output_dir).resolve()

    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(
                    f"Archive links are not allowed: '{member.name}'"
                )

            if not member.isfile() and not member.isdir():
                raise ValueError(
                    f"Special archive members are not allowed: '{member.name}'"
                )

            validate_destination_path(member.name, root)

        if hasattr(tarfile, "data_filter"):
            tar.extractall(root, filter="data")
        else:
            tar.extractall(root)


def safe_extract_zip(
    archive_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
) -> None:
    """Safely extracts a ZIP archive after validating all members.

    Args:
        archive_path: Path to the ZIP archive.
        output_dir: Target directory for extraction.

    Raises:
        ValueError: If any member escapes destination or contains links.
    """
    root = pathlib.Path(output_dir).resolve()

    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.infolist():
            if (member.external_attr >> 16) & 0o120000 == 0o120000:
                raise ValueError(f"Archive links are not allowed: '{member.filename}'")

            validate_destination_path(member.filename, root)

        zf.extractall(root)


def safe_unpack_archive(
    archive_path: str | pathlib.Path,
    output_dir: str | pathlib.Path,
) -> None:
    """Extract an archive file safely by inspecting and validating all members.

    Supports TAR formats (.tar, .tar.gz, .tgz, .tar.bz2, .tar.xz) and ZIP.

    Args:
        archive_path: Path to the archive file.
        output_dir: Destination directory.

    Raises:
        ValueError: If format is unsupported or malicious members are detected.
    """
    if tarfile.is_tarfile(archive_path):
        safe_extract_tar(archive_path, output_dir)
    elif zipfile.is_zipfile(archive_path):
        safe_extract_zip(archive_path, output_dir)
    else:
        raise ValueError(f"Unsupported or invalid archive format: '{archive_path}'")


def path_to_dict(path: str | pathlib.Path) -> dict[str, Any]:
    """Recursively converts a filesystem path into a structured dictionary.

    Args:
        path: Base directory or file path.

    Returns:
        Dictionary describing file or directory hierarchy.
    """
    str_path = str(path)
    d: dict[str, Any] = {"name": os.path.basename(str_path)}
    _, file_extension = os.path.splitext(str_path)

    if os.path.isdir(str_path):
        d["type"] = "directory"
        d["children"] = [
            path_to_dict(os.path.join(str_path, child))
            for child in sorted(os.listdir(str_path))
        ]
    else:
        d["type"] = "file"
        d["extension"] = file_extension
        d["path"] = str_path

    return d


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    raw_archives = siemplify.parameters.get("Archive") or ""
    archives = [
        archive.strip()
        for archive in raw_archives.split(",")
        if archive.strip()
    ]

    status = EXECUTION_STATE_COMPLETED
    output_message = "output message :"
    result_value: Any = None
    json_result: dict[str, Any] = {"archives": []}
    success_files: list[str] = []
    failed_files: list[str] = []

    for archive in archives:
        archive_path = pathlib.Path(archive)
        archive_name = archive_path.stem
        full_archive_name = archive_path.name

        output_dir = os.path.join(DEST_DIR, archive_name)
        if not os.path.exists(output_dir):
            try:
                pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
            except OSError as err:
                siemplify.LOGGER.error(
                    f"Creation of the directory {output_dir} failed: {err}"
                )
                status = EXECUTION_STATE_FAILED
                json_result["archives"].append(
                    {"success": False, "archive": full_archive_name},
                )
                failed_files.append(archive)
                raise

        try:
            safe_unpack_archive(archive, output_dir)
            files = path_to_dict(output_dir)
            files_w_path = [
                os.path.join(output_dir, f)
                for f in sorted(os.listdir(output_dir))
                if os.path.isfile(os.path.join(output_dir, f))
            ]
            onlyfiles = [
                f
                for f in sorted(os.listdir(output_dir))
                if os.path.isfile(os.path.join(output_dir, f))
            ]
            json_result["archives"].append(
                {
                    "success": True,
                    "archive": full_archive_name,
                    "folder": output_dir,
                    "files": files,
                    "files_with_path": files_w_path,
                    "files_list": onlyfiles,
                },
            )
            output_message = f"\nSuccessfully extracted archive: {full_archive_name}"
            success_files.append(archive)
        except Exception as e:
            siemplify.LOGGER.error("General error performing action:\r")
            siemplify.LOGGER.exception(e)
            status = EXECUTION_STATE_FAILED
            result_value = "Failed"
            output_message += f"\n{e}"
            json_result["archives"].append(
                {"success": False, "archive": full_archive_name},
            )
            failed_files.append(archive)
            raise

    if not failed_files:
        result_value = True

    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
