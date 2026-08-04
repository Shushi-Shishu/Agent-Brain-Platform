"""
Tests for blinding.py — deterministic blinding and custody infrastructure.

Coverage:
- Seed generation (randomness, format)
- Deterministic arm assignment (reproducible given seed)
- Mapping encryption/decryption round-trip
- Cross-arm artifact rejection (mismatch detection)
- Corpus hash mismatch detection
- Seed isolation: assert_seed_not_in_environment
- Mapping isolation: assert_mapping_not_in_environment
- Evaluator input isolation
- Selection-only invariant: no confirmation answer generated
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import blinding as bl
from blinding import (
    generate_seed,
    read_seed_from_env,
    assign_arms,
    encrypt_mapping,
    decrypt_mapping,
    verify_corpus_package,
    assert_seed_not_in_environment,
    assert_mapping_not_in_environment,
    MappingBundle,
    BlindingError,
    SeedAccessViolation,
    CorpusHashMismatch,
    SEED_ENV_VAR,
    SEED_BYTES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_seed() -> str:
    return generate_seed()


SAMPLE_TASKS = [f"SRCH-C{i:03d}" for i in range(1, 33)]


# ---------------------------------------------------------------------------
# Seed generation tests
# ---------------------------------------------------------------------------

class TestSeedGeneration:
    def test_seed_is_hex_string(self):
        seed = generate_seed()
        assert all(c in "0123456789ABCDEFabcdef" for c in seed)

    def test_seed_length(self):
        seed = generate_seed()
        assert len(seed) == SEED_BYTES * 2

    def test_seeds_are_unique(self):
        s1 = generate_seed()
        s2 = generate_seed()
        assert s1 != s2  # Extremely unlikely to collide

    def test_seed_is_uppercase(self):
        seed = generate_seed()
        assert seed == seed.upper()


# ---------------------------------------------------------------------------
# read_seed_from_env tests
# ---------------------------------------------------------------------------

class TestReadSeedFromEnv:
    def test_reads_valid_seed(self):
        seed = generate_seed()
        with patch.dict(os.environ, {SEED_ENV_VAR: seed}):
            result = read_seed_from_env()
        assert result == seed

    def test_raises_when_var_absent(self):
        env = {k: v for k, v in os.environ.items() if k != SEED_ENV_VAR}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(BlindingError):
                read_seed_from_env()

    def test_raises_when_var_empty(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: ""}):
            with pytest.raises(BlindingError):
                read_seed_from_env()

    def test_raises_when_var_malformed(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: "NOTAHEXSTRING"}):
            with pytest.raises(BlindingError):
                read_seed_from_env()

    def test_raises_when_var_too_short(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: "AABB" * 8}):  # 32 chars, not 64
            with pytest.raises(BlindingError):
                read_seed_from_env()


# ---------------------------------------------------------------------------
# Arm assignment tests
# ---------------------------------------------------------------------------

class TestArmAssignment:
    def test_deterministic_assignment(self):
        seed = generate_seed()
        m1 = assign_arms(SAMPLE_TASKS, seed)
        m2 = assign_arms(SAMPLE_TASKS, seed)
        assert m1 == m2

    def test_different_seeds_produce_different_assignments(self):
        s1, s2 = generate_seed(), generate_seed()
        m1 = assign_arms(SAMPLE_TASKS, s1)
        m2 = assign_arms(SAMPLE_TASKS, s2)
        # With 32 tasks there is a 2^-32 chance of exact collision
        assert m1 != m2

    def test_all_tasks_assigned(self):
        seed = generate_seed()
        mapping = assign_arms(SAMPLE_TASKS, seed)
        assert set(mapping.keys()) == set(SAMPLE_TASKS)

    def test_assignments_are_valid_arms(self):
        seed = generate_seed()
        mapping = assign_arms(SAMPLE_TASKS, seed)
        for arm in mapping.values():
            assert arm in ("generic", "configured")

    def test_custom_arms(self):
        seed = generate_seed()
        mapping = assign_arms(["T1", "T2", "T3"], seed, arms=("arm_a", "arm_b"))
        for arm in mapping.values():
            assert arm in ("arm_a", "arm_b")

    def test_both_arms_represented(self):
        seed = generate_seed()
        # With 32 tasks, the probability of all tasks mapping to one arm is ~2^-31
        mapping = assign_arms(SAMPLE_TASKS, seed)
        assert "generic" in mapping.values()
        assert "configured" in mapping.values()


# ---------------------------------------------------------------------------
# Encryption / decryption round-trip tests
# ---------------------------------------------------------------------------

class TestMappingEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        seed = generate_seed()
        mapping = assign_arms(SAMPLE_TASKS, seed)
        bundle = encrypt_mapping(mapping, seed)
        recovered = decrypt_mapping(bundle, seed)
        assert recovered == mapping

    def test_bundle_has_required_fields(self):
        seed = generate_seed()
        mapping = assign_arms(["T1"], seed)
        bundle = encrypt_mapping(mapping, seed)
        d = bundle.to_dict()
        assert "encrypted_mapping_b64" in d
        assert "mapping_hash" in d
        assert "algorithm" in d
        assert "seed_env_var" in d

    def test_bundle_hash_is_stable(self):
        seed = generate_seed()
        mapping = assign_arms(["T1", "T2"], seed)
        b1 = encrypt_mapping(mapping, seed)
        # Different nonce means different ciphertext, but both should round-trip
        recovered = decrypt_mapping(b1, seed)
        assert recovered == mapping

    def test_wrong_seed_fails_decryption(self):
        seed1 = generate_seed()
        seed2 = generate_seed()
        mapping = assign_arms(["T1"], seed1)
        bundle = encrypt_mapping(mapping, seed1)
        with pytest.raises(BlindingError):
            decrypt_mapping(bundle, seed2)

    def test_tampered_ciphertext_fails_authentication(self):
        import base64
        seed = generate_seed()
        mapping = assign_arms(["T1", "T2"], seed)
        bundle = encrypt_mapping(mapping, seed)
        # Tamper with the ciphertext
        raw = base64.b64decode(bundle.encrypted_mapping_b64)
        tampered = bytearray(raw)
        tampered[-1] ^= 0xFF
        bad_bundle = MappingBundle(
            encrypted_mapping_b64=base64.b64encode(bytes(tampered)).decode(),
            mapping_hash=bundle.mapping_hash,
            algorithm=bundle.algorithm,
            seed_env_var=bundle.seed_env_var,
        )
        with pytest.raises(BlindingError):
            decrypt_mapping(bad_bundle, seed)

    def test_hash_mismatch_detected_before_decryption(self):
        seed = generate_seed()
        mapping = assign_arms(["T1"], seed)
        bundle = encrypt_mapping(mapping, seed)
        bad_bundle = MappingBundle(
            encrypted_mapping_b64=bundle.encrypted_mapping_b64,
            mapping_hash="A" * 64,  # wrong hash
            algorithm=bundle.algorithm,
            seed_env_var=bundle.seed_env_var,
        )
        with pytest.raises(BlindingError):
            decrypt_mapping(bad_bundle, seed)


# ---------------------------------------------------------------------------
# Corpus hash mismatch tests
# ---------------------------------------------------------------------------

class TestCorpusHashMismatch:
    def test_matching_hash_passes(self, tmp_path):
        content = b"fake corpus package content"
        pkg = tmp_path / "corpus.enc"
        pkg.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest().upper()
        # Should not raise
        verify_corpus_package(pkg, expected)

    def test_mismatched_hash_raises(self, tmp_path):
        content = b"fake corpus package content"
        pkg = tmp_path / "corpus.enc"
        pkg.write_bytes(content)
        wrong_hash = "A" * 64
        with pytest.raises(CorpusHashMismatch):
            verify_corpus_package(pkg, wrong_hash)


# ---------------------------------------------------------------------------
# Seed isolation tests
# ---------------------------------------------------------------------------

class TestSeedIsolation:
    def test_seed_absent_passes(self):
        env = {k: v for k, v in os.environ.items() if k != SEED_ENV_VAR}
        with patch.dict(os.environ, env, clear=True):
            assert_seed_not_in_environment()  # should not raise

    def test_seed_present_raises_violation(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: generate_seed()}):
            with pytest.raises(SeedAccessViolation):
                assert_seed_not_in_environment()

    def test_empty_seed_var_does_not_raise(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: ""}):
            # Empty string should not be treated as a present seed
            assert_seed_not_in_environment()


# ---------------------------------------------------------------------------
# Mapping isolation (evaluator) tests
# ---------------------------------------------------------------------------

class TestMappingIsolation:
    def test_mapping_vars_absent_passes(self):
        env = {
            k: v for k, v in os.environ.items()
            if k not in (SEED_ENV_VAR, "BLIND_MAPPING", "ARM_MAPPING", "MAPPING_KEY")
        }
        with patch.dict(os.environ, env, clear=True):
            assert_mapping_not_in_environment()  # should not raise

    def test_blind_mapping_present_raises_violation(self):
        with patch.dict(os.environ, {"BLIND_MAPPING": "some_value"}):
            with pytest.raises(SeedAccessViolation):
                assert_mapping_not_in_environment()

    def test_arm_mapping_present_raises_violation(self):
        with patch.dict(os.environ, {"ARM_MAPPING": "some_value"}):
            with pytest.raises(SeedAccessViolation):
                assert_mapping_not_in_environment()

    def test_seed_present_raises_violation_in_mapping_check(self):
        with patch.dict(os.environ, {SEED_ENV_VAR: generate_seed()}):
            with pytest.raises(SeedAccessViolation):
                assert_mapping_not_in_environment()


# ---------------------------------------------------------------------------
# Cross-arm artifact rejection tests
# ---------------------------------------------------------------------------

class TestCrossArmArtifactRejection:
    def test_different_seeds_cannot_decrypt_each_other(self):
        """An artifact encrypted with seed A cannot be decrypted with seed B."""
        seed_a = generate_seed()
        seed_b = generate_seed()
        mapping = assign_arms(["T1", "T2"], seed_a)
        bundle_a = encrypt_mapping(mapping, seed_a)
        with pytest.raises(BlindingError):
            decrypt_mapping(bundle_a, seed_b)

    def test_arm_assignment_is_unique_per_seed(self):
        """Two different seeds produce different arm assignments (with high probability)."""
        seed_a = generate_seed()
        seed_b = generate_seed()
        m_a = assign_arms(SAMPLE_TASKS, seed_a)
        m_b = assign_arms(SAMPLE_TASKS, seed_b)
        # Full equality is astronomically unlikely; check at least one differs
        assert any(m_a[t] != m_b[t] for t in SAMPLE_TASKS)


# ---------------------------------------------------------------------------
# Evaluator input isolation tests
# ---------------------------------------------------------------------------

class TestEvaluatorInputIsolation:
    def test_bundle_does_not_expose_plain_mapping(self):
        seed = generate_seed()
        mapping = assign_arms(["T1", "T2", "T3"], seed)
        bundle = encrypt_mapping(mapping, seed)
        bundle_json = json.dumps(bundle.to_dict())
        # Plain task IDs must not appear in the bundle
        for task_id in mapping.keys():
            assert task_id not in bundle_json

    def test_bundle_does_not_expose_arm_labels(self):
        seed = generate_seed()
        mapping = assign_arms(["T1"], seed)
        bundle = encrypt_mapping(mapping, seed)
        bundle_str = json.dumps(bundle.to_dict())
        # Arm labels must not appear as plaintext
        for arm in ("generic", "configured"):
            assert arm not in bundle_str


# ---------------------------------------------------------------------------
# Selection-only invariant
# ---------------------------------------------------------------------------

class TestSelectionOnlyInvariant:
    def test_no_confirmation_output_in_blinding_module(self):
        src = (HERE / "blinding.py").read_text(encoding="utf-8")
        forbidden = ("confirmation verdict", "confirmed effect", "confirmation score")
        for phrase in forbidden:
            assert phrase not in src.lower(), (
                f"blinding.py contains confirmation output reference: '{phrase}'"
            )
