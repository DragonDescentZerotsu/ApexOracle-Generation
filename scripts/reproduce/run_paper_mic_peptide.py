#!/usr/bin/env python
"""Launch the frozen ApexOracle paper MIC+peptide preset safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ASSETS = {
    "dlm_generator": (
        "mdlm",
        "Checkpoints_fangping/last_reg_v1.ckpt",
        "a509b94e3780a0848b3f799ccfe754ed07524169973b08d85fdbc597f0592615",
    ),
    "noisy_mic_guidance": (
        "core",
        "Checkpoints/genome_text_learnable_emb/guidance_regressor_pad_no_mask/"
        "noise_guidance_best_R2_all_peptide_epoch_100.pth",
        "f24faf670b804edebbd4d6530a42c1351b62040046e14ebded67335aefc9c3a4",
    ),
    "noisy_peptide_classifier": (
        "mdlm",
        "cls-guide-pad-no-mask-checkpoints/"
        "epoch-epoch=1-step-step=134000-train_loss-train_loss=0.008.ckpt",
        "40f638ca5668f20a641a538035015b1741ab69cded300cba27f7148cc291945b",
    ),
}

COMPACT_ASSETS = {
    "dlm_generator": (
        "checkpoints/dlm_generator_inference.ckpt",
        "2603e875fd1882f45abab52105c275cb94e2f2aa84c7f35beb318c1a8ab80d4a",
    ),
    "noisy_mic_guidance": (
        "checkpoints/noisy_mic_guidance_inference.pth",
        "734079f8b5b2d60146a38aa1c34271f5ba712c2d24515b8a2c25b6ecf7db492e",
    ),
    "noisy_peptide_classifier": (
        "checkpoints/noisy_peptide_classifier_inference.ckpt",
        "632091509bbcda82384ffef5cd59ffbef3c38716df319c59db2167cddb7ab7ca",
    ),
}

CONDITION_DIRECTORIES = (
    ("genome_embeddings", "DataPrepare/Data/Genome_embs", 567),
    (
        "atcc_text_embeddings",
        "DataPrepare/Data/Text_Description/ATCC/embeddings",
        568,
    ),
    (
        "text_only_embeddings",
        "DataPrepare/Data/Text_Description/wo_ATCC/embeddings",
        1079,
    ),
)

STRAIN_LENGTHS = {"BAA-3170": 368, "BAA-3197": 232}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mdlm-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--asset-root",
        type=Path,
        help="Use the released compact checkpoint and BAA-3170 condition bundle.",
    )
    parser.add_argument("--strain", default="BAA-3170")
    parser.add_argument("--target-length", type=int)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--global-batch-size", type=int)
    parser.add_argument("--num-sample-batches", type=int)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run one sample on one visible GPU while preserving the paper sampler schedule.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print the Hydra job config without loading checkpoints or sampling.",
    )
    parser.add_argument(
        "--check-asset-hashes",
        action="store_true",
        help="Recompute all three large checkpoint SHA-256 values before launch.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_roots_and_assets(
    generation_root: Path,
    mdlm_root: Path,
    core_root: Path,
    *,
    check_hashes: bool,
    asset_root: Path | None = None,
) -> list[dict[str, Any]]:
    roots = {"generation": generation_root, "mdlm": mdlm_root, "core": core_root}
    required_paths = (
        generation_root / "main.py",
        generation_root / "configs" / "config_mdlm_cls.yaml",
        generation_root / "configs" / "paper" / "mic_peptide.yaml",
        mdlm_root / "src" / "apexoracle_mdlm",
    )
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(path)
    records: list[dict[str, Any]] = []
    compact_conditions = (
        ("genome_embeddings", "conditions/genome", 1),
        ("atcc_text_embeddings", "conditions/atcc_text", 1),
        ("text_only_embeddings", "conditions/text_only", 0),
    )
    condition_records = compact_conditions if asset_root else CONDITION_DIRECTORIES
    for asset_id, relative, expected_count in condition_records:
        path = (asset_root / relative) if asset_root else (core_root / relative)
        if not path.is_dir():
            raise NotADirectoryError(path)
        actual_count = sum(child.is_file() for child in path.iterdir())
        if actual_count != expected_count:
            raise ValueError(
                f"Unexpected {asset_id} file count: {actual_count} != {expected_count}"
            )
        records.append(
            {
                "id": asset_id,
                "owner": "compact_asset_bundle" if asset_root else "core",
                "relative_path": relative,
                "file_count": actual_count,
                "expected_file_count": expected_count,
            }
        )

    asset_records = COMPACT_ASSETS if asset_root else ASSETS
    for asset_id, spec in asset_records.items():
        if asset_root:
            relative, expected_hash = spec
            owner = "compact_asset_bundle"
            path = asset_root / relative
        else:
            owner, relative, expected_hash = spec
            path = roots[owner] / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        record: dict[str, Any] = {
            "id": asset_id,
            "owner": owner,
            "relative_path": relative,
            "bytes": path.stat().st_size,
            "expected_sha256": expected_hash,
            "hash_status": "not_requested",
        }
        if check_hashes:
            actual_hash = sha256(path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"SHA-256 mismatch for {asset_id}: {actual_hash} != {expected_hash}"
                )
            record["actual_sha256"] = actual_hash
            record["hash_status"] = "passed"
        records.append(record)
    return records


def validate_new_output_directory(output_dir: Path) -> Path:
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to reuse output directory; choose a new path: {output_dir}"
        )
    if output_dir == output_dir.parent:
        raise ValueError(f"Refusing broad output directory: {output_dir}")
    return output_dir


def build_command(
    generation_root: Path,
    *,
    strain: str,
    target_length: int,
    smoke: bool,
    dry_run: bool,
    global_batch_size: int | None = None,
    num_sample_batches: int | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(generation_root / "main.py"),
        "+paper=mic_peptide",
        f"sampling.strain={strain}",
        f"sampling.target_length={target_length}",
        "trainer.devices=1",
    ]
    if smoke:
        command.extend(["loader.global_batch_size=1", "sampling.num_sample_batches=1"])
    else:
        if global_batch_size is not None:
            command.append(f"loader.global_batch_size={global_batch_size}")
        if num_sample_batches is not None:
            command.append(f"sampling.num_sample_batches={num_sample_batches}")
    if dry_run:
        command.extend(["--cfg", "job", "--resolve"])
    return command


def summarize_outputs(output_dir: Path) -> dict[str, Any]:
    selfies_files = sorted(output_dir.glob("strain_*_MIC_*_length_*.txt"))
    selfies = []
    for path in selfies_files:
        rows = path.read_text(encoding="utf-8").splitlines()
        selfies.append(
            {
                "relative_path": path.relative_to(output_dir).as_posix(),
                "rows": len(rows),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    hydra_config = output_dir / ".hydra" / "config.yaml"
    return {
        "selfies_files": selfies,
        "molecule_image_count": len(
            list((output_dir / "molecule_images").glob("*.png"))
        ),
        "hydra_config": (
            {
                "relative_path": ".hydra/config.yaml",
                "bytes": hydra_config.stat().st_size,
                "sha256": sha256(hydra_config),
            }
            if hydra_config.is_file()
            else None
        ),
    }


def main() -> None:
    args = parse_args()
    generation_root = Path(__file__).resolve().parents[2]
    mdlm_root = args.mdlm_root.expanduser().resolve()
    core_root = args.core_root.expanduser().resolve()
    asset_root = args.asset_root.expanduser().resolve() if args.asset_root else None
    output_dir = validate_new_output_directory(args.output_dir)
    if args.target_length is None:
        if args.strain not in STRAIN_LENGTHS:
            raise ValueError(
                "--target-length is required for strains outside the two paper defaults"
            )
        target_length = STRAIN_LENGTHS[args.strain]
    else:
        target_length = args.target_length
    for name, value in (
        ("target_length", target_length),
        ("global_batch_size", args.global_batch_size),
        ("num_sample_batches", args.num_sample_batches),
    ):
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be positive, found {value}")
    if args.smoke and (
        args.global_batch_size is not None or args.num_sample_batches is not None
    ):
        raise ValueError(
            "--smoke cannot be combined with explicit workload-size overrides"
        )
    assets = validate_roots_and_assets(
        generation_root,
        mdlm_root,
        core_root,
        check_hashes=args.check_asset_hashes,
        asset_root=asset_root,
    )

    if asset_root:
        if args.strain != "BAA-3170":
            raise ValueError("The released compact asset bundle supports only BAA-3170")
        runtime_assets = {
            "dlm": asset_root / COMPACT_ASSETS["dlm_generator"][0],
            "mic": asset_root / COMPACT_ASSETS["noisy_mic_guidance"][0],
            "peptide": asset_root / COMPACT_ASSETS["noisy_peptide_classifier"][0],
            "genome": asset_root / "conditions/genome",
            "atcc_text": asset_root / "conditions/atcc_text",
            "text_only": asset_root / "conditions/text_only",
        }
    else:
        runtime_assets = {
            "dlm": mdlm_root / ASSETS["dlm_generator"][1],
            "mic": core_root / ASSETS["noisy_mic_guidance"][1],
            "peptide": mdlm_root / ASSETS["noisy_peptide_classifier"][1],
            "genome": core_root / CONDITION_DIRECTORIES[0][1],
            "atcc_text": core_root / CONDITION_DIRECTORIES[1][1],
            "text_only": core_root / CONDITION_DIRECTORIES[2][1],
        }

    environment = os.environ.copy()
    environment.update(
        {
            "APEXORACLE_GENERATION_ROOT": str(generation_root),
            "APEXORACLE_MDLM_ROOT": str(mdlm_root),
            "APEXORACLE_CORE_ROOT": str(core_root),
            "APEXORACLE_GENERATION_RUN_DIR": str(output_dir),
            "APEXORACLE_DLM_GENERATOR_CHECKPOINT": str(runtime_assets["dlm"]),
            "APEXORACLE_MIC_GUIDANCE_CHECKPOINT": str(runtime_assets["mic"]),
            "APEXORACLE_PEPTIDE_GUIDANCE_CHECKPOINT": str(runtime_assets["peptide"]),
            "APEXORACLE_GENOME_EMBEDDINGS": str(runtime_assets["genome"]),
            "APEXORACLE_ATCC_TEXT_EMBEDDINGS": str(runtime_assets["atcc_text"]),
            "APEXORACLE_TEXT_ONLY_EMBEDDINGS": str(runtime_assets["text_only"]),
            "CUDA_VISIBLE_DEVICES": str(args.device),
        }
    )
    mdlm_source = str(mdlm_root / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{mdlm_source}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else mdlm_source
    )
    command = build_command(
        generation_root,
        strain=args.strain,
        target_length=target_length,
        smoke=args.smoke,
        dry_run=args.dry_run,
        global_batch_size=args.global_batch_size,
        num_sample_batches=args.num_sample_batches,
    )

    launch = {
        "schema_version": 1,
        "protocol": "paper_mic_peptide_guided_v1",
        "mode": "smoke" if args.smoke else "paper",
        "dry_run": args.dry_run,
        "strain": args.strain,
        "target_length": target_length,
        "paper_default_strain": args.strain in STRAIN_LENGTHS,
        "output_dir": str(output_dir),
        "command": command,
        "assets": assets,
        "asset_profile": "compact_baa3170_v1" if asset_root else "full_paper_assets",
    }
    print(json.dumps(launch, indent=2, sort_keys=True))
    result = subprocess.run(command, cwd=generation_root, env=environment, check=False)
    if not args.dry_run and output_dir.is_dir():
        launch["exit_code"] = result.returncode
        launch["outputs"] = summarize_outputs(output_dir)
        (output_dir / "apexoracle_generation_run_manifest.json").write_text(
            json.dumps(launch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
