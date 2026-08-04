"""
Tests for blinding.py — three-layer cryptographic envelope and isolation.

Coverage (Phase 2 + Phase 3 + Phase 4 requirements):
- Seed generation and validation
- Deterministic arm assignment (seed used for HMAC only, NOT encryption key)
- AES-256-GCM mapping encryption with real cryptography library
- RSA-OAEP DEK wrapping round-trip with temporary test keypair
- Ciphertext-hash mismatch detected before decryption
- Authentication-tag tampering detected
- Placeholder public key causes production preflight to fail closed
- Test-only bundle causes production preflight to fail closed
- Dry-run bundle causes analysis path to fail closed
- Dry-run does NOT open frozen confirmation paths
- Seed isolation: assert_seed_not_in_environment
- Mapping/key isolation: assert_mapping_not_in_environment
- Corpus hash mismatch detection
- Cross-arm artifact rejection
- Selection-only invariant
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import blinding as bl
from blinding import (
    BlindingError,
    CorpusHashMismatch,
    DryRunBundle,
    MappingBundle,
    PlaceholderPublicKey,
    SeedAccessViolation,
    BundleIsTestOnly,
    KeyCompatibilityError,
    SEED_ENV_VAR,
    SEED_BYTES,
    _ALGO_REAL,
    _ALGO_TEST_ONLY,
    _DRY_RUN_TAG,
    _PLACEHOLDER_SENTINEL,
    DEFAULT_PUBLIC_KEY_PATH,
    assign_arms,
    assert_mapping_not_in_environment,
    assert_seed_not_in_environment,
    check_not_dry_run_bundle,
    check_not_placeholder_key,
    check_not_test_only_bundle,
    decrypt_mapping,
    encrypt_mapping,
    generate_seed,
    read_seed_from_env,
    verify_corpus_package,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_TASKS = [f"SRCH-C{i:03d}" for i in range(1, 33)]


def _make_temp_real_keypair():
    """Generate a temporary RSA-4096 keypair for test use; returns (pub_pem_path, priv_pem_path)."""
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    priv = generate_private_key(public_exponent=65537, key_size=4096)
    pub_pem  = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    priv_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    tmp_pub  = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_priv = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_pub.write(pub_pem);  tmp_pub.close()
    tmp_priv.write(priv_pem); tmp_priv.close()
    return Path(tmp_pub.name), Path(tmp_priv.name)


# ---------------------------------------------------------------------------
# Seed generation
# ---------------------------------------------------------------------------

class TestSeedGeneration:
    def test_seed_is_uppercase_hex(self):
        s = generate_seed()
        assert s == s.upper()
        assert all(c in "0123456789ABCDEF" for c in s)

    def test_seed_correct_length(self):
        assert len(generate_seed()) == SEED_BYTES * 2

    def test_seeds_are_unique(self):
        assert generate_seed() != generate_seed()

    def test_read_seed_from_env_valid(self):
        seed = generate_seed()
        with patch.dict(os.environ, {SEED_ENV_VAR: seed}):
            assert read_seed_from_env() == seed

    def test_read_seed_raises_absent(self):
        env = {k: v for k, v in os.environ.items() if k != SEED_ENV_VAR}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(BlindingError):
                read_seed_from_env()

    def test_read_seed_raises_empty(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: ""}):
            with pytest.raises(BlindingError):
                read_seed_from_env()

    def test_read_seed_raises_malformed(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: "NOTVALID"}):
            with pytest.raises(BlindingError):
                read_seed_from_env()


# ---------------------------------------------------------------------------
# Arm assignment (seed used for HMAC only, never for encryption)
# ---------------------------------------------------------------------------

class TestArmAssignment:
    def test_deterministic(self):
        seed = generate_seed()
        assert assign_arms(SAMPLE_TASKS, seed) == assign_arms(SAMPLE_TASKS, seed)

    def test_different_seeds_different_assignments(self):
        m1 = assign_arms(SAMPLE_TASKS, generate_seed())
        m2 = assign_arms(SAMPLE_TASKS, generate_seed())
        assert m1 != m2

    def test_all_tasks_assigned(self):
        m = assign_arms(SAMPLE_TASKS, generate_seed())
        assert set(m.keys()) == set(SAMPLE_TASKS)

    def test_valid_arm_labels(self):
        m = assign_arms(SAMPLE_TASKS, generate_seed())
        assert all(v in ("generic", "configured") for v in m.values())

    def test_both_arms_represented(self):
        m = assign_arms(SAMPLE_TASKS, generate_seed())
        assert "generic" in m.values() and "configured" in m.values()

    def test_seed_not_used_as_encryption_key(self):
        """assign_arms must not return an encryption key or touch blinding crypto."""
        seed = generate_seed()
        mapping = assign_arms(SAMPLE_TASKS, seed)
        # The mapping itself must not contain the seed or any derived key material
        m_str = json.dumps(mapping)
        assert seed not in m_str
        assert seed.lower() not in m_str.lower()


# ---------------------------------------------------------------------------
# Three-layer encryption round-trip with real keypair
# ---------------------------------------------------------------------------

class TestRealKeyEncryption:
    def setup_method(self):
        self.pub_path, self.priv_path = _make_temp_real_keypair()

    def teardown_method(self):
        for p in (self.pub_path, self.priv_path):
            try:
                p.unlink()
            except Exception:
                pass

    def test_encrypt_decrypt_roundtrip(self):
        seed = generate_seed()
        mapping = assign_arms(SAMPLE_TASKS, seed)
        bundle = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        recovered = decrypt_mapping(bundle, private_key_pem_path=self.priv_path)
        assert recovered == mapping

    def test_bundle_is_production_algorithm(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        assert bundle.algorithm == _ALGO_REAL

    def test_bundle_has_all_required_fields(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        d = bundle.to_dict()
        for field in ("encrypted_mapping_b64", "nonce_b64", "auth_tag_b64",
                      "wrapped_dek_b64", "pubkey_fingerprint_sha256",
                      "algorithm", "ciphertext_sha256"):
            assert field in d, f"Missing field: {field}"

    def test_bundle_dry_run_tag_absent_for_real(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        assert bundle.dry_run_tag == ""

    def test_nonce_is_random_across_encryptions(self):
        mapping = {"T1": "generic"}
        b1 = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        b2 = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        assert b1.nonce_b64 != b2.nonce_b64

    def test_dek_is_independent_of_seed(self):
        """Wrapped DEK must differ between calls — it is not seed-derived."""
        seed = generate_seed()
        mapping = assign_arms(["T1"], seed)
        b1 = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        b2 = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        # Independent fresh random DEKs produce different wrapped material
        assert b1.wrapped_dek_b64 != b2.wrapped_dek_b64

    def test_ciphertext_hash_in_bundle(self):
        import base64
        bundle = encrypt_mapping({"T1": "configured"}, pubkey_pem_path=self.pub_path)
        ct = base64.b64decode(bundle.encrypted_mapping_b64)
        expected = hashlib.sha256(ct).hexdigest().upper()
        assert bundle.ciphertext_sha256 == expected

    def test_is_production_returns_true(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        assert bundle.is_production()

    def test_wrong_private_key_fails(self):
        """Decryption with a different private key must fail."""
        mapping = {"T1": "generic"}
        bundle = encrypt_mapping(mapping, pubkey_pem_path=self.pub_path)
        wrong_pub, wrong_priv = _make_temp_real_keypair()
        try:
            with pytest.raises(Exception):  # ValueError or InvalidSignature from cryptography
                decrypt_mapping(bundle, private_key_pem_path=wrong_priv)
        finally:
            wrong_pub.unlink(); wrong_priv.unlink()

    def test_missing_private_key_path_raises(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        with pytest.raises(BlindingError):
            decrypt_mapping(bundle, private_key_pem_path=None)


# ---------------------------------------------------------------------------
# Ciphertext integrity
# ---------------------------------------------------------------------------

class TestCiphertextIntegrity:
    def setup_method(self):
        self.pub_path, self.priv_path = _make_temp_real_keypair()

    def teardown_method(self):
        for p in (self.pub_path, self.priv_path):
            try: p.unlink()
            except Exception: pass

    def test_tampered_ciphertext_fails(self):
        import base64
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        raw = bytearray(base64.b64decode(bundle.encrypted_mapping_b64))
        raw[-1] ^= 0xFF
        bad = MappingBundle(
            encrypted_mapping_b64     = base64.b64encode(bytes(raw)).decode(),
            nonce_b64                 = bundle.nonce_b64,
            auth_tag_b64              = bundle.auth_tag_b64,
            wrapped_dek_b64           = bundle.wrapped_dek_b64,
            pubkey_fingerprint_sha256 = bundle.pubkey_fingerprint_sha256,
            algorithm                 = bundle.algorithm,
            ciphertext_sha256         = bundle.ciphertext_sha256,
        )
        with pytest.raises(BlindingError):
            decrypt_mapping(bad, private_key_pem_path=self.priv_path)

    def test_wrong_ciphertext_hash_detected_before_decryption(self):
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        bad = MappingBundle(
            encrypted_mapping_b64     = bundle.encrypted_mapping_b64,
            nonce_b64                 = bundle.nonce_b64,
            auth_tag_b64              = bundle.auth_tag_b64,
            wrapped_dek_b64           = bundle.wrapped_dek_b64,
            pubkey_fingerprint_sha256 = bundle.pubkey_fingerprint_sha256,
            algorithm                 = bundle.algorithm,
            ciphertext_sha256         = "A" * 64,
        )
        with pytest.raises(BlindingError, match="hash mismatch"):
            decrypt_mapping(bad, private_key_pem_path=self.priv_path)

    def test_tampered_auth_tag_fails(self):
        import base64
        bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=self.pub_path)
        raw_tag = bytearray(base64.b64decode(bundle.auth_tag_b64))
        raw_tag[0] ^= 0xFF
        bad = MappingBundle(
            encrypted_mapping_b64     = bundle.encrypted_mapping_b64,
            nonce_b64                 = bundle.nonce_b64,
            auth_tag_b64              = base64.b64encode(bytes(raw_tag)).decode(),
            wrapped_dek_b64           = bundle.wrapped_dek_b64,
            pubkey_fingerprint_sha256 = bundle.pubkey_fingerprint_sha256,
            algorithm                 = bundle.algorithm,
            ciphertext_sha256         = bundle.ciphertext_sha256,
        )
        with pytest.raises(Exception):  # InvalidTag from cryptography
            decrypt_mapping(bad, private_key_pem_path=self.priv_path)


# ---------------------------------------------------------------------------
# Placeholder public key — fails closed (Phase 2 requirement 7)
# ---------------------------------------------------------------------------

class TestPlaceholderKey:
    def test_placeholder_detected_on_encrypt(self):
        """encrypt_mapping must fail closed when the PEM contains the placeholder sentinel."""
        with tempfile.NamedTemporaryFile(suffix=".pem", mode="w", delete=False) as f:
            f.write(f"-----BEGIN PUBLIC KEY-----\n{_PLACEHOLDER_SENTINEL}: fake\n-----END PUBLIC KEY-----\n")
            pem_path = Path(f.name)
        try:
            with pytest.raises(PlaceholderPublicKey):
                encrypt_mapping({"T1": "generic"}, pubkey_pem_path=pem_path)
        finally:
            pem_path.unlink()

    def test_placeholder_detected_by_check_function(self):
        with tempfile.NamedTemporaryFile(suffix=".pem", mode="w", delete=False) as f:
            f.write(f"-----BEGIN PUBLIC KEY-----\n{_PLACEHOLDER_SENTINEL}: fake\n-----END PUBLIC KEY-----\n")
            pem_path = Path(f.name)
        try:
            with pytest.raises(PlaceholderPublicKey):
                check_not_placeholder_key(pem_path)
        finally:
            pem_path.unlink()

    def test_default_pem_is_placeholder(self):
        """The committed custodian_public_key.pem must still be a placeholder."""
        with pytest.raises(PlaceholderPublicKey):
            check_not_placeholder_key()

    def test_real_key_passes_check(self):
        pub_path, priv_path = _make_temp_real_keypair()
        try:
            check_not_placeholder_key(pub_path)  # must not raise
        finally:
            pub_path.unlink(); priv_path.unlink()


# ---------------------------------------------------------------------------
# Test-only bundle — rejected by production preflight (Phase 2 requirement 8)
# ---------------------------------------------------------------------------

class TestBundleIsTestOnly:
    def test_dry_run_produces_test_only_algorithm(self):
        bundle = encrypt_mapping({"T1": "generic"}, dry_run=True)
        assert bundle.algorithm == _ALGO_TEST_ONLY

    def test_test_only_bundle_rejected_by_preflight(self):
        bundle = encrypt_mapping({"T1": "generic"}, dry_run=True)
        with pytest.raises(BundleIsTestOnly):
            check_not_test_only_bundle(bundle.to_dict())

    def test_real_bundle_passes_test_only_check(self):
        pub_path, priv_path = _make_temp_real_keypair()
        try:
            bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=pub_path)
            check_not_test_only_bundle(bundle.to_dict())  # must not raise
        finally:
            pub_path.unlink(); priv_path.unlink()

    def test_test_only_round_trip(self):
        """Dry-run bundles round-trip via the test-only unwrap path."""
        mapping = assign_arms(["T1", "T2"], generate_seed())
        bundle = encrypt_mapping(mapping, dry_run=True)
        recovered = decrypt_mapping(bundle, _test_only_unwrap=True)
        assert recovered == mapping


# ---------------------------------------------------------------------------
# Dry-run isolation (Phase 4)
# ---------------------------------------------------------------------------

class TestDryRunIsolation:
    def test_dry_run_bundle_has_tag(self):
        bundle = encrypt_mapping({"T1": "generic"}, dry_run=True)
        assert bundle.dry_run_tag == _DRY_RUN_TAG

    def test_dry_run_bundle_rejected_by_analysis_path(self):
        bundle = encrypt_mapping({"T1": "generic"}, dry_run=True)
        with pytest.raises(DryRunBundle):
            check_not_dry_run_bundle(bundle.to_dict())

    def test_real_bundle_passes_analysis_path(self):
        pub_path, priv_path = _make_temp_real_keypair()
        try:
            bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=pub_path)
            check_not_dry_run_bundle(bundle.to_dict())  # must not raise
        finally:
            pub_path.unlink(); priv_path.unlink()

    def test_dry_run_does_not_open_frozen_task_file(self):
        """Dry-run encrypt_mapping must not read tasks_v1.json."""
        frozen_task_path = HERE / "confirmation" / "tasks_v1.json"
        read_calls = []
        real_open = open

        def mock_open(path, *args, **kwargs):
            if str(frozen_task_path) in str(path):
                read_calls.append(str(path))
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            encrypt_mapping({"T1": "generic"}, dry_run=True)

        assert not read_calls, (
            f"dry_run encrypt_mapping opened frozen task file: {read_calls}"
        )

    def test_dry_run_does_not_open_confirmation_rubric(self):
        """Dry-run must not open EVALUATION_RUBRIC_V1.md."""
        rubric_path = HERE / "confirmation" / "EVALUATION_RUBRIC_V1.md"
        read_calls = []
        real_open = open

        def mock_open(path, *args, **kwargs):
            if str(rubric_path) in str(path):
                read_calls.append(str(path))
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            encrypt_mapping({"T1": "generic"}, dry_run=True)

        assert not read_calls, (
            f"dry_run encrypt_mapping opened confirmation rubric: {read_calls}"
        )

    def test_dry_run_does_not_open_sealed_labels(self):
        """Dry-run must not open any file under confirmation/sealed/."""
        sealed_dir = HERE / "confirmation" / "sealed"
        read_calls = []
        real_open = open

        def mock_open(path, *args, **kwargs):
            if str(sealed_dir) in str(path):
                read_calls.append(str(path))
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            encrypt_mapping({"T1": "generic"}, dry_run=True)

        assert not read_calls, (
            f"dry_run encrypt_mapping opened sealed file: {read_calls}"
        )


# ---------------------------------------------------------------------------
# Corpus hash mismatch
# ---------------------------------------------------------------------------

class TestCorpusHashMismatch:
    def test_matching_hash_passes(self, tmp_path):
        pkg = tmp_path / "corpus.enc"
        pkg.write_bytes(b"test content")
        expected = hashlib.sha256(b"test content").hexdigest().upper()
        verify_corpus_package(pkg, expected)  # must not raise

    def test_mismatched_hash_raises(self, tmp_path):
        pkg = tmp_path / "corpus.enc"
        pkg.write_bytes(b"test content")
        with pytest.raises(CorpusHashMismatch):
            verify_corpus_package(pkg, "A" * 64)


# ---------------------------------------------------------------------------
# Seed isolation
# ---------------------------------------------------------------------------

class TestSeedIsolation:
    def test_absent_seed_passes(self):
        env = {k: v for k, v in os.environ.items() if k != SEED_ENV_VAR}
        with patch.dict(os.environ, env, clear=True):
            assert_seed_not_in_environment()  # must not raise

    def test_present_seed_raises(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: generate_seed()}):
            with pytest.raises(SeedAccessViolation):
                assert_seed_not_in_environment()

    def test_empty_seed_var_does_not_raise(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: ""}):
            assert_seed_not_in_environment()  # empty ≠ present


# ---------------------------------------------------------------------------
# Mapping/key isolation (evaluator)
# ---------------------------------------------------------------------------

class TestMappingIsolation:
    def test_no_sensitive_vars_passes(self):
        clean = {
            k: v for k, v in os.environ.items()
            if k not in (SEED_ENV_VAR, "BLIND_MAPPING", "ARM_MAPPING",
                         "MAPPING_KEY", "CUSTODIAN_PRIVATE_KEY", "DEBLINDING_KEY")
        }
        with patch.dict(os.environ, clean, clear=True):
            assert_mapping_not_in_environment()  # must not raise

    @pytest.mark.parametrize("var", [
        SEED_ENV_VAR, "BLIND_MAPPING", "ARM_MAPPING",
        "MAPPING_KEY", "CUSTODIAN_PRIVATE_KEY", "DEBLINDING_KEY",
    ])
    def test_each_sensitive_var_raises(self, var):
        with patch.dict(os.environ, {var: "some_value"}):
            with pytest.raises(SeedAccessViolation):
                assert_mapping_not_in_environment()


# ---------------------------------------------------------------------------
# Cross-arm artifact rejection
# ---------------------------------------------------------------------------

class TestCrossArmRejection:
    def test_different_seeds_cannot_share_ciphertext(self):
        """The mapping produced from seed A must not decrypt correctly when the bundle
        was encrypted with seed B's mapping — different plaintexts encrypt differently."""
        seed_a, seed_b = generate_seed(), generate_seed()
        m_a = assign_arms(["T1", "T2"], seed_a)
        m_b = assign_arms(["T1", "T2"], seed_b)
        pub_path, priv_path = _make_temp_real_keypair()
        try:
            bundle_a = encrypt_mapping(m_a, pubkey_pem_path=pub_path)
            recovered = decrypt_mapping(bundle_a, private_key_pem_path=priv_path)
            # The recovered mapping must be m_a, not m_b
            assert recovered == m_a
            if m_a != m_b:
                assert recovered != m_b
        finally:
            pub_path.unlink(); priv_path.unlink()

    def test_evaluator_cannot_decrypt_without_private_key(self):
        pub_path, priv_path = _make_temp_real_keypair()
        try:
            bundle = encrypt_mapping({"T1": "generic"}, pubkey_pem_path=pub_path)
            with pytest.raises(BlindingError):
                decrypt_mapping(bundle, private_key_pem_path=None)
        finally:
            pub_path.unlink(); priv_path.unlink()


