"""Manifest-driven multi-strain generation grid contracts."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reproduce" / "run_mic_peptide_grid.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generation_grid", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_job_manifest_and_commands_are_explicit(tmp_path: Path) -> None:
    module = load_module()
    manifest = tmp_path / "jobs.csv"
    manifest.write_text(
        "job_id,strain,target_length,device,global_batch_size,num_sample_batches\n"
        "strain_a_280,strain-A,280,0,2,3\n"
        "strain_b_368,#002,368,1,,\n",
        encoding="utf-8",
    )
    jobs = module.load_jobs(manifest)
    assert [job.job_id for job in jobs] == ["strain_a_280", "strain_b_368"]
    assert jobs[0].global_batch_size == 2
    assert jobs[0].num_sample_batches == 3
    command = module.build_job_command(
        ROOT,
        jobs[0],
        mdlm_root=tmp_path / "mdlm",
        core_root=tmp_path / "core",
        output_root=tmp_path / "outputs",
        dry_run=True,
    )
    assert "--strain" in command and "strain-A" in command
    assert "--target-length" in command and "280" in command
    assert "--global-batch-size" in command and "2" in command
    assert "--num-sample-batches" in command and "3" in command
    assert command[-1] == "--dry-run"


def test_job_manifest_rejects_path_traversal_and_duplicates(tmp_path: Path) -> None:
    module = load_module()
    traversal = tmp_path / "traversal.csv"
    traversal.write_text(
        "job_id,strain,target_length,device\n../escape,A,280,0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid job_id"):
        module.load_jobs(traversal)

    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text(
        "job_id,strain,target_length,device\nsame,A,280,0\nsame,B,300,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        module.load_jobs(duplicate)


def test_removed_legacy_sources_are_hash_verified_and_recoverable() -> None:
    manifest = json.loads(
        (ROOT / "reproducibility/g3_legacy_cleanup.json").read_text(encoding="utf-8")
    )
    records = [manifest["debug_source"], manifest["unused_diffusion_copy"]]
    records.extend(manifest["historical_launchers"]["files"])
    records.extend(manifest["historical_orchestrators"])
    for record in records:
        path = record["path"]
        assert not (ROOT / path).exists(), path
        payload = subprocess.check_output(
            ["git", "show", f"{manifest['recovery_ref']}:{path}"], cwd=ROOT
        )
        assert hashlib.sha256(payload).hexdigest() == record["sha256"], path
    assert "import diffusion_mdlm" not in (ROOT / "main.py").read_text(encoding="utf-8")
    assert manifest["caller_audit"]["live_runtime_consumers"] == 0
    assert manifest["deletion_gate"]["generic_grid_replacement_present"]
