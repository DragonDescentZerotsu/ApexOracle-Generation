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
    parser.add_argument("--strain", choices=tuple(STRAIN_LENGTHS), default="BAA-3170")
    parser.add_argument("--target-length", type=int)
    parser.add_argument("--device", type=int, default=0)
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
    for asset_id, relative, expected_count in CONDITION_DIRECTORIES:
        path = core_root / relative
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
                "owner": "core",
                "relative_path": relative,
                "file_count": actual_count,
                "expected_file_count": expected_count,
            }
        )

    for asset_id, (owner, relative, expected_hash) in ASSETS.items():
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
    output_dir = validate_new_output_directory(args.output_dir)
    target_length = args.target_length or STRAIN_LENGTHS[args.strain]
    assets = validate_roots_and_assets(
        generation_root,
        mdlm_root,
        core_root,
        check_hashes=args.check_asset_hashes,
    )

    environment = os.environ.copy()
    environment.update(
        {
            "APEXORACLE_GENERATION_ROOT": str(generation_root),
            "APEXORACLE_MDLM_ROOT": str(mdlm_root),
            "APEXORACLE_CORE_ROOT": str(core_root),
            "APEXORACLE_GENERATION_RUN_DIR": str(output_dir),
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
    )

    launch = {
        "schema_version": 1,
        "protocol": "paper_mic_peptide_guided_v1",
        "mode": "smoke" if args.smoke else "paper",
        "dry_run": args.dry_run,
        "strain": args.strain,
        "target_length": target_length,
        "output_dir": str(output_dir),
        "command": command,
        "assets": assets,
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
