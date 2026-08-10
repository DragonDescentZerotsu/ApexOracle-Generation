import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_tree_audit_passes():
    completed = subprocess.run(
        [sys.executable, "scripts/audit/check_release_tree.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    summary = json.loads(completed.stdout)
    assert summary["status"] == "passed"
    assert summary["errors"] == []
