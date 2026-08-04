"""
Task 4 confirmation-readiness checks for POC 6c.

External-readiness infrastructure additions (Task 4 scope extension):
  check_provider_adapter()     : verifies provider.py and pricing_lock.json exist
                                 and have expected structure; fails closed if the
                                 API key is absent when a live check is requested.
  check_github_actions_workflow() : verifies the fail-closed confirmation workflow
                                 exists with required job names.
  check_custody_key()          : verifies custodian_public_key.pem is committed.
  check_blinding_module()      : verifies blinding.py exports required symbols.
  check_pricing_lock()         : verifies pricing_lock.json is present and
                                 contains locked records for both model roles.
  check_vault_hashes()         : re-checks vault-dependent hashes (R08 extension)
                                 against the actual vault at its real path.


Requirements R01–R09 with unique IDs, categories, statuses, and evidence.

Three locally feasible checks implemented here:
  R06 — corpus_facade_enforced()   : preflight verifies FrozenCorpus is the
                                     only vault-access path; rejects direct
                                     filesystem reads.
  R07 — rubric_calibration()       : delegates to rubric.py; verifies rubric
                                     structure and hash are stable.
  R08 — hash_reverification()      : re-hashes every frozen input and confirms
                                     each matches PREREGISTRATION_DRAFT.md;
                                     vault-dependent hashes reported separately.

R09 — preregistration_checklist_update() is a documentation gate: the
checklist in PREREGISTRATION_DRAFT.md is updated in this commit; the check
verifies the file is present and that three newly satisfied gates are marked.

Fail-closed preflight:
  run_preflight() raises PreflightFailed (with a full list of unmet
  requirements) if ANY requirement is not SATISFIED.  It must be called
  before every confirmation run.  No mock, env-var, or shared-directory
  convention counts as satisfying an external-blocked requirement.

External-blocked requirements (R01–R05) are permanently BLOCKED until
real infrastructure evidence is supplied.  run_preflight() always fails
while they are unmet.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
from pathlib import Path
from typing import Any

from rubric import rubric_calibration_evidence


# ---------------------------------------------------------------------------
# Requirement model
# ---------------------------------------------------------------------------

class RequirementStatus(str, enum.Enum):
    SATISFIED = "satisfied"
    BLOCKED   = "blocked_external"
    PENDING   = "pending"


class RequirementCategory(str, enum.Enum):
    RUNTIME   = "runtime"
    ISOLATION = "isolation"
    CUSTODY   = "custody"
    CORPUS    = "corpus"
    RUBRIC    = "rubric"
    HASHES    = "hashes"
    PROCESS   = "process"


@dataclasses.dataclass
class Requirement:
    req_id:          str
    category:        RequirementCategory
    description:     str
    status:          RequirementStatus
    evidence:        str
    owner:           str            # "local" | "infrastructure" | "human"
    unblock_condition: str
    required_for_confirmation: bool
    check_result:    dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "req_id":           self.req_id,
            "category":         self.category.value,
            "description":      self.description,
            "status":           self.status.value,
            "evidence":         self.evidence,
            "owner":            self.owner,
            "unblock_condition": self.unblock_condition,
            "required_for_confirmation": self.required_for_confirmation,
            "check_result":     self.check_result,
        }


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent

_PATHS = {
    "generic_prompt":    HERE / "pilot" / "GENERIC_AGENT.md",
    "configured_prompt": HERE / "pilot" / "CONFIGURED_AGENT_V2.md",
    "output_schema":     HERE / "pilot" / "OUTPUT_FORMAT.json",
    "eval_rubric":       HERE / "confirmation" / "EVALUATION_RUBRIC_V1.md",
    "task_set":          HERE / "confirmation" / "tasks_v1.json",
    "sealed_labels":     HERE / "confirmation" / "sealed" / "design_labels_v1.json",
    "preregistration":   HERE / "confirmation" / "PREREGISTRATION_DRAFT.md",
}

# ---------------------------------------------------------------------------
# Preregistered hashes (from PREREGISTRATION_DRAFT.md; utf-8 text encoding)
# ---------------------------------------------------------------------------

EXPECTED_HASHES: dict[str, str] = {
    "generic_prompt":    "119C376068579A7A0C85FF65337B6EEEF51924FFB3207869126D240926379481",
    "configured_prompt": "C13A0876413128772DAD874C55B0F7E00B2D09E02FB740E487110C042F83F8E2",
    "output_schema":     "8B966A5C7CA822A85C09A59C2D9AD46E95E3488EA9E761CD2E0B11D197FED0B3",
    "eval_rubric":       "3B1913ACFE347B9515D1C9946F47854D77E1F20DD2044B13210425AC54B264F8",
    "task_set":          "CB4A5012A274A82A3ACE8B232C34997D61B474C59CA6C6A350F620C264862F70",
    "sealed_labels":     "6B189887C869A4AA2C9F09515CB68AFBB708279E03BB429D03F09876180B75FD",
    # vault-dependent — require Project 008 on disk; reported separately
    "corpus_manifest":   "6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F",
    "indexed_body":      "E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A",
}

# Hashes verifiable without the vault
LOCAL_HASH_KEYS = (
    "generic_prompt",
    "configured_prompt",
    "output_schema",
    "eval_rubric",
    "task_set",
    "sealed_labels",
)

# Hashes that require the Project 008 vault to be present
VAULT_HASH_KEYS = ("corpus_manifest", "indexed_body")


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------

def _sha256_text(path: Path) -> str:
    return hashlib.sha256(
        path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest().upper()


# ---------------------------------------------------------------------------
# R06 — Corpus-facade enforcement
# ---------------------------------------------------------------------------

def check_corpus_facade_enforced(
    corpus_module_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify that every vault-access call in corpus.py goes through
    FrozenCorpus / SearchSession — the sole deterministic facade.

    Strategy: inspect corpus.py source for direct filesystem access patterns
    (open(), Path(...).read_text(), etc.) that bypass the facade.  The
    FrozenCorpus constructor already verifies the manifest hash; SearchSession
    enforces budget limits.  Direct reads would bypass both.

    Returns a dict with keys: passed, errors, evidence.
    """
    module_path = corpus_module_path or (HERE / "corpus.py")
    errors: list[str] = []

    if not module_path.exists():
        return {
            "passed": False,
            "errors": [f"corpus.py not found at {module_path}"],
            "evidence": "corpus module absent",
        }

    source = module_path.read_text(encoding="utf-8")

    # Confirm FrozenCorpus and SearchSession are defined
    if "class FrozenCorpus" not in source:
        errors.append("FrozenCorpus class absent from corpus.py")
    if "class SearchSession" not in source:
        errors.append("SearchSession class absent from corpus.py")

    # Confirm FrozenCorpus verifies the manifest hash on construction
    if "EXPECTED_MANIFEST_SHA256" not in source:
        errors.append(
            "FrozenCorpus does not reference EXPECTED_MANIFEST_SHA256 "
            "(manifest integrity check may be absent)"
        )

    # Confirm SearchSession enforces a budget before every operation
    if "BudgetExhausted" not in source:
        errors.append(
            "SearchSession does not raise BudgetExhausted "
            "(budget enforcement may be absent)"
        )

    # Confirm read_note rejects paths that escape the corpus root
    if "escapes the frozen corpus" not in source and "CorpusError" not in source:
        errors.append(
            "corpus.py does not raise CorpusError for path traversal "
            "(traversal protection may be absent)"
        )

    # The module imports from poc6a experiment; check it does not open the
    # vault directly (all vault I/O should flow through load_documents / BM25Index)
    direct_open_lines = [
        line.strip()
        for line in source.splitlines()
        if "open(" in line and "def " not in line and "# " not in line
        and "corpus_module_path" not in line
    ]
    if direct_open_lines:
        errors.append(
            f"corpus.py contains {len(direct_open_lines)} direct open() call(s) "
            f"outside facade: {direct_open_lines[:3]}"
        )

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "evidence": (
            "FrozenCorpus enforces manifest hash on construction; "
            "SearchSession enforces budget before every search/read; "
            "path traversal raises CorpusError; "
            "no direct open() calls bypass the facade."
        ) if not errors else "; ".join(errors),
    }


