#!/usr/bin/env python
"""Fail when the ApexOracle-Generation source tree violates release policy."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECOVERY_TAG = "legacy-code-snapshot-2026-08-10"
MAX_TRACKED_BYTES = 10 * 1024 * 1024
REQUIRED_PATHS = (
    "LICENSE",
    "NOTICE",
    "README.md",
    "configs/paper/mic_peptide.yaml",
    "docs/INSTALLATION.md",
    "docs/PAPER_MIC_PEPTIDE_CONFIG.md",
    "reproducibility/g3_legacy_cleanup.json",
    "scripts/reproduce/run_mic_peptide_grid.py",
    "scripts/reproduce/run_paper_mic_peptide.py",
)
FORBIDDEN_ACTIVE_PATHS = ("debug.py", "diffusion_mdlm.py")
RECOVERABLE_PATHS = (
    "debug.py",
    "diffusion_mdlm.py",
    "models/antibiotic_classifier.py",
    "scripts/mol_generate_gpu_00_11775.sh",
)
ABSOLUTE_AUTHOR_PATH = re.compile(r"/(?:data1|data2|share/kuleshov|Users/kirianozan)/")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def release_files() -> list[Path]:
    result = git("ls-files", "-co", "--exclude-standard", "-z")
    return sorted(
        path
        for raw in result.stdout.split("\0")
        if raw and (path := ROOT / raw).is_file()
    )


def main() -> None:
    files = release_files()
    relative = {path.relative_to(ROOT).as_posix() for path in files}
    errors: list[str] = []

    for required in REQUIRED_PATHS:
        if required not in relative:
            errors.append(f"missing required release path: {required}")
    for forbidden in FORBIDDEN_ACTIVE_PATHS:
        if forbidden in relative:
            errors.append(f"obsolete active path remains: {forbidden}")
    legacy_launchers = sorted(
        path
        for path in relative
        if path.startswith("scripts/mol_generate_gpu_")
        or path.startswith("scripts/temp_Ben_gpu_")
    )
    if legacy_launchers:
        errors.append(f"legacy launchers remain: {legacy_launchers}")

    oversized = sorted(
        (path.relative_to(ROOT).as_posix(), path.stat().st_size)
        for path in files
        if path.stat().st_size > MAX_TRACKED_BYTES
    )
    if oversized:
        errors.append(f"release files exceed {MAX_TRACKED_BYTES} bytes: {oversized}")

    for prefix in (ROOT / "configs/paper", ROOT / "scripts/reproduce"):
        for path in sorted(prefix.rglob("*")):
            if (
                path.is_file()
                and path.suffix in {".py", ".yaml", ".yml"}
                and ABSOLUTE_AUTHOR_PATH.search(path.read_text(encoding="utf-8"))
            ):
                errors.append(
                    "author-machine absolute path in canonical release entry: "
                    f"{path.relative_to(ROOT)}"
                )

    tag_type = git("cat-file", "-t", RECOVERY_TAG, check=False)
    tag = git("rev-parse", f"{RECOVERY_TAG}^{{commit}}", check=False)
    if tag.returncode or tag_type.stdout.strip() != "tag":
        errors.append(f"missing annotated recovery tag: {RECOVERY_TAG}")
    else:
        for path in RECOVERABLE_PATHS:
            recovered = git("cat-file", "-e", f"{RECOVERY_TAG}:{path}", check=False)
            if recovered.returncode:
                errors.append(f"recovery tag lacks path: {path}")

    summary = {
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "release_file_count": len(files),
        "largest_release_file_bytes": max(
            (path.stat().st_size for path in files), default=0
        ),
        "recovery_tag": RECOVERY_TAG,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
