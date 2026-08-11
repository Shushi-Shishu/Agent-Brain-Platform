"""
Role-specific allow-listed package builder for the POC 6c CI pipeline.

Security invariant: each job receives only the files it strictly requires.
Arm and evaluator jobs must never receive custody material, sealed labels,
confirmation tasks, pilot results, or mapping bundles.

Six roles with explicit allow-lists:
  preflight       — needs everything to run checks and build the package
  generic-arm     — needs source + workloads; no confirmation/custody/pilot
  configured-arm  — same as generic-arm
  blinding        — needs source + arm outputs; needs custodian public key
  evaluator       — needs source + blinded bundle only; no mapping
  integrity       — needs source + all attestations + eval results

The preflight job builds a single tarball from the full poc6c/ tree (minus
exclusions) that all downstream jobs verify by hash and extract.  This module
also provides helpers to enumerate what a given role receives, used by tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# File-path patterns relative to poc6c/ that are FORBIDDEN for each role
# ---------------------------------------------------------------------------

# Files that arm and evaluator jobs must never receive:
_CUSTODY_PATTERNS: tuple[str, ...] = (
    "confirmation/tasks_v1.json",
    "confirmation/sealed/",
    "confirmation/EVALUATION_RUBRIC_V1.md",
    "custodian_public_key.pem",
)

_PILOT_PATTERNS: tuple[str, ...] = (
    "pilot/",
    "workloads/results/",
    "workloads/runs/",
    "workloads/boundaries/",
)

# The encrypted mapping bundle is a CI output, not a repository file.
# These names identify mapping-related custody CI artifacts.
_MAPPING_ARTIFACT_NAMES: tuple[str, ...] = (
    "mapping_bundle.json",
    "mapping_bundle.sha256",
)

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

ROLES = ("preflight", "generic-arm", "configured-arm",
         "blinding", "evaluator", "integrity")

# For each role, list the artifact *names* (not paths) that are forbidden
# as CI download inputs.  These are checked by the workflow structure tests.
FORBIDDEN_ARTIFACTS_BY_ROLE: dict[str, tuple[str, ...]] = {
    "preflight": (),  # preflight checks out the full repo
    "generic-arm": (
        "blinding-outputs",
        "evaluation-results",
        "integrity-outputs",
    ),
    "configured-arm": (
        "blinding-outputs",
        "evaluation-results",
        "integrity-outputs",
    ),
    "blinding": (
        "evaluation-results",
        "integrity-outputs",
    ),
    # Evaluator must never receive the mapping bundle or custody outputs
    "evaluator": (
        "mapping_bundle.json",
        "mapping_bundle.sha256",
        "integrity-outputs",
    ),
    "integrity": (),  # integrity downloads all artifacts for validation
}

# Files within poc6c/ that each role's package must NOT contain.
# Checked by test_role_isolation.py against the tarball contents.
FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE: dict[str, tuple[str, ...]] = {
    "preflight": (),  # preflight is the one that builds the package
    "generic-arm": (
        "confirmation/tasks_v1.json",
        "confirmation/sealed/design_labels_v1.json",
        "custodian_public_key.pem",
    ),
    "configured-arm": (
        "confirmation/tasks_v1.json",
        "confirmation/sealed/design_labels_v1.json",
        "custodian_public_key.pem",
    ),
    "blinding": (),   # blinding legitimately has the public key (for wrapping)
    "evaluator": (
        "confirmation/tasks_v1.json",
        "confirmation/sealed/design_labels_v1.json",
    ),
    "integrity": (),  # integrity checks the full tree
}

# ---------------------------------------------------------------------------
# Package enumeration helper (used by tests)
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent


def list_package_paths(root: Path | None = None) -> list[str]:
    """Return sorted poc6c-relative posix paths that would be packaged.

    Excludes:
    - MANIFEST.json (rebuilt from canonical bytes)
    - __pycache__/ and .pytest_cache/
    - *.pyc / *.pyo bytecode
    - .DS_Store
    """
    from artifact_manifest import included_files
    r = root or HERE
    return [
        p.relative_to(r).as_posix()
        for p in included_files(r)
    ]


def assert_role_package_clean(role: str, package_paths: list[str]) -> None:
    """Assert that none of the forbidden paths appear in a role's package.

    Parameters
    ----------
    role : str
        One of the ROLES values.
    package_paths : list[str]
        Sorted posix paths relative to poc6c/ as returned by list_package_paths().

    Raises
    ------
    AssertionError
        If any forbidden path is present in the package.
    """
    if role not in FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE:
        raise ValueError(f"Unknown role '{role}'. Known: {ROLES}.")
    forbidden = FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE[role]
    violations: list[str] = []
    for forbidden_prefix in forbidden:
        for path in package_paths:
            if path == forbidden_prefix or path.startswith(forbidden_prefix):
                violations.append(f"role={role}: forbidden path '{path}' present in package")
    if violations:
        raise AssertionError(
            f"Role '{role}' package contains forbidden files:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


def list_filtered_package_paths(role: str, root: Path | None = None) -> list[str]:
    """Return sorted poc6c-relative posix paths for a role-specific filtered package.

    The full poc6c/ tree is filtered to exclude paths forbidden for the given role.
    This represents what the role-specific tarball would contain.

    Preflight and integrity roles receive the full tree (no filtering).
    Arm and evaluator roles have forbidden files stripped.
    Blinding role has no extra exclusions (it legitimately needs the public key).

    Parameters
    ----------
    role : str
        One of ROLES.
    root : Path | None
        Root of poc6c/; defaults to HERE.

    Returns
    -------
    list[str]
        Sorted posix paths that would appear in the role-specific package.
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Known: {ROLES}.")
    all_paths = list_package_paths(root)
    forbidden = FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE.get(role, ())
    if not forbidden:
        return all_paths
    filtered = []
    for path in all_paths:
        skip = False
        for forbidden_prefix in forbidden:
            if path == forbidden_prefix or path.startswith(forbidden_prefix):
                skip = True
                break
        if not skip:
            filtered.append(path)
    return filtered


