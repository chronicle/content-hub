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
import email
import subprocess as sp
from pathlib import Path

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

from .base.interfaces import ScriptLogger
from .data_models import SmimeEmailConfig, SmimeType
from .exceptions import ParameterExtractionError, SMIMEMailError
from .utils import create_and_write_to_tempfile

BLOCK_SIZE: int = 16


def get_private_key(password: str) -> bytes:
    """Derive a key from a password.

    Args:
        password: The password to generate the key from

    Returns:
        A byte string

    """
    salt: bytes = b"this is a salt"
    kdf: bytes = PBKDF2(password, salt, dkLen=BLOCK_SIZE * 4)
    key: bytes = kdf[:32]
    return key


def encrypt(data: str, key: str) -> bytes:
    """Encrypt data with the key
    Args:
        data: json string to encrypt
        key: password to use for key generation

    Returns:
        The encrypted message

    """
    private_key: bytes = get_private_key(key)
    iv: bytes = Random.new().read(AES.block_size)
    raw: str = _pad(data)
    aes: AES = AES.new(private_key, AES.MODE_GCM, iv)
    encrypted: bytes = aes.encrypt(raw.encode())
    return base64.b64encode(iv + encrypted)


def decrypt(enc_data: bytes, key: str) -> str:
    """Decrypt data with the password

    Args:
        enc_data: data to encrypt
        key: password to use for key generation

    Returns:
        The decrypted message

    """
    private_key: bytes = get_private_key(key)
    enc_data: bytes = base64.b64decode(enc_data)
    iv: bytes = enc_data[:16]
    cipher: AES = AES.new(private_key, AES.MODE_GCM, iv)
    return _unpad(cipher.decrypt(enc_data[16:])).decode()


def _pad(s: str) -> str:
    """Adjust str length to the multiple of BLOCK_SIZE

    Args:
        s: A string to adjust

    Returns:
        The padded string

    """
    adjusted_block_size: int = BLOCK_SIZE - len(s) % BLOCK_SIZE
    return s + adjusted_block_size * chr(adjusted_block_size)


def _unpad(b: bytes) -> bytes:
    """Adjust bytes length to the multiple of BLOCK_SIZE

    Args:
        b: A bytes object to adjust

    Returns:
        The string unpadded

    """
    return b[: -ord(b[len(b) - 1 :])]


def decrypt_email(
    smime_email_config: SmimeEmailConfig,
    logger: ScriptLogger,
) -> email.message.Message:
    """Check if message is encrypted/signed and decrypt/verify it.

    Args:
        smime_email_config (SmimeEmailConfig): SmimeEmailConfig object contains the
        following fields:
            smime_email_config.email: email.message.Message object
            smime_email_config.private_key_b64 (str): Base64-encoded private key
            smime_email_config.certificate_b64 (str): Base64-encoded certificate
            smime_email_config.ca_certificate_b64 (str): Base64-encoded CA certificate
            smime_email_config.logger: ScriptLogger instance

    Returns:
        email.message.Message: Message object with decrypted/verified message object.

    """
    temp_msg_path = None
    smime_type: SmimeType | None = _get_smime_type(
        msg=smime_email_config.email,
        logger=logger,
    )
    if smime_type is None:
        return smime_email_config.email

    try:
        decrypted_email = None
        email_bytes: bytes = smime_email_config.email.as_bytes()
        temp_msg_path: Path = create_and_write_to_tempfile(email_bytes)
        if smime_type is SmimeType.ENCRYPTED:
            decrypted_email: email.message.Message = _decrypt_smime_message(
                smime_email_config=smime_email_config, message_file_path=temp_msg_path
            )
            smime_type = _get_smime_type(
                msg=decrypted_email,
                logger=logger,
            )

        if smime_type is SmimeType.SIGNED:
            decrypted_email = _verify_smime_message(
                msg=(smime_email_config.email if decrypted_email is None else decrypted_email),
                message_file_path=temp_msg_path,
                ca_certificate_b64=smime_email_config.ca_certificate_b64,
            )

        return decrypted_email

    finally:
        if temp_msg_path is not None:
            temp_msg_path.unlink(missing_ok=True)


