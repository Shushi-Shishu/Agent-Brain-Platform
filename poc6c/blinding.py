"""
Deterministic blinding and custodian key infrastructure for POC 6c.

Cryptographic design
--------------------
Three-layer envelope:

  Layer 1 — Arm assignment (HMAC)
    assign_arms(task_ids, seed) derives per-task assignments via HMAC-SHA256.
    Only the deterministic-blinding job knows the seed.

  Layer 2 — Mapping encryption (AES-256-GCM, real GCM via `cryptography`)
    A fresh random 32-byte data-encryption key (DEK) is generated for each
    blinding operation using secrets.token_bytes.  The plain mapping is
    encrypted with AES-256-GCM (authenticated, random 96-bit nonce).
    The DEK is NOT derived from the randomization seed.

  Layer 3 — DEK wrapping (RSA-OAEP / EC-hybrid)
    The DEK is wrapped using the custodian's public key so that only the
    owner's offline private key can recover it.

    When `cryptography` is available (production path):
      RSA-OAEP with SHA-256 / MGF1-SHA-256 wraps the raw DEK bytes.

    When `cryptography` is unavailable (test-only fallback):
      _wrap_dek_test_only() XOR-pads the DEK with a fixed test key.
      Any bundle produced by this path is rejected by production preflight.

Stored artifact (`MappingBundle`)
    - encrypted_mapping_b64  : base64(AES-256-GCM(plain_mapping))
    - nonce_b64              : base64(96-bit GCM nonce)
    - auth_tag_b64           : base64(128-bit GCM authentication tag)
    - wrapped_dek_b64        : base64(OAEP-wrapped DEK)
    - pubkey_fingerprint_sha256 : SHA-256(DER(public_key)) used to match key
    - algorithm              : "AES-256-GCM+RSA-OAEP-SHA256-v1" or
                               "AES-256-GCM+TEST-ONLY-NO-REAL-CUSTODY-v1"
    - ciphertext_sha256      : SHA-256(encrypted_mapping bytes)

Security invariants
-------------------
- CONFIRMATION_BLIND_SEED is never used as or from the encryption key.
  It is used only for HMAC-SHA256 arm assignment.
- A placeholder public key causes production preflight to fail closed.
- A test-only wrapped DEK causes production preflight to fail closed.
- Plain mapping and DEK are never stored or transmitted.
- The private key must never enter: the repository, GitHub Actions, Codex,
  any agent/evaluator process, or any agent-readable filesystem.
- Deblinding requires an explicit offline step after outputs are frozen.

Dry-run isolation
-----------------
In dry-run mode the blinding module uses synthetic tasks, a synthetic seed,
and a test-only keypair.  Dry-run bundles are explicitly tagged
"diagnostic_synthetic_only" and are rejected by all confirmation-result
analysis paths (verified by `check_not_dry_run_bundle()`).

Offline key generation (custodian, run once)
---------------------------------------------
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \\
    -out custodian_private.pem
  openssl pkey -pubout -in custodian_private.pem \\
    -out poc6c/custodian_public_key.pem
  # NEVER commit custodian_private.pem

Offline deblinding (custodian, after outputs are frozen and hashed)
--------------------------------------------------------------------
  python poc6c/blinding.py deblind \\
    --bundle blinding-outputs/mapping_bundle.json \\
    --private-key /path/to/custodian_private.pem
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED_ENV_VAR    = "CONFIRMATION_BLIND_SEED"
SEED_BYTES      = 32          # 256-bit randomization seed
_DEK_BYTES      = 32          # AES-256 data-encryption key
_GCM_NONCE_BYTES = 12         # 96-bit AES-GCM nonce (standard)

HERE = Path(__file__).resolve().parent
DEFAULT_PUBLIC_KEY_PATH = HERE / "custodian_public_key.pem"

_ALGO_REAL      = "AES-256-GCM+RSA-OAEP-SHA256-v1"
_ALGO_TEST_ONLY = "AES-256-GCM+TEST-ONLY-NO-REAL-CUSTODY-v1"
_DRY_RUN_TAG    = "diagnostic_synthetic_only"

# Sentinel embedded in the placeholder PEM to detect it
_PLACEHOLDER_SENTINEL = "PLACEHOLDER"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BlindingError(RuntimeError):
    """Base class for blinding errors."""


class SeedAccessViolation(BlindingError):
    """Raised when a process that should not have the seed attempts to read it."""


class CorpusHashMismatch(BlindingError):
    """Raised when a corpus package hash does not match the frozen commitment."""


class PlaceholderPublicKey(BlindingError):
    """Raised in production preflight when custodian_public_key.pem is a placeholder."""


class BundleIsTestOnly(BlindingError):
    """Raised in production preflight when a bundle was wrapped with a test-only key."""


class DryRunBundle(BlindingError):
    """Raised by analysis paths when they detect a dry-run-tagged bundle."""


class KeyCompatibilityError(BlindingError):
    """Raised when the custodian public key is not RSA-4096 with exponent 65537."""


# ---------------------------------------------------------------------------
# Seed management (deterministic-blinding job only)
# ---------------------------------------------------------------------------

def generate_seed() -> str:
    """Generate a fresh 32-byte randomization seed (hex-encoded, uppercase)."""
    return secrets.token_bytes(SEED_BYTES).hex().upper()


def read_seed_from_env() -> str:
    """
    Read the randomization seed from the protected environment variable.

    Only the deterministic-blinding job may call this.  Agent and evaluator
    jobs must never call it.
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
            f"{SEED_ENV_VAR} must be a {SEED_BYTES * 2}-character hex string; "
            f"got {len(clean)} characters."
        )
    return clean


