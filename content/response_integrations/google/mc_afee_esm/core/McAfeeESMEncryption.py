"""Module for AES 256 encryption/decryption using pycryptodome library
"""
from __future__ import annotations

import base64
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2

BLOCK_SIZE = 16


class McAfeeESMEncryption:
    def get_private_key(self, password: str) -> bytes:
        """Derive a key from a password.

        Args:
            password: The password to generate the key from
        Returns:
            A byte string
        """
        salt = b"this is a salt"
        kdf = PBKDF2(password, salt, 64, 1000)
        key = kdf[:32]
        return key

    def encrypt(self, raw: str, password: str) -> bytes:
        """Encrypt data with the password
        Args:
            raw: json string to encrypt
            password: password to use for key generation
        Returns:
            A bytes object
        """
        private_key = self.get_private_key(password)
        iv = Random.new().read(AES.block_size)
        raw = self._pad(raw)
        obj = AES.new(private_key, AES.MODE_GCM, iv)
        encrypted = obj.encrypt(raw.encode())
        return base64.b64encode(iv + encrypted)

    def decrypt(self, enc: bytes, password: str) -> str:
        """Decrypt data with the password
        Args:
            enc: data to encrypt
            password: password to use for key generation
        Returns:
            (str)
        """
        private_key = self.get_private_key(password)
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(private_key, AES.MODE_GCM, iv)
        return self._unpad(cipher.decrypt(enc[16:])).decode()

    @staticmethod
    def _pad(s: str) -> str:
        """Adjust str length to the multiple of BLOCK_SIZE
        Args:
            s: A string to adjust
        Returns:
            str
        """
        return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(
            BLOCK_SIZE - len(s) % BLOCK_SIZE
        )

    @staticmethod
    def _unpad(b: bytes) -> bytes:
        """Adjust bytes length to the multiple of BLOCK_SIZE
        Args:
            b: A bytes object to adjust
        Returns:
            A bytes object
        """
        return b[: -ord(b[len(b) - 1 :])]
