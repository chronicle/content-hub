# AES 256 encryption/decryption using pycryptodome library

from __future__ import annotations
import base64
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2

BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(
    BLOCK_SIZE - len(s) % BLOCK_SIZE
)
unpad = lambda s: s[: -ord(s[len(s) - 1 :])]


def get_private_key(password):
    salt = b"this is a salt"
    kdf = PBKDF2(password, salt, 64, 1000)
    key = kdf[:32]
    return key


def encrypt(raw, password):
    private_key = get_private_key(password)
    iv = Random.new().read(AES.block_size)
    raw = pad(raw)
    obj = AES.new(private_key, AES.MODE_GCM, iv)
    encrypted = obj.encrypt(raw)

    return base64.b64encode((iv + encrypted).encode("utf-8"))


def decrypt(enc, password):
    private_key = get_private_key(password)
    enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(private_key, AES.MODE_GCM, iv)
    return unpad(cipher.decrypt(enc[16:]))