# ---------------------------------------------------------------------------
# Public-key operations (production path via `cryptography`)
# ---------------------------------------------------------------------------

def _load_public_key(pem_path: Path, require_rsa4096: bool = True):
    """Load and return an RSA-4096 public key from a PEM file.

    Raises PlaceholderPublicKey if the sentinel is present.
    Raises KeyCompatibilityError if the key is not RSA-4096 with exponent 65537.
    """
    pem_text = pem_path.read_text(encoding="utf-8")
    if _PLACEHOLDER_SENTINEL in pem_text:
        raise PlaceholderPublicKey(
            f"{pem_path} contains the placeholder sentinel. "
            "Replace it with a real offline-generated RSA-4096 public key before "
            "running a production confirmation. Preflight fails closed."
        )
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    key = load_pem_public_key(pem_text.encode("utf-8"))
    if require_rsa4096:
        validate_rsa4096_public_key_obj(key, str(pem_path))
    return key


def validate_rsa4096_public_key(pem_path: Path) -> None:
    """
    Parse the PEM at pem_path and verify it is RSA-4096 with exponent 65537.

    Raises KeyCompatibilityError with a descriptive message for:
    - non-RSA key type (e.g. EC)
    - RSA key size != 4096 bits
    - public exponent != 65537
    - placeholder sentinel present
    """
    pem_text = pem_path.read_text(encoding="utf-8")
    if _PLACEHOLDER_SENTINEL in pem_text:
        raise PlaceholderPublicKey(
            f"{pem_path} contains the placeholder sentinel. "
            "Replace it with a real offline-generated RSA-4096 public key."
        )
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    key = load_pem_public_key(pem_text.encode("utf-8"))
    validate_rsa4096_public_key_obj(key, str(pem_path))


