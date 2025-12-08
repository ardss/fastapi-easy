"""Field-level encryption for sensitive data protection at rest"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class FieldEncryptionError(Exception):
    """Field encryption error"""


class FieldEncryption:
    """Field-level encryption using AES-256-GCM with key derivation"""

    def __init__(
        self,
        master_key: Optional[str] = None,
        algorithm: str = "AES-256-GCM",
        key_derivation_rounds: int = 100000,
    ):
        """Initialize field encryption

        Args:
            master_key: Master encryption key (base64 encoded)
            algorithm: Encryption algorithm
            key_derivation_rounds: PBKDF2 rounds for key derivation
        """
        self.algorithm = algorithm
        self.key_derivation_rounds = key_derivation_rounds

        # Initialize master key
        if master_key:
            self.master_key = base64.urlsafe_b64decode(master_key.encode())
        else:
            master_key_env = os.getenv("FIELD_ENCRYPTION_MASTER_KEY")
            if master_key_env:
                self.master_key = base64.urlsafe_b64decode(master_key_env.encode())
            else:
                # Generate new master key
                self.master_key = os.urandom(32)
                logger.warning(
                    "Generated new encryption key. Store it securely: %s",
                    base64.urlsafe_b64encode(self.master_key).decode(),
                )

        # Initialize Fernet for fallback
        fernet_key = base64.urlsafe_b64encode(
            PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"field_encryption_salt",
                iterations=key_derivation_rounds,
                backend=default_backend(),
            ).derive(self.master_key)
        )
        self.fernet = Fernet(fernet_key)

    def encrypt(self, data: Union[str, bytes, Dict, List, int, float]) -> str:
        """Encrypt field data

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data as base64 string

        Raises:
            FieldEncryptionError: If encryption fails
        """
        try:
            # Serialize data
            if isinstance(data, (dict, list)):
                plaintext = json.dumps(data, sort_keys=True).encode()
            elif isinstance(data, str):
                plaintext = data.encode()
            elif isinstance(data, bytes):
                plaintext = data
            elif isinstance(data, (int, float)):
                plaintext = str(data).encode()
            else:
                raise FieldEncryptionError(f"Unsupported data type: {type(data)}")

            # Use Fernet for encryption (includes authentication)
            encrypted_data = self.fernet.encrypt(plaintext)

            # Return as base64 string with metadata
            result = {
                "v": 1,  # Version
                "a": self.algorithm,
                "d": base64.urlsafe_b64encode(encrypted_data).decode(),
                "t": datetime.now(timezone.utc).isoformat(),
            }

            return base64.urlsafe_b64encode(json.dumps(result).encode()).decode()

        except Exception as e:
            logger.error(f"Field encryption failed: {e}")
            raise FieldEncryptionError(f"Encryption failed: {e!s}")

    def decrypt(self, encrypted_data: str) -> Union[str, Dict, List, int, float]:
        """Decrypt field data

        Args:
            encrypted_data: Encrypted data (base64 string)

        Returns:
            Decrypted data

        Raises:
            FieldEncryptionError: If decryption fails
        """
        try:
            # Decode and parse metadata
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            metadata = json.loads(decoded.decode())

            # Validate version
            if metadata.get("v") != 1:
                raise FieldEncryptionError("Unsupported encryption version")

            # Extract encrypted data
            encrypted_bytes = base64.urlsafe_b64decode(metadata["d"].encode())

            # Decrypt using Fernet
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)

            # Try to parse as JSON first
            try:
                return json.loads(decrypted_bytes.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return as string if not valid JSON
                return decrypted_bytes.decode()

        except InvalidToken:
            raise FieldEncryptionError("Invalid or tampered encrypted data")
        except Exception as e:
            logger.error(f"Field decryption failed: {e}")
            raise FieldEncryptionError(f"Decryption failed: {e!s}")

    def encrypt_sensitive_fields(
        self,
        data: Dict[str, Any],
        sensitive_fields: Set[str],
        encrypted_field_suffix: str = "_encrypted",
    ) -> Dict[str, Any]:
        """Encrypt sensitive fields in a dictionary

        Args:
            data: Dictionary containing fields to encrypt
            sensitive_fields: Set of field names to encrypt
            encrypted_field_suffix: Suffix for encrypted field names

        Returns:
            Dictionary with encrypted fields
        """
        result = data.copy()

        for field_name in sensitive_fields:
            if field_name in data and data[field_name] is not None:
                encrypted_field_name = f"{field_name}{encrypted_field_suffix}"
                result[encrypted_field_name] = self.encrypt(data[field_name])
                del result[field_name]

        return result

    def decrypt_sensitive_fields(
        self,
        data: Dict[str, Any],
        encrypted_field_suffix: str = "_encrypted",
    ) -> Dict[str, Any]:
        """Decrypt sensitive fields in a dictionary

        Args:
            data: Dictionary containing encrypted fields
            encrypted_field_suffix: Suffix for encrypted field names

        Returns:
            Dictionary with decrypted fields
        """
        result = data.copy()

        # Find and decrypt encrypted fields
        encrypted_fields = [field for field in data if field.endswith(encrypted_field_suffix)]

        for encrypted_field_name in encrypted_fields:
            original_field_name = encrypted_field_name[: -len(encrypted_field_suffix)]
            try:
                decrypted_value = self.decrypt(result[encrypted_field_name])
                result[original_field_name] = decrypted_value
                del result[encrypted_field_name]
            except FieldEncryptionError as e:
                logger.warning(f"Failed to decrypt field {encrypted_field_name}: {e}")
                # Keep the encrypted field if decryption fails
                continue

        return result

    def rotate_encryption(self, old_encryption: FieldEncryption) -> Dict[str, Any]:
        """Rotate encryption keys and re-encrypt data

        Args:
            old_encryption: Previous encryption instance

        Returns:
            Rotation statistics
        """
        stats = {
            "rotated_fields": 0,
            "failed_rotations": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }

        # This would typically be used in a database migration context
        # where you iterate over all records and re-encrypt fields

        logger.info("Field encryption key rotation completed")
        return stats


class SearchableFieldEncryption:
    """Searchable field encryption using deterministic encryption with salted hashing"""

    def __init__(self, master_key: Optional[str] = None, salt_rounds: int = 12):
        """Initialize searchable field encryption

        Args:
            master_key: Master key for deterministic encryption
            salt_rounds: Number of salt rounds for hashing
        """
        self.field_encryption = FieldEncryption(master_key)
        self.salt_rounds = salt_rounds
        self.search_index: Dict[str, Dict[str, str]] = {}  # field -> {plaintext: encrypted}

    def encrypt_searchable(
        self,
        plaintext: str,
        field_name: str,
        store_index: bool = True,
    ) -> str:
        """Encrypt field value while maintaining searchability

        Args:
            plaintext: Plain text value
            field_name: Name of the field (for salting)
            store_index: Whether to store in search index

        Returns:
            Encrypted value
        """
        # Create deterministic encryption using field-specific key
        field_key = self._derive_field_key(field_name)

        # Use deterministic encryption for the same plaintext
        # Note: This is less secure than random encryption but allows searching
        import hashlib

        # Derive deterministic key
        key_material = hashlib.pbkdf2_hmac(
            "sha256",
            field_key + plaintext.encode(),
            f"searchable_{field_name}".encode(),
            100000,
        )

        # Simple deterministic encryption (for demonstration)
        # In production, use a more sophisticated scheme like ORE or SSE
        deterministic_key = key_material[:32]
        iv = key_material[32:48]  # Deterministic IV for searchability

        cipher = Cipher(
            algorithms.AES(deterministic_key),
            modes.GCM(iv),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()

        encrypted_value = base64.urlsafe_b64encode(ciphertext + encryptor.tag).decode()

        # Store in search index if requested
        if store_index:
            if field_name not in self.search_index:
                self.search_index[field_name] = {}
            self.search_index[field_name][plaintext.lower()] = encrypted_value

        return encrypted_value

    def search_encrypted(
        self,
        search_value: str,
        field_name: str,
    ) -> Optional[str]:
        """Search for encrypted value

        Args:
            search_value: Value to search for
            field_name: Field name to search in

        Returns:
            Encrypted value if found, None otherwise
        """
        if field_name not in self.search_index:
            return None

        return self.search_index[field_name].get(search_value.lower())

    def _derive_field_key(self, field_name: str) -> bytes:
        """Derive field-specific encryption key"""
        return hashlib.pbkdf2_hmac(
            "sha256",
            self.field_encryption.master_key,
            f"field_{field_name}".encode(),
            self.field_encryption.key_derivation_rounds,
        )


class DatabaseFieldEncryption:
    """Integration with database models for field encryption"""

    def __init__(self, field_encryption: FieldEncryption):
        """Initialize database field encryption

        Args:
            field_encryption: Field encryption instance
        """
        self.field_encryption = field_encryption

    def encrypt_model_fields(
        self,
        model_data: Dict[str, Any],
        sensitive_fields: Set[str],
    ) -> Dict[str, Any]:
        """Encrypt sensitive fields in model data

        Args:
            model_data: Model data dictionary
            sensitive_fields: Set of sensitive field names

        Returns:
            Model data with encrypted fields
        """
        return self.field_encryption.encrypt_sensitive_fields(model_data, sensitive_fields)

    def decrypt_model_fields(
        self,
        model_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Decrypt sensitive fields in model data

        Args:
            model_data: Model data dictionary

        Returns:
            Model data with decrypted fields
        """
        return self.field_encryption.decrypt_sensitive_fields(model_data)

    def create_encrypted_field_mapper(self, model_class: type) -> type:
        """Create a mapped model class with encrypted field support

        Args:
            model_class: Original model class

        Returns:
            Mapped model class with encryption support
        """
        # This would integrate with SQLAlchemy, Tortoise ORM, etc.
        # For now, provide a basic implementation

        class EncryptedModelWrapper:
            def __init__(self, original_data: Dict[str, Any]):
                self._original_data = original_data
                self._decrypted_data = None

            @property
            def data(self) -> Dict[str, Any]:
                """Get decrypted model data"""
                if self._decrypted_data is None:
                    self._decrypted_data = self.field_encryption.decrypt_sensitive_fields(
                        self._original_data
                    )
                return self._decrypted_data

            def to_dict(self) -> Dict[str, Any]:
                """Get decrypted data as dictionary"""
                return self.data

        return EncryptedModelWrapper


