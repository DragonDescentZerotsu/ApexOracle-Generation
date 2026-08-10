"""Portable paper MIC+peptide config and launcher contracts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "configs" / "paper" / "mic_peptide.yaml"
LAUNCHER = ROOT / "scripts" / "reproduce" / "run_paper_mic_peptide.py"


def load_launcher():
    spec = importlib.util.spec_from_file_location(
        "paper_mic_peptide_launcher", LAUNCHER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paper_preset_uses_only_explicit_roots() -> None:
    source = PRESET.read_text(encoding="utf-8")
    config = yaml.safe_load(source)

    assert config["apexoracle_release"]["protocol"] == "paper_mic_peptide_guided_v1"
    assert config["seed"] == 2
    assert config["sampling"]["steps"] == 256
    assert config["sampling"]["strain"] == "BAA-3170"
    assert config["sampling"]["target_length"] == 368
    assert config["sampling"]["num_sample_batches"] == 10
    assert config["guidance"]["var_gamma"]["gamma_l"] == 15.0
    assert config["guidance"]["var_gamma"]["gamma_s"] == 15.0
    assert config["sampling"]["mol_img_save_dir"] == (
        "${oc.env:APEXORACLE_GENERATION_RUN_DIR}/molecule_images"
    )
    assert config["sampling"]["mol_SELFIES_save_dir"] == (
        "${oc.env:APEXORACLE_GENERATION_RUN_DIR}"
    )
    assert config["data"]["cache_dir"].startswith(
        "${oc.env:APEXORACLE_GENERATION_RUN_DIR}"
    )
    assert config["checkpointing"]["save_dir"] == (
        "${oc.env:APEXORACLE_GENERATION_RUN_DIR}"
    )
    assert config["callbacks"]["checkpoint_every_n_steps"]["dirpath"].startswith(
        "${oc.env:APEXORACLE_GENERATION_RUN_DIR}"
    )
    assert "/data1/" not in source
    assert "/data2/" not in source
    assert "/Users/" not in source
    assert config["sampling"]["pretrained_ckpt_path"] == (
        "${oc.env:APEXORACLE_DLM_GENERATOR_CHECKPOINT}"
    )
    assert config["guidance"]["regressor_checkpoint_path"] == (
        "${oc.env:APEXORACLE_MIC_GUIDANCE_CHECKPOINT}"
    )


def test_compact_asset_bundle_contract(tmp_path: Path) -> None:
    launcher = load_launcher()
    mdlm_root = tmp_path / "mdlm"
    (mdlm_root / "src/apexoracle_mdlm").mkdir(parents=True)
    for relative, _ in launcher.COMPACT_ASSETS.values():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"asset")
    for relative in ("conditions/genome", "conditions/atcc_text"):
        path = tmp_path / relative
        path.mkdir(parents=True)
        (path / "Escherichia_coli_ATCC_BAA_3170.pt").write_bytes(b"tensor")
    (tmp_path / "conditions/text_only").mkdir(parents=True)

    records = launcher.validate_roots_and_assets(
        ROOT,
        mdlm_root,
        Path("/unused-core"),
        check_hashes=False,
        asset_root=tmp_path,
    )

    assert len(records) == 6
    assert {record["owner"] for record in records} == {"compact_asset_bundle"}


def test_launcher_requires_a_new_output_directory(tmp_path: Path) -> None:
    launcher = load_launcher()
    output = tmp_path / "new-run"
    assert launcher.validate_new_output_directory(output) == output.resolve()
    output.mkdir()
    with pytest.raises(FileExistsError):
        launcher.validate_new_output_directory(output)


def test_smoke_command_changes_only_workload_size() -> None:
    launcher = load_launcher()
    command = launcher.build_command(
        ROOT,
        strain="BAA-3197",
        target_length=232,
        smoke=True,
        dry_run=True,
    )
    assert "+paper=mic_peptide" in command
    assert "sampling.strain=BAA-3197" in command
    assert "sampling.target_length=232" in command
    assert "loader.global_batch_size=1" in command
    assert "sampling.num_sample_batches=1" in command
    assert "sampling.steps=1" not in command
    assert command[-3:] == ["--cfg", "job", "--resolve"]


def test_extension_command_accepts_explicit_strain_and_workload() -> None:
    launcher = load_launcher()
    command = launcher.build_command(
        ROOT,
        strain="custom-strain",
        target_length=300,
        smoke=False,
        dry_run=False,
        global_batch_size=4,
        num_sample_batches=3,
    )
    assert "sampling.strain=custom-strain" in command
    assert "sampling.target_length=300" in command
    assert "loader.global_batch_size=4" in command
    assert "sampling.num_sample_batches=3" in command


def test_machine_readable_protocol_matches_preset() -> None:
    manifest = json.loads(
        (ROOT / "reproducibility" / "paper_mic_peptide_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["status"] == "portable_preset_and_gpu_smoke_validated"
    assert manifest["protocol"]["steps"] == 256
    assert manifest["protocol"]["gamma_mic"] == 15.0
    assert manifest["protocol"]["gamma_peptide"] == 15.0
    assert manifest["condition_embedding_file_counts"] == {
        "genome": 567,
        "atcc_text": 568,
        "text_only": 1079,
    }
    assert manifest["output_safety"]["requires_absent_output_directory"]


def test_output_summary_preserves_zero_row_success(tmp_path: Path) -> None:
    launcher = load_launcher()
    (tmp_path / ".hydra").mkdir()
    (tmp_path / ".hydra/config.yaml").write_text("sampling: {}\n", encoding="utf-8")
    (tmp_path / "molecule_images").mkdir()
    output = tmp_path / "strain_BAA-3170_MIC_1_length_368_noise.txt"
    output.write_text("", encoding="utf-8")

    summary = launcher.summarize_outputs(tmp_path)
    assert summary["selfies_files"][0]["rows"] == 0
    assert summary["selfies_files"][0]["bytes"] == 0
    assert summary["molecule_image_count"] == 0
    assert summary["hydra_config"]["relative_path"] == ".hydra/config.yaml"
