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

import base64
import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from enum import Enum
from pathlib import Path
from typing import Any

import magic
import requests
from py7zz.core import find_7z_binary

try:
    from wordlist import wordlist
except ImportError:
    wordlist = None

try:
    import py7zr
    import py7zr.io
    HAS_PY7ZR = True
except Exception:
    HAS_PY7ZR = False

from soar_sdk.SiemplifyDataModel import Attachment
from soar_sdk.SiemplifyUtils import dict_to_flat
from TIPCommon.data_models import CreateEntity
from TIPCommon.rest.soar_api import (
    add_attachment_to_case_wall,
    create_entity,
    get_attachments_metadata,
)
from TIPCommon.types import SingleJson


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


CASE_EVIDENCE_ID = "evidenceId"
ORIG_EMAIL_DESCRIPTION = "This is the original message as EML"
BINARY_NAMES: list[str] = ["7z", "7za", "7zr"]
COMMON_PATHS: list[str] = [
    "/usr/bin",
    "/bin",
    "/usr/local/bin",
    "/usr/sbin",
    "/sbin",
    "/opt/bin",
]


class AttachmentsManager:
    def __init__(self, siemplify):
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER
        self.alert_entities = self.get_alert_entities()
        self.attachments = self._get_attachments()

    def get_alert_entities(self):
        execution_scope = getattr(
            self.siemplify, "execution_scope", ExecutionScope.Alert
        )
        if execution_scope.value == ExecutionScope.Alert.value:
            return getattr(self.siemplify.current_alert, "entities", [])

        alerts = getattr(
            self.siemplify.case, "open_alerts", getattr(self.siemplify.case, "alerts", [])
        )
        entities = []
        for alert in alerts:
            try:
                for entity in alert.entities:
                    entities.append(entity)
            except Exception as e:
                self.logger.error(
                    "Failed to retrieve entities for alert "
                    f"{alert.identifier}: {e}"
                )
        return entities

    def get_attachments(self):
        attachments = []
        for wall_item in self.attachments:
            if wall_item["type"] == 4:
                if not wall_item["alertIdentifier"]:
                    attachments.append(wall_item)

        return attachments

    def get_alert_attachments(self):
        attachments = []
        for wall_item in self.attachments:
            if wall_item["type"] == 4:
                if (
                    self.siemplify.current_alert.identifier
                    == wall_item["alertIdentifier"]
                ):
                    attachments.append(wall_item)
        return attachments

    def _get_attachments(self) -> list[SingleJson]:
        """Get attachments metadata from case wall and alert wall.

        Returns:
            list[SingleJson]: List of attachments metadata
        """
        return [
            attachment.to_json()
            for attachment in get_attachments_metadata(
                self.siemplify, self.siemplify.case.identifier
            )
        ]

    def get_attachments_by_scope(
        self,
        execution_scope: Any,
        attachment_scope_param: str = "Alert",
    ) -> list[SingleJson]:
        """Get attachments based on execution scope and parameter choice.

        Args:
            execution_scope: The current execution scope (Alert or Case).
            attachment_scope_param: The 'Attachment Scope' parameter value
            ('Alert' or 'Case').

        Returns:
            List of filtered attachments metadata.
        """
        if attachment_scope_param.lower() == "case":
            return [
                wall_item for wall_item in self.attachments if wall_item["type"] == 4
            ]

        self.logger.info(f"Running in {execution_scope.name.lower()} scope")
        if execution_scope.value == ExecutionScope.Alert.value:
            return [
                wall_item
                for wall_item in self.attachments
                if wall_item["type"] == 4
                and wall_item.get("alertIdentifier")
                == self.siemplify.current_alert.identifier
            ]

        target_alerts: list[Any] = getattr(self.siemplify.case, "open_alerts", self.siemplify.case.alerts)
        alert_identifiers: set[str] = {alert.identifier for alert in target_alerts}

        return [
            wall_item
            for wall_item in self.attachments
            if wall_item["type"] == 4
            and wall_item.get("alertIdentifier") in alert_identifiers
        ]

    def get_attachment_blobs(self, attachments: list[SingleJson]) -> list[SingleJson]:
        """Retrieve file content/blobs for the given list of attachments.

        Args:
            attachments: List of attachments metadata.

        Returns:
            List of attachments with 'base64_blob' populated.
        """
        processed_attachments = []
        for attachment in attachments:
            try:
                evidence_id = attachment.get(CASE_EVIDENCE_ID)
                if not evidence_id:
                    continue
                attachment_record = self.siemplify.get_attachment(evidence_id)
                attachment_content = attachment_record.getvalue()
                b64 = base64.b64encode(attachment_content)
                attachment["base64_blob"] = b64.decode("ascii")
                processed_attachments.append(attachment)
            except Exception as e:
                att_name = attachment.get(
                    "filename",
                    attachment.get(CASE_EVIDENCE_ID),
                )
                self.logger.error(
                    "Failed to get content for attachment "
                    f"{att_name}: {e}"
                )
                continue
        return processed_attachments

    def add_attachment(
        self,
        filename,
        base64_blob,
        case_id,
        alert_identifier,
        description=None,
        is_favorite=False,
    ):
        """Add attachment
        :param file_path: {string} file path
        :param case_id: {string} case identifier
        :param alert_identifier: {string} alert identifier
        :param description: {string} attachment description
        :param is_favorite: {boolean} is attachment favorite
        :return: {dict} attachment_id
        """
        name, attachment_type = os.path.splitext(os.path.split(filename)[1])
        if not attachment_type:
            attachment_type = ".noext"
        attachment = Attachment(
            case_id,
            alert_identifier,
            base64_blob,
            attachment_type,
            name,
            description,
            is_favorite,
            len(base64.b64decode(base64_blob)),
            len(base64_blob),
        )
        attachment.case_identifier = case_id
        attachment.alert_identifier = alert_identifier
        result = None
        try:
            result = add_attachment_to_case_wall(self.siemplify, attachment)

        except requests.HTTPError as e:
            if "Attachment size" in str(e):
                raise ValueError(
                    "Attachment size should be < 5MB. Original file size: "
                    f"{attachment.orig_size}. Size after encoding: {attachment.size}."
                ) from e

        return result

    def create_file_entities(self, attachments):
        new_entities_w_rel = {}
        updated_entities = []
        for file_entity in attachments:
            entity_identifier = str(file_entity["filename"].strip()).upper()

            try:
                properties = {}
                properties = dict_to_flat(file_entity)
                del properties["filename"]
                if "parent_file" in properties:
                    self.logger.info(
                        f"creating with relation: {entity_identifier} to "
                        f"{properties['parent_file']}"
                    )
                    self.create_entity_with_relation(
                        entity_identifier,
                        properties["parent_file"].upper(),
                        entity_type="FILENAME",
                    )
                    new_entities_w_rel[entity_identifier] = properties
                else:
                    name, attachment_type = os.path.splitext(entity_identifier)
                    found = 0
                    for alert_entity in self.alert_entities:
                        if (
                            alert_entity.identifier == name.upper()
                            and alert_entity.entity_type == "EMAILSUBJECT"
                        ):
                            self.create_entity_with_relation(
                                entity_identifier,
                                alert_entity.identifier,
                                entity_type="FILENAME",
                            )
                            new_entities_w_rel[entity_identifier] = properties
                            found = 1
                            break
                    if found == 0:
                        self.logger.info(
                            f"Creating entity: {entity_identifier} without relationship.",
                        )
                        self.siemplify.add_entity_to_case(
                            entity_identifier,
                            "FILENAME",
                            False,
                            False,
                            True,
                            False,
                            properties,
                        )
            except Exception as e:
                self.logger.error(e)
                raise
            self.logger.info(
                f"Creating entity: {properties['hash_md5']} and linking it to f{entity_identifier}."
            )
            self.create_entity_with_relation(
                properties["hash_md5"],
                entity_identifier,
                entity_type="FILEHASH",
            )

        if new_entities_w_rel:
            self.siemplify.load_case_data()
            time.sleep(3)
            for new_entity in new_entities_w_rel:
                for entity in self.get_alert_entities():
                    if new_entity.strip() == entity.identifier.strip():
                        entity.additional_properties.update(
                            new_entities_w_rel[new_entity],
                        )
                        updated_entities.append(entity)
                        break
            self.logger.info(f"updating entities: {updated_entities}")
            self.siemplify.update_entities(updated_entities)

    def check_if_entity_exists(self, entity_identifier):
        """Verify if entity with such identifier already exists within the case.

        :param target_entities: enumeration of case entities (e.g. siemplify.target_entities)
        :param entity_identifier: identifier of entity, which we're checking
        :return: True if entity with such identier exists already within case; False - otherwise
        """
        for entity in self.alert_entities:
            if entity.identifier.strip() == entity_identifier:
                return True
        return False

    def create_entity_with_relation(
        self,
        new_entity,
        linked_entity,
        entity_type="FILENAME",
    ):
        entity_to_create = CreateEntity(
            case_id=self.siemplify.case_id,
            alert_identifier=self.siemplify.alert_id,
            entity_type=f"{entity_type}",
            entity_identifier=new_entity.upper(),
            entity_to_connect_regex=f"{re.escape(linked_entity.upper())}$",
            types_to_connect=[],
        )
        create_entity(self.siemplify, entity_to_create)

    def extract_zip(self, zip_filename, content, bruteforce=False, pwds=None):
        try:
            return self._extract_zip_native(zip_filename, content, bruteforce, pwds)
        except Exception as e:
            self.logger.info(
                f"Native zipfile extraction failed: {e}. Falling back to 7z/CLI extraction."
            )
            content.seek(0)
            return self.extract_7z(zip_filename, content, bruteforce, pwds)

    def _extract_zip_native(self, zip_filename, content, bruteforce=False, pwds=None):
        with zipfile.ZipFile(content) as attach_zip:
            extracted_files = []
            try:
                for name in attach_zip.namelist():
                    extracted_file = self.attachment(name, attach_zip.read(name))
                    extracted_file["parent_file"] = zip_filename
                    extracted_files.append(extracted_file)
                return extracted_files
            except Exception:
                pass
            pwd = None
            if bruteforce and wordlist:
                for line in io.StringIO(wordlist.WORDLIST).readlines():
                    password = line.strip("\n")
                    try:
                        attach_zip.setpassword(password.encode())
                        for name in attach_zip.namelist():
                            _file = attach_zip.read(name)
                            pwd = password
                            self.logger.info(f"Password found {pwd}")
                            break
                        break
                    except Exception:
                        pass

            if pwds and pwd is None:
                try:
                    found = 0
                    for passwd in pwds:
                        try:
                            attach_zip.setpassword(passwd.encode())
                            for name in attach_zip.namelist():
                                _file = attach_zip.read(name)
                                pwd = passwd
                                self.logger.info(f"Password found {pwd}")
                                found = 1
                                break
                            if found == 1:
                                break
                        except Exception:
                            pass
                except:
                    raise

            try:
                for name in attach_zip.namelist():
                    extracted_file = self.attachment(name, attach_zip.read(name))
                    extracted_file["parent_file"] = zip_filename
                    extracted_files.append(extracted_file)
                return extracted_files
            except RuntimeError:
                raise

    def extract_7z(
        self,
        zip_filename: str,
        content: io.BytesIO,
        bruteforce: bool = False,
        pwds: list[str] | None = None,
    ) -> list[SingleJson]:
        """Extract a 7z archive using py7zr or CLI fallback.

        Args:
            zip_filename: Name of the archive file.
            content: BytesIO buffer of the archive.
            bruteforce: Whether to use wordlist passwords.
            pwds: List of extra passwords to check.

        Returns:
            List of extracted files' metadata.
        """
        unique_passwords: list[str | None] = (
            self._get_password_candidates(bruteforce, pwds)
        )

        extracted: list[SingleJson] | None = (
            self._extract_7z_with_py7zr(
                zip_filename, content, unique_passwords
            )
        )
        if extracted is not None:
            return extracted

        return self._extract_7z_with_cli(
            zip_filename, content, unique_passwords
        )

    def _get_password_candidates(
        self,
        bruteforce: bool,
        pwds: list[str] | None,
    ) -> list[str | None]:
        """Collect and return a unique list of password candidates.

        Args:
            bruteforce: Whether to include wordlist passwords.
            pwds: List of extra passwords to check.

        Returns:
            A unique list of password candidates, starting with None.
        """
        password_candidates: list[str | None] = [None]
        lines: list[str] = []
        if bruteforce and wordlist:
            lines = io.StringIO(wordlist.WORDLIST).readlines()

        for line in lines:
            password_candidates.append(line.rstrip("\r\n"))

        if pwds:
            password_candidates.extend(pwds)

        unique_passwords: list[str | None] = list(
            dict.fromkeys(password_candidates)
        )
        return unique_passwords

    def _extract_7z_with_py7zr(
        self,
        zip_filename: str,
        content: io.BytesIO,
        unique_passwords: list[str | None],
    ) -> list[SingleJson] | None:
        """Attempt to extract 7z archive in-memory using py7zr.

        Args:
            zip_filename: Name of the archive file.
            content: BytesIO buffer of the archive.
            unique_passwords: List of password candidates.

        Returns:
            List of extracted files' metadata, or None if extraction failed
            or py7zr is not available.
        """
        if not HAS_PY7ZR:
            return None

        needs_pwd: bool = self._check_7z_needs_password(content)

        for passwd in unique_passwords:
            if needs_pwd and passwd is None:
                continue

            extracted: list[SingleJson] | None = (
                self._try_py7zr_extract(content, passwd, zip_filename)
            )
            if extracted is not None:
                return extracted

        self.logger.error("Failed to extract 7z archive using py7zr.")
        return None

    def _check_7z_needs_password(self, content: io.BytesIO) -> bool:
        """Check if 7z archive needs a password.

        Args:
            content: BytesIO buffer of the archive.

        Returns:
            True if archive is password-protected, False otherwise.
        """
        try:
            content.seek(0)
            with py7zr.SevenZipFile(content, mode="r") as archive:
                return archive.needs_password()
        except Exception:
            return True

    def _try_py7zr_extract(
        self,
        content: io.BytesIO,
        passwd: str | None,
        zip_filename: str,
    ) -> list[SingleJson] | None:
        """Try to extract 7z using py7zr with a specific password.

        Args:
            content: BytesIO buffer of the archive.
            passwd: Password candidate.
            zip_filename: Name of the archive file.

        Returns:
            List of extracted files' metadata, or None if extraction failed.
        """
        try:
            content.seek(0)
            with py7zr.SevenZipFile(
                content, mode="r", password=passwd
            ) as archive:
                factory: py7zr.io.BytesIOFactory = (
                    py7zr.io.BytesIOFactory(limit=100 * 1024 * 1024)
                )
                archive.extractall(factory=factory)
                return self._parse_py7zr_extracted(
                    archive, factory, zip_filename
                )
        except Exception as e:
            self.logger.debug(f"py7zr extraction failed: {e}")
            return None

    def _parse_py7zr_extracted(
        self,
        archive: Any,
        factory: Any,
        zip_filename: str,
    ) -> list[SingleJson]:
        """Parse extracted files from py7zr factory.

        Args:
            archive: py7zr SevenZipFile instance.
            factory: py7zr BytesIOFactory instance.
            zip_filename: Name of the archive file.

        Returns:
            List of extracted files' metadata.
        """
        extracted_files: list[SingleJson] = []
        for f_info in archive.list():
            self._add_py7zr_file_to_list(
                extracted_files, f_info, factory, zip_filename
            )
        return extracted_files

    def _add_py7zr_file_to_list(
        self,
        extracted_files: list[SingleJson],
        f_info: Any,
        factory: Any,
        zip_filename: str,
    ) -> None:
        """Extract and format a single file info if it is a file.

        Args:
            extracted_files: List to append metadata to.
            f_info: py7zr FileInfo instance.
            factory: py7zr BytesIOFactory instance.
            zip_filename: Name of the archive file.
        """
        if not f_info.is_file:
            return

        obj: Any = factory.get(f_info.filename)
        if not obj:
            return

        obj.seek(0)
        file_content: bytes = obj.read()
        extracted_file: SingleJson = self.attachment(
            f_info.filename, file_content
        )
        extracted_file["parent_file"] = zip_filename
        extracted_files.append(extracted_file)

    def _extract_7z_with_cli(
        self,
        zip_filename: str,
        content: io.BytesIO,
        unique_passwords: list[str | None],
    ) -> list[SingleJson]:
        """Attempt to extract 7z archive using system CLI binaries.

        Args:
            zip_filename: Name of the archive file.
            content: BytesIO buffer of the archive.
            unique_passwords: List of password candidates.

        Returns:
            List of extracted files' metadata.

        Raises:
            RuntimeError: If no CLI binary is found or extraction fails.
        """
        cli_binary: str = self._get_7z_cli_binary()

        for passwd in unique_passwords:
            extracted: list[SingleJson] | None = (
                self._try_cli_extract(
                    cli_binary, content, passwd, zip_filename
                )
            )
            if extracted is not None:
                return extracted

        raise RuntimeError(
            "Failed to extract 7z archive. Wrong password or corrupted "
            "archive."
        )

    def _get_7z_cli_binary(self) -> str:
        """Find the path to the 7z, 7za or 7zr CLI binary.

        Returns:
            The path/name of the available binary.

        Raises:
            RuntimeError: If no binary is found.
        """
        try:
            py7zz_bin: str | None = find_7z_binary()
            if py7zz_bin and os.path.isfile(py7zz_bin) and os.access(py7zz_bin, os.X_OK):
                return py7zz_bin
        except Exception:
            pass

        for bin_name in BINARY_NAMES:
            path: str | None = shutil.which(bin_name)
            if path:
                return path

            for folder in COMMON_PATHS:
                full_path: str = os.path.join(folder, bin_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    return full_path

        raise RuntimeError(
            "No 7z, 7za or 7zr binary found, and py7zr could not extract "
            "the archive."
        )

    def _try_cli_extract(
        self,
        cli_binary: str,
        content: io.BytesIO,
        passwd: str | None,
        zip_filename: str,
    ) -> list[SingleJson] | None:
        """Attempt extraction using 7z CLI for a single password.

        Args:
            cli_binary: The name of the binary.
            content: BytesIO buffer of the archive.
            passwd: Password candidate.
            zip_filename: Name of the archive file.

        Returns:
            List of extracted files' metadata, or None if extraction failed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            temp_archive = temp_dir_path / "archive.7z"
            content.seek(0)
            temp_archive.write_bytes(content.getvalue())

            extracted_dir = temp_dir_path / "extracted"
            cmd: list[str] = self._build_7z_cmd(
                cli_binary, str(temp_archive), str(extracted_dir), passwd
            )

            res: subprocess.CompletedProcess[str] = subprocess.run(
                cmd, capture_output=True, text=True
            )
            if res.returncode != 0:
                return None

            if passwd:
                self.logger.info("Password found")

            return self._read_cli_extracted_files(str(extracted_dir), zip_filename)

    def _build_7z_cmd(
        self,
        cli_binary: str,
        temp_archive: str,
        extracted_dir: str,
        passwd: str | None,
    ) -> list[str]:
        """Construct the 7z CLI extraction command.

        Args:
            cli_binary: The name of the binary.
            temp_archive: Path to temporary archive file.
            extracted_dir: Path to directory to extract to.
            passwd: Password candidate.

        Returns:
            Constructed command list.
        """
        cmd: list[str] = [
            cli_binary,
            "x",
            temp_archive,
            f"-o{extracted_dir}",
            "-y",
        ]
        if passwd:
            cmd.append(f"-p{passwd}")
        else:
            cmd.append("-p-")
        return cmd

    def _read_cli_extracted_files(
        self,
        extracted_dir: str,
        zip_filename: str,
    ) -> list[SingleJson]:
        """Read all extracted files recursively from extraction directory.

        Args:
            extracted_dir: Directory where files were extracted.
            zip_filename: Name of the archive file.

        Returns:
            List of extracted files' metadata.
        """
        extracted_files: list[SingleJson] = []
        extracted_path = Path(extracted_dir)
        for file_path in extracted_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(extracted_path)
                extracted_file = self.attachment(
                    str(rel_path), file_path.read_bytes()
                )
                extracted_file["parent_file"] = zip_filename
                extracted_files.append(extracted_file)
        return extracted_files

    @staticmethod
    def get_file_hash(data: bytes) -> dict[str, str]:
        """Generate hashes of various types (``MD5``, ``SHA-1``, ``SHA-256``, ``SHA-512``)\
        for the provided data.

        Args:
          data (bytes): The data to calculate the hashes on.

        Returns:
          dict: Returns a dict with as key the hash-type and value the calculated hash.

        """
        hashalgo = ["md5", "sha1", "sha256", "sha512"]
        hash_ = {}

        for k in hashalgo:
            ha = getattr(hashlib, k)
            h = ha()
            h.update(data)
            hash_[k] = h.hexdigest()

        return hash_

    @staticmethod
    def get_mime_type(
        data: bytes,
    ) -> tuple[str, str] | tuple[None, None]:
        """Get mime-type information based on the provided bytes object.

        Args:
            data: Binary data.

        Returns:
            typing.Tuple[str, str]: Identified mime information and mime-type. If **magic** is not,
            available returns *None, None*. E.g. *"ELF 64-bit LSB shared object, x86-64,
             version 1 (SYSV)", "application/x-sharedlib"*

        """
        if magic is None:
            return None, None

        detected = magic.detect_from_content(data)
        return detected.name, detected.mime_type

    @staticmethod
    def attachment(filename, content):
        mime_type, mime_type_short = AttachmentsManager.get_mime_type(content)
        attachment_json = {
            "filename": filename,
            "size": len(content),
            "extension": os.path.splitext(filename)[1][1:],
            "hash": {
                "md5": hashlib.md5(content).hexdigest(),
                "sha1": hashlib.sha1(content).hexdigest(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "sha512": hashlib.sha512(content).hexdigest(),
            },
            "mime_type": mime_type,
            "mime_type_short": mime_type_short,
            "raw": base64.b64encode(content).decode(),
        }
        return attachment_json