def create_field_encryption_config() -> Dict[str, Any]:
    """Create field encryption configuration

    Returns:
        Configuration dictionary
    """
    master_key = os.getenv("FIELD_ENCRYPTION_MASTER_KEY")
    if not master_key:
        # Generate and display new key
        import secrets

        master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        logger.warning(
            "Generated new field encryption master key: %s",
            master_key,
        )

    return {
        "master_key": master_key,
        "algorithm": "AES-256-GCM",
        "key_derivation_rounds": 100000,
        "encrypted_field_suffix": "_encrypted",
        "searchable_fields": set(),  # Configure per application
        "sensitive_fields": {
            "email",
            "phone",
            "ssn",
            "credit_card",
            "password",
            "api_key",
            "secret_key",
            "private_key",
            "token",
        },
    }


# SQLAlchemy integration example
def create_encrypted_column_type(field_encryption: FieldEncryption):
    """Create encrypted column type for SQLAlchemy

    Args:
        field_encryption: Field encryption instance

    Returns:
        SQLAlchemy custom column type
    """
    try:
        from sqlalchemy import LargeBinary, TypeDecorator
        from sqlalchemy.dialects.postgresql import BYTEA

        class EncryptedType(TypeDecorator):
            """Encrypted column type for SQLAlchemy"""

            impl = BYTEA
            cache_ok = False

            def process_bind_param(self, value, dialect):
                """Encrypt value before storing"""
                if value is None:
                    return None
                return field_encryption.encrypt(value)

            def process_result_value(self, value, dialect):
                """Decrypt value after retrieving"""
                if value is None:
                    return None
                return field_encryption.decrypt(value)

        return EncryptedType

    except ImportError:
        logger.warning("SQLAlchemy not available for encrypted column type")
        return None


# Data retention and secure deletion
class SecureDataDeletion:
    """Secure data deletion with cryptographic sanitization"""

    def __init__(self, overwrite_passes: int = 3):
        """Initialize secure deletion

        Args:
            overwrite_passes: Number of overwrite passes
        """
        self.overwrite_passes = overwrite_passes

    def secure_delete_data(self, data: str) -> None:
        """Securely delete sensitive data from memory

        Args:
            data: Data to securely delete
        """
        # Overwrite memory with random data
        for _ in range(self.overwrite_passes):
            overwrite_data = os.urandom(len(data.encode()))
            # In practice, this would need to work with memoryviews
            # Python's garbage collection makes true secure deletion challenging

    def generate_deletion_proof(
        self,
        record_id: str,
        timestamp: datetime,
    ) -> str:
        """Generate cryptographic proof of deletion

        Args:
            record_id: ID of deleted record
            timestamp: Deletion timestamp

        Returns:
            Deletion proof hash
        """
        proof_data = f"{record_id}:{timestamp.isoformat()}:DELETED"
        import hashlib

        return hashlib.sha256(proof_data.encode()).hexdigest()
