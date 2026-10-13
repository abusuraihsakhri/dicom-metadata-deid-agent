"""Smoke and regression tests for CSV parsing, API, and browser JavaScript."""
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

os.environ.setdefault("AUDIT_SECRET_KEY", "test-key-not-for-production")

import pytest
from fastapi.testclient import TestClient

from cli import main as main_cli, parse_csv_bool
from dicom_metadata_deid_agent.cli import parse_csv_bool as parse_secondary_bool
from agents.api import app


@pytest.mark.parametrize("value,expected", [
    ("false", False), ("FALSE", False), ("0", False), ("", False),
    ("true", True), ("TRUE", True), ("1", True), ("yes", True),
])
def test_boolean_values(value, expected):
    assert parse_csv_bool(value) is expected
    assert parse_secondary_bool(value) is expected


def test_boolean_invalid():
    for parser in (parse_csv_bool, parse_secondary_bool):
        with pytest.raises(ValueError):
            parser("perhaps")


def test_batch_csv_preserves_false(tmp_path):
    source, output = tmp_path / "cases.csv", tmp_path / "results.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag\n"
        "TASK1,SYNTH1,10,1,false\n"
        "TASK2,SYNTH2,10,1,true\n",
        encoding="utf-8",
    )
    assert main_cli(["batch", "-i", str(source), "-o", str(output)]) == 0
    with output.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["overall_urgency"] == "ROUTINE"
    assert rows[1]["overall_urgency"] == "CRITICAL_STAT_PANIC"


def test_health_and_local_console():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    res = client.get("/")
    assert res.status_code == 200
    assert 'id="audit-form"' in res.text
    assert "Not a DICOM anonymizer" in res.text


def test_api_rejects_phi_and_nonfinite():
    client = TestClient(app)
    base = {
        "task_id": "TASK1", "target_identifier": "SYNTH1",
        "primary_metric": 10, "secondary_metric": 1,
    }
    phi = {**base, "attributes": {"note": "MRN-12345678"}}
    response = client.post("/api/audit", json=phi)
    assert response.status_code == 422
    assert "MRN-12345678" not in response.text
    nonfinite = {**base, "primary_metric": "nan"}
    assert client.post("/api/audit", json=nonfinite).status_code == 422


def test_embedded_javascript_syntax(tmp_path):
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Node.js not installed")
    text = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    sections = re.findall(r"<script>(.*?)</script>", text, re.DOTALL)
    assert len(sections) == 1
    script = tmp_path / "console.js"
    script.write_text(sections[0], encoding="utf-8")
    result = subprocess.run([executable, "--check", str(script)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