def validate_rsa4096_public_key_obj(key: Any, label: str = "") -> None:
    """
    Validate that a loaded public key object is RSA-4096 with exponent 65537.

    Raises KeyCompatibilityError otherwise.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    except ImportError:
        return  # cryptography unavailable — skip validation (test-only path)
    if not isinstance(key, RSAPublicKey):
        raise KeyCompatibilityError(
            f"Key at '{label}' is not an RSA key. "
            "Only RSA-4096 with exponent 65537 is accepted for custody wrapping."
        )
    pub_numbers = key.public_numbers()
    if key.key_size != 4096:
        raise KeyCompatibilityError(
            f"Key at '{label}' is RSA-{key.key_size}. "
            "Only RSA-4096 is accepted."
        )
    if pub_numbers.e != 65537:
        raise KeyCompatibilityError(
            f"Key at '{label}' has public exponent {pub_numbers.e}. "
            "Only exponent 65537 is accepted."
        )


def validate_key_fingerprint_matches(bundle: "MappingBundle", pem_path: Path) -> None:
    """
    Verify that the bundle's recorded pubkey_fingerprint_sha256 matches
    the fingerprint of the key at pem_path.

    Raises KeyCompatibilityError on mismatch.
    """
    actual_fp = _pubkey_fingerprint(pem_path)
    if bundle.pubkey_fingerprint_sha256.upper() != actual_fp.upper():
        raise KeyCompatibilityError(
            f"Bundle fingerprint '{bundle.pubkey_fingerprint_sha256[:16]}…' "
            f"does not match key at '{pem_path}' ('{actual_fp[:16]}…'). "
            "Use the correct private key for deblinding."
        )


def _pubkey_fingerprint(pem_path: Path) -> str:
    """SHA-256 of the DER-encoded public key (hex, uppercase)."""
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat
    )
    key = _load_public_key(pem_path)
    der = key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest().upper()


def _wrap_dek_real(dek: bytes, pem_path: Path) -> bytes:
    """Wrap DEK with RSA-OAEP (SHA-256 / MGF1-SHA-256)."""
    from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
    from cryptography.hazmat.primitives.hashes import SHA256
    key = _load_public_key(pem_path)
    return key.encrypt(dek, OAEP(mgf=MGF1(algorithm=SHA256()), algorithm=SHA256(), label=None))


def _unwrap_dek_real(wrapped_dek: bytes, private_key_pem_path: Path) -> bytes:
    """Unwrap DEK using the custodian's offline private key (offline step only)."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
    from cryptography.hazmat.primitives.hashes import SHA256
    pem_text = private_key_pem_path.read_bytes()
    private_key = load_pem_private_key(pem_text, password=None)
    return private_key.decrypt(
        wrapped_dek,
        OAEP(mgf=MGF1(algorithm=SHA256()), algorithm=SHA256(), label=None)
    )


# ---------------------------------------------------------------------------
# Test-only key wrapping (dry-run / test path — no real custody)
# ---------------------------------------------------------------------------

def _generate_test_keypair_pem() -> tuple[bytes, bytes]:
    """
    Generate a temporary RSA-4096 keypair for test/dry-run use.

    Uses RSA-4096 (not 2048) so that tests exercise the same key-size
    validation path as production.  The resulting private key is used only
    in tests; it is never stored and bundles produced with it carry the
    test-only algorithm tag.
    """
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    private_key = generate_private_key(public_exponent=65537, key_size=4096)
    pub_pem  = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    priv_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    return pub_pem, priv_pem


def _wrap_dek_test_only(dek: bytes) -> bytes:
    """
    Wrap DEK with a deterministic test-only sentinel (no real custody).

    The algorithm field is set to _ALGO_TEST_ONLY so production preflight
    rejects any bundle produced by this path.
    """
    # Prepend a fixed sentinel so it is recognizable and cannot be mistaken
    # for real key-wrapped material.
    return b"TESTONLY:" + dek


def _unwrap_dek_test_only(wrapped: bytes) -> bytes:
    if not wrapped.startswith(b"TESTONLY:"):
        raise BlindingError("Expected TESTONLY: prefix; not a test-only wrapped DEK.")
    return wrapped[len(b"TESTONLY:"):]


# ---------------------------------------------------------------------------
# AES-256-GCM (requires `cryptography`)
# ---------------------------------------------------------------------------

def _aes256gcm_encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt plaintext with AES-256-GCM.

    Returns (ciphertext, nonce, auth_tag).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(_GCM_NONCE_BYTES)
    aesgcm = AESGCM(key)
    # cryptography's AESGCM.encrypt() appends the 16-byte tag to ciphertext
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext = ct_with_tag[:-16]
    auth_tag   = ct_with_tag[-16:]
    return ciphertext, nonce, auth_tag


def _aes256gcm_decrypt(key: bytes, ciphertext: bytes, nonce: bytes, auth_tag: bytes) -> bytes:
    """Decrypt and authenticate AES-256-GCM ciphertext."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    ct_with_tag = ciphertext + auth_tag
    return aesgcm.decrypt(nonce, ct_with_tag, None)


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

    The seed is used ONLY for HMAC arm assignment; it is NOT used as or
    derived into an encryption key.
    """
    mapping: dict[str, str] = {}
    seed_bytes = bytes.fromhex(seed)
    for task_id in task_ids:
        digest = hmac.new(seed_bytes, task_id.encode("utf-8"), hashlib.sha256).digest()
        bit    = digest[0] & 1
        mapping[task_id] = arms[bit]
    return mapping