# ---------------------------------------------------------------------------
# Evaluator input isolation
# ---------------------------------------------------------------------------

class TestEvaluatorInputIsolation:
    def test_bundle_does_not_contain_plain_task_ids(self):
        # Use realistic multi-character task IDs that won't appear in base64
        # by coincidence (unlike single chars like "T1" / "T2")
        mapping = assign_arms(
            ["SRCH-C001", "SRCH-C002", "SRCH-C003"], generate_seed()
        )
        bundle = encrypt_mapping(mapping, dry_run=True)
        bundle_json = json.dumps(bundle.to_dict())
        # The full task IDs must not appear as plaintext in the bundle JSON
        for tid in mapping.keys():
            assert tid not in bundle_json, (
                f"Task ID '{tid}' found as plaintext in bundle — mapping leaked"
            )

    def test_bundle_does_not_contain_arm_labels(self):
        mapping = assign_arms(["T1", "T2"], generate_seed())
        bundle = encrypt_mapping(mapping, dry_run=True)
        bundle_str = json.dumps(bundle.to_dict())
        for arm in ("generic", "configured"):
            assert arm not in bundle_str


# ---------------------------------------------------------------------------
# Selection-only invariant
# ---------------------------------------------------------------------------

class TestSelectionOnlyInvariant:
    def test_no_confirmation_verdict_in_blinding_module(self):
        src = (HERE / "blinding.py").read_text(encoding="utf-8")
        for phrase in ("confirmation verdict", "confirmed effect", "confirmation score"):
            assert phrase not in src.lower()


