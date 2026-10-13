"""Regression tests for DICOM metadata extracts and audit integrity."""
import json
import os

os.environ.setdefault("AUDIT_SECRET_KEY", "test-key-not-for-production")

import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

from dicom_metadata_deid_agent.deidentify import (
    MetadataInspectionError, export_sanitized_metadata, inspect_dicom_file, main
)
from agents.base import AuditTrail


def _make_dicom(path):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.PatientName = "Jane^Private"
    ds.PatientID = "ID99887766"
    ds.PatientBirthDate = "19800101"
    ds.InstitutionName = "Hidden Hospital"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDescription = "SECRET STUDY"
    ds.Modality = "CT"
    ds.Rows = 128
    ds.Columns = 256
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BurnedInAnnotation = "YES"
    ds.add_new((0x0011, 0x1010), "LO", "PRIVATE_SOURCE_DATA")
    ds.PixelData = b"SECRET_PIXELS"
    ds.save_as(str(path), enforce_file_format=True)


def test_inspection_allowlist_excludes_identifiers_and_pixels(tmp_path):
    source = tmp_path / "Jane_Private.dcm"
    _make_dicom(source)
    report = inspect_dicom_file(source)
    as_json = json.dumps(report)
    assert report["technical_metadata"]["Rows"] == 128
    assert report["technical_metadata"]["Modality"] == "CT"
    assert report["burned_in_annotation_flag"] == "YES"
    assert report["source_pixel_data_read"] is False
    assert report["private_element_count"] >= 1
    for private in ("Jane", "ID99887766", "Hidden Hospital", "SECRET STUDY",
                    "PRIVATE_SOURCE_DATA", "SECRET_PIXELS", "StudyInstanceUID",
                    "PatientName", "Jane_Private"):
        assert private not in as_json


def test_metadata_export_refuses_overwrite(tmp_path):
    source, dest = tmp_path / "input.dcm", tmp_path / "safe.json"
    _make_dicom(source)
    report = export_sanitized_metadata(source, dest)
    assert json.loads(dest.read_text(encoding="utf-8")) == report
    with pytest.raises(MetadataInspectionError):
        export_sanitized_metadata(source, dest)
    with pytest.raises(MetadataInspectionError):
        export_sanitized_metadata(source, source)


def test_invalid_dicom_does_not_disclose_path(tmp_path):
    source = tmp_path / "SecretPatientName.dcm"
    source.write_bytes(b"not a DICOM file")
    with pytest.raises(MetadataInspectionError) as error:
        inspect_dicom_file(source)
    assert "SecretPatientName" not in str(error.value)


def test_cli_scan_and_export(tmp_path, capsys):
    source, dest = tmp_path / "input.dcm", tmp_path / "safe.json"
    _make_dicom(source)
    assert main(["scan", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["technical_metadata"]["Rows"] == 128
    assert main(["export", str(source), str(dest)]) == 0
    assert dest.exists()


def test_audit_hmac_detects_modified_entry_and_chain():
    audit = AuditTrail(secret_key="test-integrity-key")
    audit.log("worker", "supervisor", "EVENT", {"status": "OK"})
    audit.log("worker", "supervisor", "EVENT", {"status": "OK"})
    assert audit.verify_integrity()
    audit.logs[0]["event_type"] = "FORGED"
    assert not audit.verify_integrity()
    audit.logs[0]["event_type"] = "EVENT"
    assert audit.verify_integrity()
    audit.logs[1]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_audit_detects_mutated_digest():
    audit = AuditTrail(secret_key="test-integrity-key")
    audit.log("worker", "supervisor", "EVENT", {"status": "OK"})
    audit.logs[0]["payload_hash"] = "a" * 64
    assert not audit.verify_integrity()
