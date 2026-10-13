# DICOM Metadata De-ID Agent

A Python research utility containing **two distinct functions**: conservative local DICOM technical-metadata inspection, and an existing synthetic-input rule-engine demonstration. The project is **not** a validated DICOM anonymizer or a clinical decision-support system.

## Capabilities and limitations

- **DICOM technical-metadata inspection:** reads a DICOM Part 10 file locally with pydicom, stopping before Pixel Data. Exports only a small allowlist of image-encoding fields (such as Modality, Rows, and Columns) in JSON. Identifiers, UIDs, dates, free text, private elements, and images are **not included** in the report.
- **Metadata risk indicators:** reports counts of excluded/private elements and the source `BurnedInAnnotation` flag where present. These indicators are not an assessment of the image itself.
- **Synthetic rule-engine demo:** preserves the original CLI, REST API, and numeric threshold-alert workflows. Their generic clinical-sounding thresholds have **no established DICOM PS3.15 interpretation**.
- **Audit trail:** HMAC-SHA256 authenticates stored entry metadata and chain links. Original payload details are not retained, so their contents cannot be reconstructed or independently revalidated from the digest alone.

**Safety boundary:** Neither the inspector nor the rule engine performs complete DICOM PS3.15 de-identification. The inspector does not inspect pixel content, burned-in annotations, overlays, structured reports, encapsulated data, or other possible identifiers. A metadata-only JSON extract must be reviewed before disclosure. Never release the original DICOM file on the assumption that this tool anonymized it.

## Install

Python 3.10–3.13:

```bash
git clone https://github.com/abusuraihsakhri/dicom-metadata-deid-agent.git
cd dicom-metadata-deid-agent
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api]"
```

For test and lint tools, use `python -m pip install -e ".[api,dev]"`.

## Inspect a local DICOM file

```bash
# Prints an allowlisted technical-metadata JSON report (does not modify input)
dicom-metadata-inspect scan example.dcm

# Writes a new JSON file; refuses to overwrite any existing output
dicom-metadata-inspect export example.dcm technical-metadata.json
```

This command operates locally and does **not** upload the file, export pixel data, preserve identifying metadata or create a de-identified DICOM file. Only DICOM Part 10 inputs are accepted; nonstandard/raw datasets are not coerced into acceptance.

## Use the legacy synthetic rule engine

The rule engine requires an audit key even in local mode:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# CLI demonstration (not a DICOM scan)
python cli.py audit --task-id TASK-001 --target SYNTH-001 --primary 12 --secondary 4

# Existing CSV batch mode, using synthetic identifiers only
python cli.py batch -i sample.csv -o results.csv

# Start the optional local REST API and web console
python cli.py serve --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** for the local rule-engine console, **/docs** for API schema and **/health** for a health check. The browser form sends synthetic rule metrics to the same-origin API. It does not upload or de-identify DICOM files, and it does not fabricate offline audit results.

`dicom-metadata-deid-engine` remains an alternative console entry point for the separately maintained `dicom_metadata_deid_agent` clinical-metric demonstration. `dicom_deid.py`, `enrichment.py`, and `agents/` retain their existing demonstration and utility interfaces.

## Privacy and security

- Run the inspector locally, avoid real patient data in the demo API, and review any output before sharing. Regex-based PHI blocking is heuristic and cannot guarantee HIPAA compliance or absence of PHI.
- The HMAC audit key must be provided through `AUDIT_SECRET_KEY`; there is no production fallback. Do not commit the key to the repository. Logs are held **in memory** and are not durable evidence after process termination.
- Docker Compose requires an explicit key and publishes the REST service on **127.0.0.1:8000** by default. The REST endpoints do not implement user authentication, so do not expose them on a public interface without suitable access control and a security review.
- The local web interface is served by FastAPI, not GitHub Pages. GitHub Pages cannot run the project's Python API, and no verified live GitHub Pages application is provided.

## Development and verification

```bash
python -m pip install -e ".[api,dev]"
python -m compileall -q agents dicom_metadata_deid_agent cli.py dicom_deid.py enrichment.py
ruff check --select E9,F63,F7,F82 .
python -m pytest -q
```

GitHub Actions runs the Python test suite on Python 3.10, 3.11, 3.12 and 3.13. Tests include synthetic DICOM metadata, audit-tampering regression cases, CSV parsing, API smoke tests and browser JavaScript syntax. Full automated cross-browser testing and a formal DICOM conformance assessment are not included.

For container use:

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

## Technology and license

Python, pydicom, Pydantic, optional FastAPI/Uvicorn and a dependency-light HTML/JavaScript UI. The repository is licensed under the [MIT License](LICENSE).
