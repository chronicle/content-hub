from __future__ import annotations

import hashlib
import io
import zipfile

import paramiko
import pyzipper
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceHTTPException, ZipExtractionError

SSH_PORT = 22
ZIP_MAGIC_HEADER = b"\x50\x4b\x03\x04"


class FileManager:
    """A utility class for managing file operations, including:

    - Retrieving file contents from a remote Unix server via SFTP
    - Checking whether a given path points to a ZIP archive

    This class assumes that the caller will implement the
    `_get_server_sftp_session` method to return an active
    `paramiko.SFTPClient` session.
    """

    def __init__(
        self,
        address: str | None = None,
        username: str = "",
        password: str = "",
    ):
        """Initialize FileManager with remote SSH credentials.

        Args:
            address: Remote host address.
            username: SSH username.
            password: SSH password

        """
        self.address = address
        self.username = username
        self.password = password

    def _get_server_sftp_session(self) -> paramiko.SFTPClient:
        """Create SSH session to remote server

        Returns:
            paramiko.SFTPClient: sftp client object (paramiko data model)

        """
        transport = paramiko.Transport(self.address, SSH_PORT)
        transport.connect(username=self.username, password=self.password)
        return paramiko.SFTPClient.from_transport(transport)

    def get_remote_unix_file_content(self, remote_file_path: str) -> bytes:
        """Retrieve file content (file blob) from remote linux host

        Args:
            remote_file_path: The file path on the remote server
        Returns:
            bytes: The content of the file

        """
        with self._get_server_sftp_session() as sftp_client:
            with sftp_client.open(remote_file_path, mode="rb") as remote_file:
                return remote_file.read()

    @staticmethod
    def is_zip_folder(folder_path: str) -> bool:
        """Check if the given folder path points to a valid ZIP file.

        Args:
            folder_path: The path to the folder or file.

        Return:
            bool: True if it's ZIP file, otherwise False.

        """
        return zipfile.is_zipfile(filename=folder_path)

    @staticmethod
    def is_zip_file(file_obj: io.BytesIO) -> bool:
        """Check if a file-like object is a ZIP archive by magic number."""
        file_obj.seek(0)
        signature = file_obj.read(4)
        file_obj.seek(0)
        return signature == ZIP_MAGIC_HEADER

    @staticmethod
    def extract_single_file_from_zip(
        file: io.BytesIO,
        password: str | None = None,
    ) -> bytes:
        """Extract the content of a single file from ZIP archive.

        Args:
            file: A BytesIO object containing ZIP archive.
            password: Password for encrypted ZIP file (if any).

        Returns:
            bytes: Content of the extracted file.

        Raises:
            ZipExtractionError: If archive is invalid, encrypted incorrectly,
                                or does not contain exactly one file.

        """
        try:
            with pyzipper.AESZipFile(file, "r") as zip_file:
                file_list = [f for f in zip_file.namelist() if not f.endswith("/")]
                if password:
                    zip_file.pwd = password.encode()

                if len(file_list) != 1:
                    raise ZipExtractionError("Archive must contain exactly one file")

                return zip_file.read(file_list[0])
        except GoogleThreatIntelligenceHTTPException as e:
            raise ZipExtractionError(f"Extraction failed. Reason: {e}") from e

    @staticmethod
    def generate_file_hash(file_stream: io.BytesIO) -> str:
        """Generate SHA-256 hash for the given in-memory file-like object.

        Args:
            file_stream: A file-like object containing the file data.

        Returns:
            str: The hexadecimal representation of the SHA-256 hash.

        """
        file_stream.seek(0)
        hash_sha256 = hashlib.sha256()
        while chunk := file_stream.read(8192):
            hash_sha256.update(chunk)
        file_stream.seek(0)
        return hash_sha256.hexdigest()
