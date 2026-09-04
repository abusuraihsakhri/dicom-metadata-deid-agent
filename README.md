# Dicom Metadata Deid Agent

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Dicom Metadata Deid Agent** is an advanced analytical and computational platform implementing DICOM PS 3.15 Header De-Identification & Synthetic UID Generator. It provides multi-agent consensus evaluation, PHI outbound protection, and tamper-evident audit logging.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`Severity`** — dedicated module for severity evaluation and state verification.
- **`DomainKnowledgeRegistry`**: Enterprise domain rules, guideline matrices, and evidence benchmarks.
- **`AgentAlert`** — dedicated module for agent alert evaluation and state verification.
- **`TagConfidentialityAuditorAgent`**: Specialized Sub-Agent 1 for dicom-metadata-deid-agent
- **`SyntheticUIDGeneratorAgent`**: Specialized Sub-Agent 2 for dicom-metadata-deid-agent
- **`BurnedInPixelPHIScannerAgent`**: Specialized Sub-Agent 3 for dicom-metadata-deid-agent

### 🏗️ Architecture

The project contains two parallel implementations:

1. **`agents/` package** — Enterprise supervisor orchestration with worker-based evaluation
2. **`dicom_metadata_deid_agent/` package** — Clinical domain engine with DICOM PS 3.15 de-identification profile

---

## 💻 CLI Quickstart & Usage

### Installation

```bash
pip install -e .
```

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --task-id <value> --target <value> --primary <value> --secondary <value>
```

### Parameter Reference
- `--task-id`: Specifies input measurement or parameter value.
- `--target`: Specifies input measurement or parameter value.
- `--primary`: Specifies input measurement or parameter value.
- `--secondary`: Specifies input measurement or parameter value.
- `--critical`: Specifies input measurement or parameter value.
- `--status`: Specifies input measurement or parameter value.
- `--input`: Specifies input measurement or parameter value.
- `--output`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Configuration

The audit trail requires a secret key to be configured via environment variable:

```bash
export AUDIT_SECRET_KEY="your-secure-random-key-here"
```

**Never use hardcoded secrets in production.** The application will raise a `SecurityException` if the key is not set.

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t dicom-metadata-deid-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY="your-secure-key" dicom-metadata-deid-agent
```

Or using Docker Compose:

```bash
AUDIT_SECRET_KEY="your-secure-key" docker-compose up
```

---

## 📁 Project Structure

```
dicom-metadata-deid-agent/
├── agents/                          # Enterprise supervisor package
│   ├── __init__.py
│   ├── api.py                       # FastAPI REST endpoints
│   ├── base.py                      # PHI guard, audit trail, security
│   ├── learning.py                  # Bayesian calibration engine
│   ├── llm_factory.py               # LLM provider abstraction
│   ├── metrics.py                   # Prometheus metrics collector
│   ├── models.py                    # Pydantic schemas
│   ├── streamer.py                  # WebSocket telemetry
│   ├── supervisor.py                # Master orchestrator
│   └── workers.py                   # Specialized evaluation workers
├── dicom_metadata_deid_agent/        # Clinical domain package
│   ├── __init__.py
│   ├── agents.py                    # DICOM-specific sub-agents
│   ├── cli.py                       # Clinical CLI
│   ├── engine.py                    # Clinical domain rules
│   ├── models.py                    # Clinical data models
│   └── server.py                    # Clinical FastAPI server
├── tests/                           # Test suite
│   ├── test_dicom_metadata_deid_agent.py
│   ├── test_enrichment.py
│   └── test_additional_modules.py
├── web/                             # Operations console UI
├── cli.py                           # Main CLI entry point
├── dicom_deid.py                    # Standalone DICOM de-identification
├── enrichment.py                    # Feature enrichment engines
├── simulator.py                     # Load testing simulator
├── pyproject.toml                   # Project configuration
├── Dockerfile                       # Container build
└── docker-compose.yml               # Container orchestration
```