# ---------------------------------------------------------------------------
# T4B-05: _cli_deblind repair tests
# ---------------------------------------------------------------------------

def _make_temp_rsa4096_keypair():
    """Generate a temporary RSA-4096 keypair for tests."""
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption,
    )
    priv = generate_private_key(public_exponent=65537, key_size=4096)
    pub_pem  = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    priv_pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    tmp_pub  = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_priv = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
    tmp_pub.write(pub_pem);  tmp_pub.close()
    tmp_priv.write(priv_pem); tmp_priv.close()
    return Path(tmp_pub.name), Path(tmp_priv.name)


class TestCliDeblind:
    def test_cli_deblind_roundtrip_rsa4096(self, tmp_path):
        """Generate RSA-4096 pair, encrypt a mapping, deblind via _cli_deblind."""
        pub_path, priv_path = _make_temp_rsa4096_keypair()
        try:
            mapping = {"TASK-001": "generic", "TASK-002": "configured"}
            bundle  = encrypt_mapping(mapping, pubkey_pem_path=pub_path, dry_run=False)
            bundle_file = tmp_path / "mapping_bundle.json"
            import json as _json
            bundle_file.write_text(_json.dumps(bundle.to_dict()), encoding="utf-8")

            # Capture stdout
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                bl._cli_deblind(str(bundle_file), str(priv_path))
            result = _json.loads(buf.getvalue())
            assert result == mapping
        finally:
            pub_path.unlink(missing_ok=True)
            priv_path.unlink(missing_ok=True)

    def test_cli_deblind_rejects_dry_run_bundle(self, tmp_path):
        """_cli_deblind must raise SystemExit on a dry-run-tagged bundle."""
        mapping = {"T": "generic"}
        bundle  = encrypt_mapping(mapping, dry_run=True)
        import json as _json
        bundle_file = tmp_path / "dry_bundle.json"
        bundle_file.write_text(_json.dumps(bundle.to_dict()), encoding="utf-8")
        with pytest.raises((DryRunBundle, SystemExit)):
            bl._cli_deblind(str(bundle_file), "/nonexistent/key.pem")

    def test_cli_deblind_rejects_missing_fields(self, tmp_path):
        """_cli_deblind must exit on a bundle missing required fields."""
        import json as _json
        bundle_file = tmp_path / "incomplete.json"
        bundle_file.write_text(_json.dumps({"algorithm": "AES-256-GCM+RSA-OAEP-SHA256-v1"}),
                               encoding="utf-8")
        with pytest.raises(SystemExit):
            bl._cli_deblind(str(bundle_file), "/nonexistent/key.pem")


