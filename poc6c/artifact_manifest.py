"""Content-addressed reproducibility manifest for POC 6c artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXCLUDED_NAMES = {
    "MANIFEST.json",
    ".DS_Store",
}
EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def included_files(root: Path) -> list[Path]:
    root = Path(root)
    return [
        path
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
        and path.name not in EXCLUDED_NAMES
        and path.suffix not in {".pyc", ".pyo"}
        and not EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
    ]


def build_manifest(root: Path) -> dict:
    root = Path(root).resolve()
    files = included_files(root)
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in files
    ]
    payload = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "schema": "poc6c-artifact-manifest-v1",
        "file_count": len(records),
        "total_bytes": sum(record["size_bytes"] for record in records),
        "records_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest().upper(),
        "files": records,
    }


def verify_manifest(root: Path, manifest: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "poc6c-artifact-manifest-v1":
        return ["unsupported manifest schema"]
    actual = build_manifest(root)
    expected_by_path = {
        record["path"]: record for record in manifest.get("files", [])
    }
    actual_by_path = {record["path"]: record for record in actual["files"]}
    missing = sorted(expected_by_path.keys() - actual_by_path.keys())
    extra = sorted(actual_by_path.keys() - expected_by_path.keys())
    changed = sorted(
        path
        for path in expected_by_path.keys() & actual_by_path.keys()
        if expected_by_path[path] != actual_by_path[path]
    )
    if missing:
        errors.append(f"missing files: {missing}")
    if extra:
        errors.append(f"extra files: {extra}")
    if changed:
        errors.append(f"changed files: {changed}")
    if not errors and manifest.get("records_sha256") != actual["records_sha256"]:
        errors.append("records hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("write", "verify"))
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "write":
        value = build_manifest(args.root)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest for {value['file_count']} files")
        return 0
    value = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = verify_manifest(args.root, value)
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 2
    print(f"verified manifest for {value['file_count']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