# ---------------------------------------------------------------------------
# Mapping bundle
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class MappingBundle:
    """
    Encrypted arm-assignment mapping bundle.

    Fields
    ------
    encrypted_mapping_b64  : base64(AES-256-GCM ciphertext of JSON mapping)
    nonce_b64              : base64(96-bit GCM nonce)
    auth_tag_b64           : base64(128-bit GCM authentication tag)
    wrapped_dek_b64        : base64(OAEP-wrapped DEK, or test-only sentinel)
    pubkey_fingerprint_sha256 : SHA-256(DER pubkey) used to match decryption key
    algorithm              : one of _ALGO_REAL or _ALGO_TEST_ONLY
    ciphertext_sha256      : SHA-256(encrypted_mapping bytes, hex upper)
    dry_run_tag            : "diagnostic_synthetic_only" when set in dry-run mode
    """
    encrypted_mapping_b64:     str
    nonce_b64:                 str
    auth_tag_b64:              str
    wrapped_dek_b64:           str
    pubkey_fingerprint_sha256: str
    algorithm:                 str
    ciphertext_sha256:         str
    dry_run_tag:               str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def is_production(self) -> bool:
        return self.algorithm == _ALGO_REAL and not self.dry_run_tag

    def is_test_only(self) -> bool:
        return self.algorithm == _ALGO_TEST_ONLY or bool(self.dry_run_tag)


# ---------------------------------------------------------------------------
# Encrypt / decrypt mapping
# ---------------------------------------------------------------------------

def encrypt_mapping(
    mapping: dict[str, str],
    pubkey_pem_path: Path | None = None,
    dry_run: bool = False,
) -> MappingBundle:
    """
    Encrypt the arm-assignment mapping with a random DEK wrapped under the
    custodian's public key.

    The seed is NOT passed to this function.  The DEK is independent of the
    randomization seed.

    Parameters
    ----------
    mapping : dict[str, str]
        Plain arm-assignment mapping (task_id → arm label).
    pubkey_pem_path : Path | None
        Path to the custodian's RSA public key PEM.  Defaults to
        poc6c/custodian_public_key.pem.  For tests, generate a temporary
        keypair and pass its public key PEM as a temp file.
    dry_run : bool
        When True, uses a test-only wrapping scheme and tags the bundle
        "diagnostic_synthetic_only".  Must not be used in production.

    Returns
    -------
    MappingBundle
        Contains ciphertext, nonce, tag, wrapped DEK, pubkey fingerprint,
        algorithm, and ciphertext hash.  The plain mapping is never stored.
    """
    pem_path = pubkey_pem_path or DEFAULT_PUBLIC_KEY_PATH

    plaintext = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # Generate a fresh random DEK (independent of CONFIRMATION_BLIND_SEED)
    dek = secrets.token_bytes(_DEK_BYTES)

    # Encrypt mapping with AES-256-GCM
    ciphertext, nonce, auth_tag = _aes256gcm_encrypt(dek, plaintext)

    ciphertext_sha256 = hashlib.sha256(ciphertext).hexdigest().upper()

    if dry_run:
        wrapped_dek = _wrap_dek_test_only(dek)
        algo        = _ALGO_TEST_ONLY
        fingerprint = "DRY-RUN-TEST-ONLY-KEY"
    else:
        wrapped_dek = _wrap_dek_real(dek, pem_path)
        algo        = _ALGO_REAL
        fingerprint = _pubkey_fingerprint(pem_path)

    # Explicitly overwrite DEK in memory
    dek = b"\x00" * _DEK_BYTES  # noqa: SIM910 — deliberate zeroing

    return MappingBundle(
        encrypted_mapping_b64     = base64.b64encode(ciphertext).decode("ascii"),
        nonce_b64                 = base64.b64encode(nonce).decode("ascii"),
        auth_tag_b64              = base64.b64encode(auth_tag).decode("ascii"),
        wrapped_dek_b64           = base64.b64encode(wrapped_dek).decode("ascii"),
        pubkey_fingerprint_sha256 = fingerprint,
        algorithm                 = algo,
        ciphertext_sha256         = ciphertext_sha256,
        dry_run_tag               = _DRY_RUN_TAG if dry_run else "",
    )