# ---------------------------------------------------------------------------
# T4B-06: RSA-4096 key validation tests
# ---------------------------------------------------------------------------

class TestRsa4096Validation:
    def test_rsa4096_exponent65537_passes(self):
        pub_path, priv_path = _make_temp_rsa4096_keypair()
        try:
            bl.validate_rsa4096_public_key(pub_path)  # no raise
        finally:
            pub_path.unlink(missing_ok=True)
            priv_path.unlink(missing_ok=True)

    def test_rsa2048_raises_key_compatibility_error(self):
        from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat,
        )
        priv = generate_private_key(public_exponent=65537, key_size=2048)
        pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        tmp.write(pub_pem); tmp.close()
        try:
            with pytest.raises(bl.KeyCompatibilityError, match="RSA-2048"):
                bl.validate_rsa4096_public_key(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_ec_key_raises_key_compatibility_error(self):
        from cryptography.hazmat.primitives.asymmetric.ec import (
            generate_private_key, SECP384R1,
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat,
        )
        priv = generate_private_key(SECP384R1())
        pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        tmp.write(pub_pem); tmp.close()
        try:
            with pytest.raises(bl.KeyCompatibilityError, match="not an RSA key"):
                bl.validate_rsa4096_public_key(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_placeholder_raises_placeholder_error(self):
        with pytest.raises(PlaceholderPublicKey):
            bl.validate_rsa4096_public_key(DEFAULT_PUBLIC_KEY_PATH)

    def test_fingerprint_mismatch_detected(self, tmp_path):
        pub_a, priv_a = _make_temp_rsa4096_keypair()
        pub_b, priv_b = _make_temp_rsa4096_keypair()
        try:
            mapping = {"T": "generic"}
            # Encrypt with key A
            bundle = encrypt_mapping(mapping, pubkey_pem_path=pub_a, dry_run=False)
            # Verify fingerprint against key B — must raise
            with pytest.raises(bl.KeyCompatibilityError, match="fingerprint"):
                bl.validate_key_fingerprint_matches(bundle, pub_b)
            # Verify against key A — must pass
            bl.validate_key_fingerprint_matches(bundle, pub_a)
        finally:
            for p in (pub_a, priv_a, pub_b, priv_b):
                p.unlink(missing_ok=True)

    def test_load_public_key_validates_rsa4096(self):
        """_load_public_key must reject RSA-2048 keys."""
        from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat,
        )
        priv = generate_private_key(public_exponent=65537, key_size=2048)
        pub_pem = priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        tmp = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)
        tmp.write(pub_pem); tmp.close()
        try:
            with pytest.raises(bl.KeyCompatibilityError):
                bl._load_public_key(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