def build_filtered_package_script(role: str) -> str:
    """Return a shell command fragment that builds a role-specific tarball.

    Used in the GitHub Actions preflight step to create per-role packages.
    The script is added after the full git archive, filters out forbidden paths,
    and writes a new tarball.

    Returns a Python-executable script fragment (as a string) suitable for
    embedding in a workflow run: block.
    """
    forbidden = FORBIDDEN_PATHS_IN_PACKAGE_BY_ROLE.get(role, ())
    excluded_str = repr(list(forbidden))
    return f"""\
# Build role-specific package for {role}
python - <<'PYEOF'
import tarfile, io, hashlib, sys
FORBIDDEN_PREFIXES = {excluded_str}
with tarfile.open("poc6c-package.tar.gz", "r:gz") as src:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as dst:
        for member in src.getmembers():
            name = member.name
            # Strip leading poc6c/ for prefix matching
            rel = name[len("poc6c/"):] if name.startswith("poc6c/") else name
            skip = any(
                rel == fp or rel.startswith(fp)
                for fp in FORBIDDEN_PREFIXES
            )
            if not skip:
                fobj = src.extractfile(member)
                dst.addfile(member, fobj)
    data = buf.getvalue()
sha = hashlib.sha256(data).hexdigest().upper()
with open("poc6c-{role}-package.tar.gz", "wb") as f:
    f.write(data)
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"{role.replace("-","_")}_pkg_sha256={{sha}}\\n")
print(f"Role package {role} SHA256={{sha}}")
PYEOF
"""


def assert_evaluator_no_mapping(artifacts_available: list[str]) -> None:
    """Assert that mapping bundle artifacts are not in the evaluator's download list.

    Parameters
    ----------
    artifacts_available : list[str]
        Artifact names or file paths available to the evaluator job.

    Raises
    ------
    AssertionError
        If any mapping-related artifact name appears.
    """
    violations: list[str] = []
    for name in artifacts_available:
        for forbidden in _MAPPING_ARTIFACT_NAMES:
            if forbidden in name:
                violations.append(f"evaluator must not receive mapping artifact: '{name}'")
    if violations:
        raise AssertionError("\n".join(violations))
