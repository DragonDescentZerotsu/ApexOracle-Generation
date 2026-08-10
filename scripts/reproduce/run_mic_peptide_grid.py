#!/usr/bin/env python
"""Run a manifest-defined MIC+peptide strain/length grid."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class GenerationJob:
    job_id: str
    strain: str
    target_length: int
    device: int
    global_batch_size: int | None = None
    num_sample_batches: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-manifest", type=Path, required=True)
    parser.add_argument("--mdlm-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-experimental-extension",
        action="store_true",
        help="Acknowledge that a multi-strain grid is not the frozen paper run.",
    )
    return parser.parse_args()


def optional_positive_int(row: dict[str, str], field: str) -> int | None:
    raw = (row.get(field) or "").strip()
    if not raw:
        return None
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{field} must be positive, found {value}")
    return value


def load_jobs(path: Path) -> list[GenerationJob]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"job_id", "strain", "target_length", "device"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Job manifest lacks columns: {sorted(missing)}")
        jobs = []
        for line_number, row in enumerate(reader, start=2):
            job_id = row["job_id"].strip()
            strain = row["strain"].strip()
            if not JOB_ID_PATTERN.fullmatch(job_id):
                raise ValueError(f"Invalid job_id at line {line_number}: {job_id!r}")
            if not strain:
                raise ValueError(f"Empty strain at line {line_number}")
            target_length = int(row["target_length"])
            device = int(row["device"])
            if target_length <= 0 or device < 0:
                raise ValueError(
                    f"Invalid target_length/device at line {line_number}: "
                    f"{target_length}/{device}"
                )
            jobs.append(
                GenerationJob(
                    job_id=job_id,
                    strain=strain,
                    target_length=target_length,
                    device=device,
                    global_batch_size=optional_positive_int(row, "global_batch_size"),
                    num_sample_batches=optional_positive_int(row, "num_sample_batches"),
                )
            )
    if not jobs:
        raise ValueError("Job manifest is empty")
    job_ids = [job.job_id for job in jobs]
    if len(job_ids) != len(set(job_ids)):
        raise ValueError("Job manifest contains duplicate job_id values")
    return jobs


def build_job_command(
    generation_root: Path,
    job: GenerationJob,
    *,
    mdlm_root: Path,
    core_root: Path,
    output_root: Path,
    dry_run: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(generation_root / "scripts/reproduce/run_paper_mic_peptide.py"),
        "--mdlm-root",
        str(mdlm_root),
        "--core-root",
        str(core_root),
        "--output-dir",
        str(output_root / job.job_id),
        "--strain",
        job.strain,
        "--target-length",
        str(job.target_length),
        "--device",
        str(job.device),
    ]
    if job.global_batch_size is not None:
        command.extend(["--global-batch-size", str(job.global_batch_size)])
    if job.num_sample_batches is not None:
        command.extend(["--num-sample-batches", str(job.num_sample_batches)])
    if dry_run:
        command.append("--dry-run")
    return command


def run_device_queue(
    device_jobs: list[GenerationJob],
    *,
    generation_root: Path,
    mdlm_root: Path,
    core_root: Path,
    output_root: Path,
    dry_run: bool,
) -> list[dict[str, Any]]:
    results = []
    for job in device_jobs:
        command = build_job_command(
            generation_root,
            job,
            mdlm_root=mdlm_root,
            core_root=core_root,
            output_root=output_root,
            dry_run=dry_run,
        )
        completed = subprocess.run(command, cwd=generation_root, check=False)
        results.append(
            {
                "job": asdict(job),
                "command": command,
                "exit_code": completed.returncode,
            }
        )
        if completed.returncode:
            break
    return results


def main() -> None:
    args = parse_args()
    if not args.confirm_experimental_extension:
        raise ValueError(
            "Pass --confirm-experimental-extension: a grid is not the frozen paper run"
        )
    generation_root = Path(__file__).resolve().parents[2]
    mdlm_root = args.mdlm_root.expanduser().resolve()
    core_root = args.core_root.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    if output_root.exists():
        raise FileExistsError(
            f"Refusing to reuse grid output root; choose a new path: {output_root}"
        )
    jobs = load_jobs(args.job_manifest)
    queues: dict[int, list[GenerationJob]] = defaultdict(list)
    for job in jobs:
        queues[job.device].append(job)

    if not args.dry_run:
        output_root.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=len(queues)) as executor:
        futures = [
            executor.submit(
                run_device_queue,
                device_jobs,
                generation_root=generation_root,
                mdlm_root=mdlm_root,
                core_root=core_root,
                output_root=output_root,
                dry_run=args.dry_run,
            )
            for _, device_jobs in sorted(queues.items())
        ]
        results = [item for future in futures for item in future.result()]
    results.sort(key=lambda item: item["job"]["job_id"])
    summary = {
        "schema_version": 1,
        "scope": "experimental_multi_strain_mic_peptide_grid",
        "dry_run": args.dry_run,
        "job_count": len(jobs),
        "device_queues": {
            str(device): [job.job_id for job in device_jobs]
            for device, device_jobs in sorted(queues.items())
        },
        "results": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not args.dry_run:
        (output_root / "grid_run_manifest.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    failed = [item for item in results if item["exit_code"]]
    if failed:
        raise SystemExit(failed[0]["exit_code"])


if __name__ == "__main__":
    main()