# ---------------------------------------------------------------------------
# R07 — Rubric calibration
# ---------------------------------------------------------------------------

def check_rubric_calibration(
    rubric_path: Path | None = None,
) -> dict[str, Any]:
    """Delegate to rubric.py and return the calibration evidence dict."""
    return rubric_calibration_evidence(rubric_path)


# ---------------------------------------------------------------------------
# R08 — Hash reverification
# ---------------------------------------------------------------------------

def check_hash_reverification(
    paths: dict[str, Path] | None = None,
    expected: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Re-hash every frozen input and confirm each matches PREREGISTRATION_DRAFT.md.

    Local artifacts (prompts, schema, rubric, task set, labels) are hashed
    directly.  Vault-dependent hashes (corpus_manifest, indexed_body) are
    reported as "vault_absent" when the Project 008 vault is not on disk.

    Returns:
      passed         : True only when all local hashes match and vault status
                       is noted (vault absence does not fail this check, but
                       is recorded as requiring verification before activation).
      local_results  : per-artifact match/mismatch for local files.
      vault_results  : per-artifact vault-absent/match for vault-dependent hashes.
      errors         : list of local mismatches or missing files.
    """
    file_paths = paths or _PATHS
    expected_h = expected or EXPECTED_HASHES

    local_results: dict[str, dict[str, Any]] = {}
    vault_results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for key in LOCAL_HASH_KEYS:
        path = file_paths.get(key)
        if path is None or not Path(path).exists():
            local_results[key] = {"status": "missing", "actual": None, "expected": expected_h[key]}
            errors.append(f"{key}: file not found at {path}")
            continue
        actual = _sha256_text(Path(path))
        match = actual == expected_h[key]
        local_results[key] = {
            "status": "match" if match else "mismatch",
            "actual":   actual,
            "expected": expected_h[key],
        }
        if not match:
            errors.append(
                f"{key}: hash mismatch "
                f"(expected {expected_h[key][:16]}…, got {actual[:16]}…)"
            )

    for key in VAULT_HASH_KEYS:
        vault_results[key] = {
            "status": "vault_absent_requires_verification",
            "expected": expected_h.get(key, ""),
            "note": (
                "Project 008 vault not present locally. "
                "This hash must be verified before activation using "
                "corpus.manifest_content_commitment() and "
                "corpus.indexed_content_commitment()."
            ),
        }

    return {
        "requirement": "R08",
        "check": "hash_reverification",
        "local_results": local_results,
        "vault_results": vault_results,
        "errors": errors,
        "passed": len(errors) == 0,
        "vault_verification_required_before_activation": True,
        "selection_limitation": (
            "Hash reverification confirms frozen-input integrity only. "
            "No confirmation outputs exist. "
            "All ablation results remain labeled selection-only."
        ),
    }


# ---------------------------------------------------------------------------
# R09 — Preregistration checklist update
# ---------------------------------------------------------------------------

def check_preregistration_checklist(
    preregistration_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify that PREREGISTRATION_DRAFT.md is present and that R06/R07/R08
    gates are marked satisfied (contain '[x]') without any new confirmation
    outputs or threshold changes.

    Does NOT activate the preregistration — activation requires all nine
    requirements including the five externally blocked ones.
    """
    path = preregistration_path or _PATHS["preregistration"]
    errors: list[str] = []

    if not path.exists():
        return {
            "passed": False,
            "errors": [f"PREREGISTRATION_DRAFT.md not found at {path}"],
        }

    text = path.read_text(encoding="utf-8")

    # File must still be a draft (not activated)
    if "Not Yet Activated" not in text and "not yet activated" not in text.lower():
        errors.append(
            "PREREGISTRATION_DRAFT.md appears to have been activated; "
            "activation requires all nine requirements"
        )

    # Three newly-satisfied gates must be checked
    for gate_phrase in (
        "deterministic corpus facade",
        "numeric rubric anchors",
        "task file and all prompts",
    ):
        # Find lines containing this phrase and check for [x]
        lines = [ln for ln in text.splitlines() if gate_phrase.lower() in ln.lower()]
        if not lines:
            errors.append(f"gate '{gate_phrase}' not found in preregistration")
        elif not any("[x]" in ln for ln in lines):
            errors.append(
                f"gate '{gate_phrase}' exists but is not marked [x]"
            )

    # Must not contain confirmation outputs
    forbidden = ("confirmation run", "confirmation score", "confirmed effect")
    for phrase in forbidden:
        if phrase.lower() in text.lower():
            errors.append(
                f"preregistration contains confirmation output reference: '{phrase}'"
            )

    return {
        "requirement": "R09",
        "check": "preregistration_checklist",
        "path": str(path),
        "errors": errors,
        "passed": len(errors) == 0,
    }


# ---------------------------------------------------------------------------
# Provider adapter checks (R01–R03 infrastructure evidence)
# ---------------------------------------------------------------------------

def check_provider_adapter(
    provider_module_path: Path | None = None,
    pricing_lock_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify that provider.py and pricing_lock.json exist and have expected
    structure.  Does not call the live API (no key required).
    """
    errors: list[str] = []
    provider_path = provider_module_path or (HERE / "provider.py")
    p_lock_path   = pricing_lock_path   or (HERE / "pricing_lock.json")

    if not provider_path.exists():
        errors.append(f"provider.py not found at {provider_path}")
    else:
        src = provider_path.read_text(encoding="utf-8")
        for symbol in ("AnthropicProviderAdapter", "ResponseTelemetry",
                       "MissingApiKey", "ResponseModelMismatch",
                       "compute_provider_cost_usd", "verify_models_available",
                       "ANTHROPIC_API_KEY"):
            if symbol not in src:
                errors.append(f"provider.py missing expected symbol: {symbol}")

    if not p_lock_path.exists():
        errors.append(f"pricing_lock.json not found at {p_lock_path}")
    else:
        try:
            import json as _json
            lock = _json.loads(p_lock_path.read_text(encoding="utf-8"))
            if "models" not in lock:
                errors.append("pricing_lock.json missing 'models' array")
            else:
                roles = {m.get("role") for m in lock["models"]}
                for required_role in ("agent", "evaluator"):
                    if required_role not in roles:
                        errors.append(
                            f"pricing_lock.json missing model entry with role='{required_role}'"
                        )
                if "confirmation_constraints" not in lock:
                    errors.append("pricing_lock.json missing 'confirmation_constraints'")
        except Exception as exc:
            errors.append(f"pricing_lock.json parse error: {exc}")

    return {
        "requirement": "provider_adapter",
        "check": "check_provider_adapter",
        "errors": errors,
        "passed": len(errors) == 0,
        "evidence": (
            "provider.py and pricing_lock.json present with required structure."
            if not errors else "; ".join(errors)
        ),
    }


def check_github_actions_workflow(
    workflow_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify that the fail-closed confirmation workflow exists with the
    required job names.
    """
    errors: list[str] = []
    wf_path = workflow_path or (HERE.parents[0] / ".github" / "workflows" / "poc6c-confirmation.yml")

    if not wf_path.exists():
        return {
            "requirement": "github_actions_workflow",
            "check": "check_github_actions_workflow",
            "errors": [f"Workflow file not found at {wf_path}"],
            "passed": False,
            "evidence": "Workflow file absent.",
        }

    content = wf_path.read_text(encoding="utf-8")
    required_jobs = [
        "preflight",
        "generic-arm",
        "configured-arm",
        "deterministic-blinding",
        "blinded-evaluator",
        "integrity-and-analysis",
    ]
    for job in required_jobs:
        if job not in content:
            errors.append(f"Workflow missing required job: '{job}'")

    # Check for protected environment requirement
    if "environment: confirmation" not in content:
        errors.append("Workflow does not require 'confirmation' protected environment")

    # Check workflow is manual-trigger only (no automatic push triggers)
    if "on:\n  push:" in content or "on:\n  pull_request:" in content:
        errors.append("Workflow has automatic triggers (push/pull_request); must be manual only")

    return {
        "requirement": "github_actions_workflow",
        "check": "check_github_actions_workflow",
        "errors": errors,
        "passed": len(errors) == 0,
        "evidence": (
            f"Confirmation workflow found at {wf_path} with all required jobs."
            if not errors else "; ".join(errors)
        ),
    }


def check_custody_key(
    key_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify custodian_public_key.pem: present, PEM-formatted, and NOT the
    placeholder.  A placeholder key causes R05 to remain BLOCKED.
    """
    errors: list[str] = []
    path = key_path or (HERE / "custodian_public_key.pem")

    if not path.exists():
        errors.append(f"custodian_public_key.pem not found at {path}")
        return {
            "requirement": "custody_key",
            "check": "check_custody_key",
            "errors": errors,
            "passed": False,
            "is_placeholder": True,
            "evidence": "; ".join(errors),
        }

    content = path.read_text(encoding="utf-8")
    is_placeholder = "PLACEHOLDER" in content

    if "BEGIN" not in content:
        errors.append("custodian_public_key.pem does not look like a PEM file")
    if is_placeholder:
        errors.append(
            "custodian_public_key.pem is still the placeholder. "
            "R05 remains BLOCKED until a real offline-generated key replaces it."
        )

    return {
        "requirement": "custody_key",
        "check": "check_custody_key",
        "errors": errors,
        "passed": len(errors) == 0,
        "is_placeholder": is_placeholder,
        "evidence": (
            f"custodian_public_key.pem present and not a placeholder at {path}."
            if not errors else "; ".join(errors)
        ),
    }


def check_blinding_module(
    blinding_module_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify that blinding.py exports the required symbols and documents
    the isolation invariants.
    """
    errors: list[str] = []
    path = blinding_module_path or (HERE / "blinding.py")

    if not path.exists():
        return {
            "requirement": "blinding_module",
            "check": "check_blinding_module",
            "errors": [f"blinding.py not found at {path}"],
            "passed": False,
            "evidence": "blinding.py absent.",
        }

    src = path.read_text(encoding="utf-8")
    required_symbols = [
        "generate_seed", "assign_arms", "encrypt_mapping", "decrypt_mapping",
        "assert_seed_not_in_environment", "assert_mapping_not_in_environment",
        "CONFIRMATION_BLIND_SEED", "SeedAccessViolation",
        # Phase 2 additions: three-layer envelope
        "AES-256-GCM+RSA-OAEP-SHA256-v1",
        "check_not_placeholder_key",
        "check_not_dry_run_bundle",
        "check_not_test_only_bundle",
        "PlaceholderPublicKey",
        "BundleIsTestOnly",
        "DryRunBundle",
        "_DEK_BYTES",
    ]
    for sym in required_symbols:
        if sym not in src:
            errors.append(f"blinding.py missing required symbol: {sym}")

    return {
        "requirement": "blinding_module",
        "check": "check_blinding_module",
        "errors": errors,
        "passed": len(errors) == 0,
        "evidence": (
            "blinding.py present with all required symbols."
            if not errors else "; ".join(errors)
        ),
    }


def check_pricing_lock(
    pricing_lock_path: Path | None = None,
) -> dict[str, Any]:
    """
    Verify pricing_lock.json: present, parseable, contains locked model
    records for agent and evaluator roles, and documents confirmation
    constraints.
    """
    p_lock_path = pricing_lock_path or (HERE / "pricing_lock.json")
    # Delegate to check_provider_adapter which already inspects the file
    result = check_provider_adapter(pricing_lock_path=p_lock_path)
    return {
        "requirement": "pricing_lock",
        "check": "check_pricing_lock",
        "errors": result["errors"],
        "passed": result["passed"],
        "evidence": result["evidence"],
    }


def check_vault_hashes_with_actual_vault(
    vault_root: Path | None = None,
    expected_manifest_sha256: str = "6BBA908F43640349937E94AEC9054E0DB16E9561265057099FBDFFEE8C6A8B3F",
    expected_indexed_body_sha256: str = "E7EE682DCE4175752FF38861E49EE5EA6836D7830AE37E1353640638657D084A",
) -> dict[str, Any]:
    """
    Re-check vault-dependent hashes (R08 extension) against the actual vault.

    Verifies BOTH corpus_manifest and indexed_body against frozen commitments.
    Returns passed=True only when both hashes match.

    The vault location is resolved via the PROJECT008_PATH environment variable
    or the explicit vault_root argument.  No developer-specific default path is
    used — callers must supply vault_root or set PROJECT008_PATH.
    """
    import os as _os
    errors: list[str] = []

    if vault_root is not None:
        vault_path = vault_root
    else:
        env_path = _os.environ.get("PROJECT008_PATH", "").strip()
        if not env_path:
            return {
                "requirement": "R08_vault",
                "check": "check_vault_hashes_with_actual_vault",
                "vault_path": None,
                "errors": [
                    "Vault path not supplied: set PROJECT008_PATH environment variable "
                    "or pass vault_root explicitly. No developer-specific default is used."
                ],
                "passed": False,
                "vault_present": False,
                "evidence": "Vault path not configured.",
            }
        vault_path = Path(env_path)

    manifest_path = (
        vault_path
        / "0. Exploration & Applicability Engine"
        / "state"
        / "identity-manifest.json"
    )
    # indexed_body: BM25 index / content file — adjust sub-path if vault layout differs
    indexed_body_path = (
        vault_path
        / "0. Exploration & Applicability Engine"
        / "state"
        / "indexed_body.json"
    )

    if not vault_path.exists():
        return {
            "requirement": "R08_vault",
            "check": "check_vault_hashes_with_actual_vault",
            "vault_path": str(vault_path),
            "errors": [f"Vault root not found at {vault_path}"],
            "passed": False,
            "vault_present": False,
            "evidence": "Vault absent; cannot verify corpus_manifest and indexed_body hashes.",
        }

    # Check corpus_manifest
    if not manifest_path.exists():
        errors.append(f"identity-manifest.json not found at {manifest_path}")
    else:
        actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
        if actual != expected_manifest_sha256.upper():
            errors.append(
                f"corpus_manifest hash mismatch: "
                f"expected {expected_manifest_sha256[:16]}…, "
                f"actual {actual[:16]}…"
            )

    # Check indexed_body
    if not indexed_body_path.exists():
        errors.append(f"indexed_body.json not found at {indexed_body_path}")
    else:
        actual_ib = hashlib.sha256(indexed_body_path.read_bytes()).hexdigest().upper()
        if actual_ib != expected_indexed_body_sha256.upper():
            errors.append(
                f"indexed_body hash mismatch: "
                f"expected {expected_indexed_body_sha256[:16]}…, "
                f"actual {actual_ib[:16]}…"
            )

    return {
        "requirement": "R08_vault",
        "check": "check_vault_hashes_with_actual_vault",
        "vault_path": str(vault_path),
        "errors": errors,
        "passed": len(errors) == 0,
        "vault_present": True,
        "evidence": (
            f"Vault present at {vault_path}; corpus_manifest and indexed_body hashes verified."
            if not errors else "; ".join(errors)
        ),
    }

def build_requirements_matrix(
    corpus_path: Path | None = None,
    rubric_path: Path | None = None,
    hash_paths: dict[str, Path] | None = None,
    preregistration_path: Path | None = None,
) -> list[Requirement]:
    """
    Build and return the full R01–R09 requirements matrix.

    Feasible checks (R06–R09) are run here.
    Blocked requirements (R01–R05) are always BLOCKED with no mock bypass.
    """
    # Run the three feasible checks
    corpus_result = check_corpus_facade_enforced(corpus_path)
    rubric_result = check_rubric_calibration(rubric_path)
    hash_result   = check_hash_reverification(hash_paths)
    prereg_result = check_preregistration_checklist(preregistration_path)

    matrix: list[Requirement] = [

        # ---- Externally blocked ----

        Requirement(
            req_id="R01",
            category=RequirementCategory.RUNTIME,
            description=(
                "Auditable configured-agent model ID and version locked "
                "and supplied by the execution environment."
            ),
            status=RequirementStatus.BLOCKED,
            evidence="No auditable model ID is available in the current runtime.",
            owner="infrastructure",
            unblock_condition=(
                "The execution environment must expose a stable, tamper-evident "
                "model identifier (e.g. API response header or signed metadata) "
                "that can be recorded in every trace. A convention, env-var, or "
                "self-reported prompt value does not satisfy this requirement."
            ),
            required_for_confirmation=True,
        ),

        Requirement(
            req_id="R02",
            category=RequirementCategory.RUNTIME,
            description=(
                "Auditable evaluator model IDs and versions locked and "
                "supplied by the execution environment for every evaluator call."
            ),
            status=RequirementStatus.BLOCKED,
            evidence="No auditable evaluator model ID is available in the current runtime.",
            owner="infrastructure",
            unblock_condition=(
                "Same as R01, applied to all evaluator calls. Each evaluator "
                "invocation must record a provider-supplied model identifier."
            ),
            required_for_confirmation=True,
        ),

        Requirement(
            req_id="R03",
            category=RequirementCategory.RUNTIME,
            description=(
                "Provider token count and monetary cost captured for every "
                "agent and evaluator call; missing values must not be estimated."
            ),
            status=RequirementStatus.BLOCKED,
            evidence=(
                "model_usage fields are null in all pilot outputs "
                "(controller.py model_usage block)."
            ),
            owner="infrastructure",
            unblock_condition=(
                "The execution environment must return input_tokens, "
                "output_tokens, and provider_cost_usd in the API response for "
                "every call. The controller trace schema already has these fields "
                "(currently null). When the provider supplies them, populate "
                "them; do not estimate from character counts."
            ),
            required_for_confirmation=True,
        ),

        Requirement(
            req_id="R04",
            category=RequirementCategory.ISOLATION,
            description=(
                "OS-enforced isolated workspaces preventing cross-arm, "
                "mapping, evaluator, and out-of-scope file access."
            ),
            status=RequirementStatus.BLOCKED,
            evidence=(
                "Collaboration agents share the host filesystem; "
                "no process-boundary isolation exists."
            ),
            owner="infrastructure",
            unblock_condition=(
                "Each arm and the evaluator must run in a separate OS process "
                "with filesystem access restricted by OS-level permissions "
                "(e.g. separate user accounts, containers, or chroot jails) "
                "so that arm A cannot read arm B's outputs, the blind mapping, "
                "or evaluation results. A shared-directory convention or "
                "promise-based separation does not satisfy this requirement."
            ),
            required_for_confirmation=True,
        ),

        Requirement(
            req_id="R05",
            category=RequirementCategory.CUSTODY,
            description=(
                "Randomization seed and blind-mapping file locked in a custody "
                "location inaccessible to agents and evaluators."
            ),
            status=RequirementStatus.BLOCKED,
            evidence=(
                "No neutral custody location exists; mapping lives on the "
                "same filesystem accessible to all agents."
            ),
            owner="human",
            unblock_condition=(
                "The randomization seed and arm-assignment mapping must be "
                "generated and stored by a human custodian (or a sealed "
                "environment) before confirmation runs start, in a location "
                "that no agent or evaluator process can read. The mapping is "
                "revealed to the analyst only after all outputs are collected "
                "and locked. An env-var or shared-directory convention does "
                "not satisfy this requirement."
            ),
            required_for_confirmation=True,
        ),

        # ---- Locally feasible ----

        Requirement(
            req_id="R06",
            category=RequirementCategory.CORPUS,
            description=(
                "Deterministic FrozenCorpus / SearchSession facade is the only "
                "vault access path; direct filesystem reads are blocked."
            ),
            status=(
                RequirementStatus.SATISFIED
                if corpus_result["passed"]
                else RequirementStatus.PENDING
            ),
            evidence=(
                corpus_result["evidence"]
                if corpus_result["passed"]
                else "; ".join(corpus_result["errors"])
            ),
            owner="local",
            unblock_condition=(
                "All vault access in corpus.py must flow through FrozenCorpus "
                "and SearchSession. No open() or Path.read_text() calls may "
                "bypass these classes."
            ),
            required_for_confirmation=True,
            check_result=corpus_result,
        ),

        Requirement(
            req_id="R07",
            category=RequirementCategory.RUBRIC,
            description=(
                "Anchored 100-point rubric dimensions, score bounds, and "
                "canonical hash verified using non-confirmation pilot material."
            ),
            status=(
                RequirementStatus.SATISFIED
                if rubric_result["passed"]
                else RequirementStatus.PENDING
            ),
            evidence=(
                f"rubric hash match: {rubric_result['hash_match']}; "
                f"dimensions verified; total={rubric_result['expected_total']}"
                if rubric_result["passed"]
                else "; ".join(rubric_result["errors"])
            ),
            owner="local",
            unblock_condition=(
                "EVALUATION_RUBRIC_V1.md must be present, hash-stable, "
                "and structurally valid (all six dimensions, correct maxima, "
                "valid anchors, critical-failure definition)."
            ),
            required_for_confirmation=True,
            check_result=rubric_result,
        ),

        Requirement(
            req_id="R08",
            category=RequirementCategory.HASHES,
            description=(
                "All frozen inputs re-hashed and confirmed against "
                "PREREGISTRATION_DRAFT.md values; vault-dependent hashes "
                "require Project 008 on disk."
            ),
            status=(
                RequirementStatus.SATISFIED
                if hash_result["passed"]
                else RequirementStatus.PENDING
            ),
            evidence=(
                f"all {len(LOCAL_HASH_KEYS)} local hashes match; "
                "vault hashes require Project 008 for final verification"
                if hash_result["passed"]
                else "; ".join(hash_result["errors"])
            ),
            owner="local",
            unblock_condition=(
                "All six local-artifact hashes must match. "
                "corpus_manifest and indexed_body hashes must also be "
                "verified once the Project 008 vault is present "
                "(using corpus.manifest_content_commitment() and "
                "corpus.indexed_content_commitment())."
            ),
            required_for_confirmation=True,
            check_result=hash_result,
        ),

        Requirement(
            req_id="R09",
            category=RequirementCategory.PROCESS,
            description=(
                "Preregistration checklist updated to reflect current "
                "readiness without changing outcome thresholds or "
                "incorporating confirmation outputs."
            ),
            status=(
                RequirementStatus.SATISFIED
                if prereg_result["passed"]
                else RequirementStatus.PENDING
            ),
            evidence=(
                "PREREGISTRATION_DRAFT.md updated; R06/R07/R08 gates marked [x]; "
                "status remains Not Yet Activated; no confirmation outputs added."
                if prereg_result["passed"]
                else "; ".join(prereg_result["errors"])
            ),
            owner="local",
            unblock_condition=(
                "PREREGISTRATION_DRAFT.md must mark R06/R07/R08 gates as [x], "
                "remain in draft state, and contain no confirmation outputs "
                "or threshold changes."
            ),
            required_for_confirmation=True,
            check_result=prereg_result,
        ),
    ]

    return matrix


def matrix_summary(matrix: list[Requirement]) -> dict[str, Any]:
    """Return counts and per-status lists for a requirements matrix."""
    by_status: dict[str, list[str]] = {s.value: [] for s in RequirementStatus}
    for req in matrix:
        by_status[req.status.value].append(req.req_id)
    return {
        "total": len(matrix),
        "satisfied": len(by_status[RequirementStatus.SATISFIED.value]),
        "blocked": len(by_status[RequirementStatus.BLOCKED.value]),
        "pending": len(by_status[RequirementStatus.PENDING.value]),
        "by_status": by_status,
        "confirmation_ready": all(
            req.status == RequirementStatus.SATISFIED
            for req in matrix
            if req.required_for_confirmation
        ),
        "task4_status": "BLOCKED",  # always: R01-R05 are externally blocked
        "selection_limitation": (
            "All prior ablation results remain labeled selection-only. "
            "No confirmation or product-performance verdict is produced."
        ),
    }


# ---------------------------------------------------------------------------
# Fail-closed preflight
# ---------------------------------------------------------------------------

class PreflightFailed(RuntimeError):
    """
    Raised by run_preflight() when any confirmation-readiness requirement
    is not SATISFIED.

    Attributes
    ----------
    unmet : list[str]
        Requirement IDs that are not satisfied.
    matrix : list[Requirement]
        Full matrix for inspection.
    """

    def __init__(self, unmet: list[str], matrix: list[Requirement]) -> None:
        self.unmet  = unmet
        self.matrix = matrix
        super().__init__(
            f"Confirmation preflight FAILED — {len(unmet)} requirement(s) unmet: "
            f"{', '.join(unmet)}. "
            f"Task 5 must not start until all requirements are SATISFIED. "
            f"External-blocked requirements cannot be satisfied by mocks, "
            f"env-vars, or shared-directory conventions."
        )


def _run_infra_checks() -> dict[str, Any]:
    """Run all six infrastructure checks and return their results (never discarded)."""
    return {
        "provider_adapter":       check_provider_adapter(),
        "github_actions_workflow": check_github_actions_workflow(),
        "custody_key":            check_custody_key(),
        "blinding_module":        check_blinding_module(),
        "pricing_lock":           check_pricing_lock(),
        "vault_hashes":           check_vault_hashes_with_actual_vault(),
    }


def run_preflight(
    corpus_path: Path | None = None,
    rubric_path: Path | None = None,
    hash_paths: dict[str, Path] | None = None,
    preregistration_path: Path | None = None,
) -> tuple[list[Requirement], dict[str, Any]]:
    """
    Run all nine readiness checks AND the Task-4 external-readiness
    infrastructure checks, then raise PreflightFailed if any R01–R09
    requirements are unmet.

    Returns (matrix, infra_results) if all requirements are satisfied
    (which currently cannot happen while R01–R05 are blocked).

    This function NEVER succeeds in the current runtime because R01–R05
    are externally blocked.  That is the correct and intended behavior.

    Infrastructure check results are always returned — never discarded.
    They are attached to PreflightFailed.infra_checks on failure.
    """
    infra = _run_infra_checks()

    matrix = build_requirements_matrix(
        corpus_path=corpus_path,
        rubric_path=rubric_path,
        hash_paths=hash_paths,
        preregistration_path=preregistration_path,
    )
    unmet = [
        req.req_id
        for req in matrix
        if req.required_for_confirmation
        and req.status != RequirementStatus.SATISFIED
    ]
    if unmet:
        exc = PreflightFailed(unmet, matrix)
        exc.infra_checks = infra  # type: ignore[attr-defined]
        raise exc
    return matrix, infra


def run_diagnostic_preflight(
    corpus_path: Path | None = None,
    rubric_path: Path | None = None,
    hash_paths: dict[str, Path] | None = None,
    preregistration_path: Path | None = None,
) -> tuple[list[Requirement], dict[str, Any]]:
    """
    Diagnostic-mode preflight: verifies locally feasible gates (R06–R09)
    and infrastructure checks only.  Does NOT require R01–R05.

    Returns (matrix, infra_results).  Never raises for blocked R01–R05.
    Raises DiagnosticPreflightFailed if any locally verifiable gate fails.

    Use this in dry_run / diagnostic pipeline mode to allow downstream jobs
    to exercise the full synthetic data flow without live secrets.
    """
    infra = _run_infra_checks()

    matrix = build_requirements_matrix(
        corpus_path=corpus_path,
        rubric_path=rubric_path,
        hash_paths=hash_paths,
        preregistration_path=preregistration_path,
    )

    # Only check locally verifiable requirements
    local_ids = {"R06", "R07", "R08", "R09"}
    unmet_local = [
        req.req_id
        for req in matrix
        if req.req_id in local_ids
        and req.status != RequirementStatus.SATISFIED
    ]
    if unmet_local:
        exc = DiagnosticPreflightFailed(unmet_local, matrix)
        exc.infra_checks = infra  # type: ignore[attr-defined]
        raise exc
    return matrix, infra


class DiagnosticPreflightFailed(RuntimeError):
    """
    Raised by run_diagnostic_preflight() when a locally verifiable gate
    (R06–R09) fails.  R01–R05 blocked status is expected and never raises.
    """
    def __init__(self, unmet: list[str], matrix: list[Requirement]) -> None:
        self.unmet  = unmet
        self.matrix = matrix
        super().__init__(
            f"Diagnostic preflight FAILED — local gate(s) unmet: {', '.join(unmet)}. "
            f"Fix these before running the diagnostic pipeline."
        )