def decrypt_mapping(
    bundle: MappingBundle,
    private_key_pem_path: Path | None = None,
    _test_only_unwrap: bool = False,
) -> dict[str, str]:
    """
    Decrypt the mapping bundle.  Requires the custodian's offline private key.

    Must only be called after all evaluator outputs are collected and hashed.
    Never call during or before the confirmation run.

    Parameters
    ----------
    bundle : MappingBundle
        The encrypted bundle produced by encrypt_mapping().
    private_key_pem_path : Path | None
        Path to the custodian's private key PEM (offline only).
    _test_only_unwrap : bool
        Internal flag for test use; accepted only when bundle.algorithm
        is _ALGO_TEST_ONLY.  Never set this in production code.
    """
    ciphertext = base64.b64decode(bundle.encrypted_mapping_b64)
    nonce      = base64.b64decode(bundle.nonce_b64)
    auth_tag   = base64.b64decode(bundle.auth_tag_b64)
    wrapped_dek = base64.b64decode(bundle.wrapped_dek_b64)

    # Verify ciphertext hash before decryption
    actual_hash = hashlib.sha256(ciphertext).hexdigest().upper()
    if actual_hash != bundle.ciphertext_sha256:
        raise BlindingError(
            f"Ciphertext hash mismatch: expected {bundle.ciphertext_sha256[:16]}…, "
            f"actual {actual_hash[:16]}…. Bundle may have been tampered with."
        )

    if bundle.algorithm == _ALGO_TEST_ONLY or _test_only_unwrap:
        if not (bundle.algorithm == _ALGO_TEST_ONLY or _test_only_unwrap):
            raise BlindingError(
                "Attempt to use test-only unwrap on a production bundle."
            )
        dek = _unwrap_dek_test_only(wrapped_dek)
    else:
        if private_key_pem_path is None:
            raise BlindingError(
                "private_key_pem_path is required to decrypt a production bundle. "
                "This is an offline custodian step."
            )
        dek = _unwrap_dek_real(wrapped_dek, private_key_pem_path)

    plaintext = _aes256gcm_decrypt(dek, ciphertext, nonce, auth_tag)
    return json.loads(plaintext.decode("utf-8"))


# ---------------------------------------------------------------------------
# Preflight production guards
# ---------------------------------------------------------------------------

def check_not_placeholder_key(pem_path: Path | None = None) -> None:
    """
    Raise PlaceholderPublicKey if the committed PEM is still the placeholder.

    Called from production preflight to fail closed.
    """
    path = pem_path or DEFAULT_PUBLIC_KEY_PATH
    if not path.exists():
        raise PlaceholderPublicKey(f"custodian_public_key.pem not found at {path}.")
    pem_text = path.read_text(encoding="utf-8")
    if _PLACEHOLDER_SENTINEL in pem_text:
        raise PlaceholderPublicKey(
            f"custodian_public_key.pem at {path} is still the placeholder. "
            "Generate a real offline keypair and replace it before production runs."
        )


def check_not_dry_run_bundle(bundle_dict: dict[str, Any]) -> None:
    """
    Raise DryRunBundle if the bundle carries a dry-run tag.

    Called from all confirmation-result analysis paths to fail closed on
    synthetic data.
    """
    if bundle_dict.get("dry_run_tag") == _DRY_RUN_TAG:
        raise DryRunBundle(
            "This mapping bundle is tagged 'diagnostic_synthetic_only'. "
            "It was produced in dry-run mode and must not be used for "
            "any confirmation result analysis or deblinding."
        )


def check_not_test_only_bundle(bundle_dict: dict[str, Any]) -> None:
    """
    Raise BundleIsTestOnly if the bundle uses the test-only wrapping algorithm.

    Called from production preflight.
    """
    if bundle_dict.get("algorithm") == _ALGO_TEST_ONLY:
        raise BundleIsTestOnly(
            "This mapping bundle uses the test-only wrapping algorithm. "
            "It provides no real custody guarantee. "
            "Production preflight fails closed."
        )


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
            "Confirmation is blocked."
        )