def _decrypt_smime_message(
    smime_email_config: SmimeEmailConfig,
    message_file_path: Path,
) -> email.message.Message:
    """Decrypt encrypted SMIME email.

    Args:
        smime_email_config (SmimeEmailConfig): SmimeEmailConfig object.
        message_file_path (Path): Path to temporary message file.

    Returns:
        email.message.Message: Message object with decrypted content.

    """
    key_file_path = None
    cert_file_path = None
    if not smime_email_config.private_key_b64 or not smime_email_config.certificate_b64:
        raise ValueError("Private key and Certificate are required to decrypt S/MIME email.")

    try:
        private_key: bytes = base64.b64decode(smime_email_config.private_key_b64)
        key_file_path: Path = create_and_write_to_tempfile(private_key)
        key_certificate: bytes = base64.b64decode(smime_email_config.certificate_b64)
        cert_file_path: Path = create_and_write_to_tempfile(key_certificate)

        decrypt_command: str = (
            f"openssl smime -decrypt -in {message_file_path} -out {message_file_path} "
            f"-inkey {key_file_path} -certfile {cert_file_path}"
        )

        sp.run(decrypt_command.split(), capture_output=True, text=True, check=True)
        with Path(message_file_path).open(encoding="utf-8") as file:
            decrypted_msg: email.message.Message = email.message_from_string(file.read())

        for key, value in smime_email_config.email.items():
            decrypted_msg.add_header(key, value)

        return decrypted_msg

    except sp.CalledProcessError as e:
        raise SMIMEMailError(f"Failed to decrypt S/MIME email. Error: {e.stderr}") from e

    finally:
        if key_file_path is not None:
            key_file_path.unlink(missing_ok=True)

        if cert_file_path is not None:
            cert_file_path.unlink(missing_ok=True)


def _verify_smime_message(
    msg: email.message.Message,
    message_file_path: Path,
    ca_certificate_b64: str,
) -> email.message.Message:
    """Verify signed SMIME email.

    Args:
        msg (email.message.Message): Message object with signed content
        message_file_path (Path): Path to message file
        ca_certificate_b64 (str): Base64-encoded CA certificate

    Returns:
        email.message.Message: Message object with verified content

    """
    ca_file_path = None
    if not ca_certificate_b64:
        raise ParameterExtractionError("CA certificate is required to verify S/MIME signed email.")

    try:
        ca_certificate = base64.b64decode(ca_certificate_b64)
        ca_file_path: Path = create_and_write_to_tempfile(ca_certificate)
        verify_command = (
            f"openssl smime -verify -in {message_file_path} -CAfile {ca_file_path} "
            f"-out {message_file_path}"
        )

        sp.run(verify_command.split(), capture_output=True, text=True, check=True)
        with Path(message_file_path).open(encoding="utf-8") as file:
            extracted_msg: email.message.Message = email.message_from_string(file.read())

        for key, value in msg.items():
            extracted_msg.add_header(key, value)

        return extracted_msg

    except sp.CalledProcessError as e:
        raise SMIMEMailError(f"Failed to verify S/MIME email. Error: {e.stderr}") from e

    finally:
        if ca_file_path is not None:
            ca_file_path.unlink(missing_ok=True)


def _get_smime_type(
    msg: email.message.Message,
    logger: ScriptLogger,
) -> SmimeType | None:
    """Check if the message is S/MIME encrypted, signed, or neither.

    Args:
        msg (email.message.Message): Message object
        logger (ScriptLogger): ScriptLogger instance

    Returns:
        SmimeType | None: SmimeType enum item if it is an S/MIME message, otherwise None

    """
    content_type: str = msg.get("Content-Type", "").lower()
    logger.info(f'Message Content-Type: "{content_type}"')

    is_encrypted = "application/pkcs7-mime" in content_type
    is_signed = "multipart/signed" in content_type or "signed-data" in content_type

    if is_encrypted:
        return SmimeType.ENCRYPTED

    if is_signed:
        return SmimeType.SIGNED

    return None
