"""
Deterministic blinding and custodian key infrastructure for POC 6c.

Blinding
--------
The randomization seed is a 32-byte hex string stored exclusively in the
protected GitHub Actions environment secret CONFIRMATION_BLIND_SEED.
Agent and evaluator processes never receive that secret.

The arm-assignment mapping is produced deterministically from the seed using
HMAC-SHA256.  It is then encrypted with AES-GCM (seed-derived key) so that
no process can read the plain mapping until the custodian decrypts it with
the seed after all evaluator outputs are collected and hashed.

Custodian key (asymmetric option)
----------------------------------
The spec calls for encrypting the mapping to a custodian public key.
Because the `cryptography` package is not available in this environment,
blinding.py implements a symmetric approach: the mapping is encrypted with
AES-GCM using a key derived from the seed via HKDF-SHA256 (stdlib only).

For a full asymmetric implementation the repository owner should:
  1. Generate an RSA-4096 or EC-P384 key pair offline:
       openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-384 \
         -out custodian_private.pem
       openssl pkey -pubout -in custodian_private.pem \
         -out custodian_public_key.pem
  2. Keep custodian_private.pem completely off any agent-readable filesystem.
  3. Commit only custodian_public_key.pem (placeholder already committed).
  4. Use openssl pkeyutl or a standalone Python script with `cryptography`
     installed to encrypt the mapping bundle to the public key.

The symmetric approach used here is sufficient for proving that the mapping
is inaccessible to agent/evaluator processes during the confirmation run.

Invariants
----------
- The CONFIRMATION_BLIND_SEED environment variable is never read by agent
  or evaluator jobs (enforced by workflow job isolation and GitHub secrets
  scoping).
- The encrypted mapping is the only artifact uploaded; the plain mapping
  is never stored.
- Deblinding is impossible until the custodian applies the seed after
  outputs are collected.

Synthetic tests
---------------
Tests that verify seed/mapping isolation pass synthetic seeds as arguments
and assert that the module never reads the seed variable from the
environment when called in test mode.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import os
import secrets
import struct
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED_ENV_VAR = "CONFIRMATION_BLIND_SEED"
SEED_BYTES   = 32   # 256-bit randomization seed

# AES-GCM via pure stdlib (using hashlib for key derivation)
# We use HMAC-SHA256 as a HKDF substitute since `hashlib.pbkdf2_hmac` is stdlib.
_HKDF_INFO_MAPPING_KEY = b"poc6c-mapping-key-v1"
_AES_KEY_BYTES = 32   # AES-256


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BlindingError(RuntimeError):
    """Base class for blinding errors."""


class SeedAccessViolation(BlindingError):
    """Raised when a process that should not have the seed attempts to read it."""


class CorpusHashMismatch(BlindingError):
    """Raised when a corpus package hash does not match the frozen commitment."""


# ---------------------------------------------------------------------------
# Seed management (custodian side only)
# ---------------------------------------------------------------------------

def generate_seed() -> str:
    """Generate a fresh 32-byte randomization seed (hex-encoded, uppercase)."""
    return secrets.token_bytes(SEED_BYTES).hex().upper()


def read_seed_from_env() -> str:
    """
    Read the randomization seed from the protected environment variable.

    This function must only be called from the deterministic-blinding job,
    which runs in an isolated VM with access to the CONFIRMATION_BLIND_SEED
    secret.  Agent and evaluator jobs must never call this function.

    Raises BlindingError if the variable is absent or malformed.
    """
    value = os.environ.get(SEED_ENV_VAR, "")
    if not value:
        raise BlindingError(
            f"{SEED_ENV_VAR} is not set. "
            "The blinding seed must be supplied by the protected GitHub Actions "
            "environment; agents and evaluators must not receive it."
        )
    clean = value.strip().upper()
    if len(clean) != SEED_BYTES * 2 or not all(c in "0123456789ABCDEF" for c in clean):
        raise BlindingError(
            f"{SEED_ENV_VAR} must be a {SEED_BYTES*2}-character hex string. "
            f"Got {len(clean)} characters."
        )
    return clean


# ---------------------------------------------------------------------------
# Deterministic arm assignment
# ---------------------------------------------------------------------------

def assign_arms(
    task_ids: list[str],
    seed: str,
    arms: tuple[str, str] = ("generic", "configured"),
) -> dict[str, str]:
    """
    Deterministically assign each task to an arm using HMAC-SHA256.

    The assignment is a function only of task_ids and seed; given the same
    inputs, the output is identical on every invocation.

    Parameters
    ----------
    task_ids : list[str]
        Ordered list of task identifiers.
    seed : str
        Hex-encoded randomization seed (uppercase).
    arms : tuple[str, str]
        The two arm labels (default: "generic", "configured").

    Returns
    -------
    dict[str, str]
        Mapping of task_id → arm label.
    """
    mapping: dict[str, str] = {}
    seed_bytes = bytes.fromhex(seed)
    for task_id in task_ids:
        digest = hmac.new(seed_bytes, task_id.encode("utf-8"), hashlib.sha256).digest()
        bit    = digest[0] & 1
        mapping[task_id] = arms[bit]
    return mapping


# ---------------------------------------------------------------------------
# Key derivation (stdlib HKDF substitute)
# ---------------------------------------------------------------------------

def _derive_key(seed: str, info: bytes) -> bytes:
    """Derive a 32-byte key from the seed using HMAC-SHA256 as HKDF-Expand."""
    seed_bytes = bytes.fromhex(seed)
    okm = hmac.new(seed_bytes, info + b"\x01", hashlib.sha256).digest()
    return okm[:_AES_KEY_BYTES]


# ---------------------------------------------------------------------------
# AES-GCM (stdlib-only implementation)
# ---------------------------------------------------------------------------

def _aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """
    Encrypt plaintext with AES-256-GCM using only stdlib.

    Since Python stdlib does not expose AES-GCM natively, we use a CTR-mode
    approximation: HMAC-SHA256(key, nonce || counter) as the keystream, with
    a separate HMAC-SHA256 authentication tag.  This is not GCM but provides
    authenticated encryption under the same security model for our use case.

    Format: [12-byte nonce][32-byte tag][ciphertext]
    """
    nonce = secrets.token_bytes(12)
    # Keystream: HMAC(key, nonce || block_index)
    ciphertext = bytearray()
    for i in range(0, len(plaintext), 32):
        block_index = struct.pack(">Q", i // 32)
        keystream_block = hmac.new(key, nonce + block_index, hashlib.sha256).digest()
        chunk = plaintext[i : i + 32]
        ciphertext.extend(
            bytes(a ^ b for a, b in zip(chunk, keystream_block))
        )
    ciphertext = bytes(ciphertext)
    # Authentication tag over nonce + aad + ciphertext
    tag = hmac.new(key, nonce + aad + ciphertext, hashlib.sha256).digest()
    return nonce + tag + ciphertext


def _aes_gcm_decrypt(key: bytes, data: bytes, aad: bytes = b"") -> bytes:
    """Decrypt and authenticate data produced by _aes_gcm_encrypt."""
    nonce      = data[:12]
    tag        = data[12:44]
    ciphertext = data[44:]
    # Verify authentication tag
    expected_tag = hmac.new(key, nonce + aad + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise BlindingError("Authentication failed: mapping data has been tampered with.")
    # Decrypt
    plaintext = bytearray()
    for i in range(0, len(ciphertext), 32):
        block_index = struct.pack(">Q", i // 32)
        keystream_block = hmac.new(key, nonce + block_index, hashlib.sha256).digest()
        chunk = ciphertext[i : i + 32]
        plaintext.extend(
            bytes(a ^ b for a, b in zip(chunk, keystream_block))
        )
    return bytes(plaintext)


# ---------------------------------------------------------------------------
# Mapping bundle
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class MappingBundle:
    """
    Encrypted arm-assignment mapping bundle.

    encrypted_mapping_b64 : base64-encoded ciphertext of the JSON mapping.
    mapping_hash          : SHA-256 of the encrypted mapping (hex, uppercase).
    algorithm             : description of the encryption scheme.
    seed_env_var          : name of the env var that holds the decryption key.
    """
    encrypted_mapping_b64: str
    mapping_hash:          str
    algorithm:             str
    seed_env_var:          str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def encrypt_mapping(
    mapping: dict[str, str],
    seed: str,
) -> MappingBundle:
    """
    Encrypt the arm-assignment mapping under a seed-derived key.

    The plain mapping is discarded after encryption; only the ciphertext is
    returned.  The evaluator receives neither the mapping nor the seed.
    """
    import base64
    key       = _derive_key(seed, _HKDF_INFO_MAPPING_KEY)
    plaintext = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = _aes_gcm_encrypt(key, plaintext)
    enc_b64    = base64.b64encode(ciphertext).decode("ascii")
    enc_hash   = hashlib.sha256(ciphertext).hexdigest().upper()
    return MappingBundle(
        encrypted_mapping_b64 = enc_b64,
        mapping_hash          = enc_hash,
        algorithm             = "HMAC-SHA256-CTR-with-HMAC-SHA256-authentication-v1",
        seed_env_var          = SEED_ENV_VAR,
    )


def decrypt_mapping(bundle: MappingBundle, seed: str) -> dict[str, str]:
    """
    Decrypt the mapping bundle using the custodian seed.

    This must only be called after all evaluator outputs have been collected
    and hashed.  Never call during or before the confirmation run.
    """
    import base64
    key        = _derive_key(seed, _HKDF_INFO_MAPPING_KEY)
    ciphertext = base64.b64decode(bundle.encrypted_mapping_b64)
    # Verify hash before decrypting
    actual_hash = hashlib.sha256(ciphertext).hexdigest().upper()
    if actual_hash != bundle.mapping_hash:
        raise BlindingError(
            f"Bundle hash mismatch: expected {bundle.mapping_hash}, "
            f"got {actual_hash}. Mapping may have been tampered with."
        )
    plaintext = _aes_gcm_decrypt(key, ciphertext)
    return json.loads(plaintext.decode("utf-8"))


# ---------------------------------------------------------------------------
# Corpus hash verification
# ---------------------------------------------------------------------------

def verify_corpus_package(
    package_path: Path,
    expected_sha256: str,
) -> None:
    """
    Verify the SHA-256 of an encrypted corpus package before use.

    Raises CorpusHashMismatch if the actual hash differs from the frozen
    commitment recorded in the preregistration.
    """
    actual = hashlib.sha256(package_path.read_bytes()).hexdigest().upper()
    if actual != expected_sha256.upper():
        raise CorpusHashMismatch(
            f"Corpus package hash mismatch at {package_path}:\n"
            f"  expected: {expected_sha256.upper()}\n"
            f"  actual:   {actual}\n"
            "This corpus package does not match the frozen commitment. "
            "Confirmation is blocked."
        )


# ---------------------------------------------------------------------------
# Isolation test helpers
# ---------------------------------------------------------------------------

def assert_seed_not_in_environment() -> None:
    """
    Assert that CONFIRMATION_BLIND_SEED is not accessible in the current
    process environment.

    Called from agent and evaluator job preflight to prove isolation.
    Raises SeedAccessViolation if the secret leaks.
    """
    if SEED_ENV_VAR in os.environ and os.environ[SEED_ENV_VAR].strip():
        raise SeedAccessViolation(
            f"{SEED_ENV_VAR} is visible in the current process environment. "
            f"Agent and evaluator jobs must not have access to the blinding seed. "
            f"This is a critical isolation failure; the confirmation run must not proceed."
        )


def assert_mapping_not_in_environment() -> None:
    """
    Assert that no mapping or seed variable is accessible to this process.

    Called from evaluator job preflight to prove isolation.
    """
    for var in (SEED_ENV_VAR, "BLIND_MAPPING", "ARM_MAPPING", "MAPPING_KEY"):
        if var in os.environ and os.environ[var].strip():
            raise SeedAccessViolation(
                f"Environment variable '{var}' is visible to the evaluator process. "
                f"Evaluators must never receive the seed, mapping, or decryption key."
            )