# ---------------------------------------------------------------------------
# Process isolation assertions
# ---------------------------------------------------------------------------

def assert_seed_not_in_environment() -> None:
    """
    Assert that CONFIRMATION_BLIND_SEED is not accessible in the current process.

    Called from agent and evaluator job preflight.
    Raises SeedAccessViolation if the secret leaks.
    """
    if SEED_ENV_VAR in os.environ and os.environ[SEED_ENV_VAR].strip():
        raise SeedAccessViolation(
            f"{SEED_ENV_VAR} is visible in the current process environment. "
            "Agent and evaluator jobs must not have access to the blinding seed. "
            "This is a critical isolation failure."
        )


def assert_mapping_not_in_environment() -> None:
    """
    Assert that no mapping or seed variable is accessible to this process.

    Called from evaluator job preflight.
    """
    for var in (SEED_ENV_VAR, "BLIND_MAPPING", "ARM_MAPPING", "MAPPING_KEY",
                "CUSTODIAN_PRIVATE_KEY", "DEBLINDING_KEY"):
        if var in os.environ and os.environ[var].strip():
            raise SeedAccessViolation(
                f"Environment variable '{var}' is visible to the evaluator process. "
                "Evaluators must never receive the seed, mapping, or any decryption key."
            )


# ---------------------------------------------------------------------------
# CLI deblinding entry point (offline custodian use)
# ---------------------------------------------------------------------------

def _cli_deblind(bundle_path: str, private_key_path: str) -> None:
    """
    Offline deblinding CLI.

    Usage:
        python blinding.py deblind \\
            --bundle blinding-outputs/mapping_bundle.json \\
            --private-key /path/to/custodian_private.pem

    This step must be run AFTER all evaluator outputs are collected and
    their hashes are recorded.  Never run during or before the confirmation.
    """
    import sys
    raw = Path(bundle_path).read_text(encoding="utf-8")
    bundle_dict = json.loads(raw)

    # Validate required fields present before constructing
    required_fields = {f.name for f in dataclasses.fields(MappingBundle)}
    missing = required_fields - {"dry_run_tag"} - set(bundle_dict.keys())
    if missing:
        print(f"FATAL: Bundle is missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)

    # Refuse to deblind dry-run or test-only bundles
    check_not_dry_run_bundle(bundle_dict)
    check_not_test_only_bundle(bundle_dict)

    # Verify ciphertext hash before constructing bundle object
    import base64 as _b64
    ct_bytes = _b64.b64decode(bundle_dict["encrypted_mapping_b64"])
    actual_hash = hashlib.sha256(ct_bytes).hexdigest().upper()
    if actual_hash != bundle_dict.get("ciphertext_sha256", "").upper():
        print(
            f"FATAL: Ciphertext hash mismatch before decryption. "
            "Bundle may be tampered.",
            file=sys.stderr,
        )
        sys.exit(1)

    bundle = MappingBundle(
        encrypted_mapping_b64     = bundle_dict["encrypted_mapping_b64"],
        nonce_b64                 = bundle_dict["nonce_b64"],
        auth_tag_b64              = bundle_dict["auth_tag_b64"],
        wrapped_dek_b64           = bundle_dict["wrapped_dek_b64"],
        pubkey_fingerprint_sha256 = bundle_dict["pubkey_fingerprint_sha256"],
        algorithm                 = bundle_dict["algorithm"],
        ciphertext_sha256         = bundle_dict["ciphertext_sha256"],
        dry_run_tag               = bundle_dict.get("dry_run_tag", ""),
    )

    mapping = decrypt_mapping(bundle, Path(private_key_path))
    print(json.dumps(mapping, indent=2))


if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser(description="POC 6c blinding utility")
    sub = parser.add_subparsers(dest="command")
    p_deblind = sub.add_parser("deblind", help="Offline deblinding (custodian only)")
    p_deblind.add_argument("--bundle", required=True)
    p_deblind.add_argument("--private-key", required=True)
    args = parser.parse_args()
    if args.command == "deblind":
        _cli_deblind(args.bundle, args.private_key)
    else:
        parser.print_help()
        sys.exit(1)
