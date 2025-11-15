import base64
import binascii
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from whisperninja.src.utils.utils import (
    get_system_serial_number_language_independent,
    resource_path,
    user_config_path,
)


DEFAULT_LICENSE_RELATIVE_PATH = "whisperninja/config/license.json"
HKDF_INFO = b"whisperninja-license-v1"
HKDF_SALT_SIZE = 16
AESGCM_NONCE_SIZE = 12
AES_KEY_SIZE = 32


class LicenseStorageError(Exception):
    """Base exception for license storage issues."""


class LicenseEncryptionError(LicenseStorageError):
    """Raised when encryption or decryption fails."""


@dataclass
class EncryptedLicenseBlob:
    version: int
    salt: bytes
    nonce: bytes
    ciphertext: bytes

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, Any]) -> "EncryptedLicenseBlob":
        try:
            return cls(
                version=int(payload["version"]),
                salt=base64.b64decode(payload["salt"]),
                nonce=base64.b64decode(payload["nonce"]),
                ciphertext=base64.b64decode(payload["ciphertext"]),
            )
        except (KeyError, ValueError, TypeError, binascii.Error) as exc:
            raise LicenseEncryptionError("Corrupted encrypted license payload") from exc


def _get_license_path(license_file: Optional[str] = None) -> str:
    # If an absolute path is provided, use it directly
    if license_file and os.path.isabs(license_file):
        return license_file
    
    # Use user-writable config directory instead of app bundle
    # This avoids needing special permissions to write to the app bundle
    return user_config_path("license.json")


def _derive_key(salt: bytes) -> bytes:
    serial_number = get_system_serial_number_language_independent()
    if not serial_number:
        raise LicenseEncryptionError("Unable to derive encryption key from system serial number")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        info=HKDF_INFO,
    )
    key_material = hkdf.derive(serial_number.encode("utf-8"))
    return key_material


def _encrypt_license_data(data: Dict[str, Any]) -> EncryptedLicenseBlob:
    salt = os.urandom(HKDF_SALT_SIZE)
    key = _derive_key(salt)
    nonce = os.urandom(AESGCM_NONCE_SIZE)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(data, separators=(",", ":")).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return EncryptedLicenseBlob(version=1, salt=salt, nonce=nonce, ciphertext=ciphertext)


def _decrypt_license_blob(blob: EncryptedLicenseBlob) -> Dict[str, Any]:
    if blob.version != 1:
        raise LicenseEncryptionError(f"Unsupported encrypted license version: {blob.version}")

    key = _derive_key(blob.salt)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(blob.nonce, blob.ciphertext, None)
    except Exception as exc:
        raise LicenseEncryptionError("Failed to decrypt license payload") from exc

    try:
        return json.loads(plaintext.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LicenseEncryptionError("Decrypted license payload is invalid JSON") from exc


def read_license_data(license_file: Optional[str] = None) -> Dict[str, Any]:
    path = _get_license_path(license_file)
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    # Detect encrypted payload
    if isinstance(payload, dict) and {"version", "salt", "nonce", "ciphertext"} <= payload.keys():
        blob = EncryptedLicenseBlob.from_json(payload)
        return _decrypt_license_blob(blob)

    # Backwards compatibility: treat as plaintext payload and re-encrypt on next write
    if isinstance(payload, dict):
        try:
            write_license_data(payload, license_file=license_file)
        except LicenseEncryptionError as exc:
            # If we can't re-encrypt (e.g., missing serial number), return plaintext data
            print(f"Warning: Unable to re-encrypt existing license data: {exc}")
        return payload

    return {}


def write_license_data(data: Dict[str, Any], license_file: Optional[str] = None) -> None:
    path = _get_license_path(license_file)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    blob = _encrypt_license_data(data)

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(blob.to_json(), handle, indent=4)


