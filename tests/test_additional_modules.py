"""
Additional tests for dicom-metadata-deid-agent modules.
Covers: dicom_metadata_deid_agent package, metrics, llm_factory, learning engine.
"""
import os
import sys
from pathlib import Path

# Set audit key before importing agents that initialize GLOBAL_AUDIT
os.environ.setdefault("AUDIT_SECRET_KEY", "test-audit-key-not-for-production")
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.metrics import SystemMetricsCollector, GLOBAL_METRICS
from agents.llm_factory import LLMFactory, MockLLM
from agents.learning import ActiveLearningEngine, GLOBAL_LEARNING_ENGINE
from agents.base import PHIGuard, SecurityException


class TestPHIGuardRedaction:
    """Test PHI redaction functionality."""

    def test_redact_phi_ssn(self):
        text = "Patient SSN: 123-45-6789"
        redacted = PHIGuard.redact_phi(text)
        assert "123-45-6789" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted

    def test_redact_phi_email(self):
        text = "Contact: john.doe@hospital.org"
        redacted = PHIGuard.redact_phi(text)
        assert "john.doe@hospital.org" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted

    def test_redact_phi_phone(self):
        text = "Phone: (555) 123-4567"
        redacted = PHIGuard.redact_phi(text)
        assert "555" not in redacted or "[REDACTED_IDENTIFIER]" in redacted

    def test_redact_phi_mrn(self):
        text = "MRN-12345678"
        redacted = PHIGuard.redact_phi(text)
        assert "12345678" not in redacted

    def test_clean_text_unchanged(self):
        text = "Sample KEY-001 nominal parameters"
        assert PHIGuard.redact_phi(text) == text


class TestMetricsCollector:
    """Test Prometheus metrics collection."""

    def test_initial_state(self):
        collector = SystemMetricsCollector()
        assert collector.tasks_total == 0
        assert collector.critical_alerts_total == 0
        assert collector.phi_blocks_total == 0

    def test_record_task_critical(self):
        collector = SystemMetricsCollector()
        collector.record_task("CRITICAL_STAT_PANIC", 0.05)
        assert collector.tasks_total == 1
        assert collector.critical_alerts_total == 1
        assert collector.audit_blocks_total == 1

    def test_record_task_elevated(self):
        collector = SystemMetricsCollector()
        collector.record_task("ELEVATED_RISK", 0.03)
        assert collector.tasks_total == 1
        assert collector.elevated_alerts_total == 1

    def test_record_task_routine(self):
        collector = SystemMetricsCollector()
        collector.record_task("ROUTINE", 0.01)
        assert collector.tasks_total == 1
        assert collector.routine_tasks_total == 1

    def test_record_phi_block(self):
        collector = SystemMetricsCollector()
        collector.record_phi_block()
        assert collector.phi_blocks_total == 1

    def test_prometheus_export(self):
        collector = SystemMetricsCollector()
        collector.record_task("CRITICAL_STAT_PANIC", 0.05)
        collector.record_phi_block()
        output = collector.export_prometheus_text()
        assert "system_tasks_total" in output
        assert "alerts_triggered_total" in output
        assert "phi_outbound_blocks_total" in output
        assert "audit_chain_blocks_total" in output
        assert 'system="dicom-metadata-deid-agent"' in output


class TestLLMFactory:
    """Test LLM factory and mock provider."""

    def test_mock_llm_creation(self):
        llm = LLMFactory.create("mock")
        assert isinstance(llm, MockLLM)

    def test_mock_llm_response(self):
        llm = LLMFactory.create("mock")
        response = llm.invoke("Test query about specimen parameters")
        assert "Deterministic Verification Engine" in response
        assert "No clinical or DICOM conformance verification" in response

    def test_mock_llm_phi_blocking(self):
        llm = LLMFactory.create("mock")
        with pytest.raises(SecurityException):
            llm.invoke("Patient John Doe MRN-12345")

    def test_factory_various_providers(self):
        for provider in ["mock", "ollama", "claude", "openai", "unknown"]:
            llm = LLMFactory.create(provider)
            assert isinstance(llm, MockLLM)

    def test_factory_custom_system_name(self):
        llm = LLMFactory.create("mock", system_name="Custom System")
        response = llm.invoke("Test")
        assert "Custom System" in response


class TestActiveLearningEngine:
    """Test Bayesian calibration and active learning."""

    def test_initial_weights(self):
        engine = ActiveLearningEngine()
        weights = engine.get_calibrated_weights()
        assert "InvariantQCWorker" in weights
        assert "SafetyEscalationWorker" in weights
        assert "ProtocolConformanceWorker" in weights
        assert all(w == 1.0 for w in weights.values())

    def test_record_concordant_feedback(self):
        engine = ActiveLearningEngine()
        engine.record_feedback("InvariantQCWorker", was_concordant=True, confidence_score=0.9)
        weights = engine.get_calibrated_weights()
        assert weights["InvariantQCWorker"] > 1.0

    def test_record_discordant_feedback(self):
        engine = ActiveLearningEngine()
        engine.record_feedback("InvariantQCWorker", was_concordant=False, confidence_score=0.1)
        weights = engine.get_calibrated_weights()
        assert weights["InvariantQCWorker"] < 1.0

    def test_uncertainty_buffer(self):
        engine = ActiveLearningEngine()
        engine.record_feedback("InvariantQCWorker", was_concordant=True, confidence_score=0.55)
        engine.record_feedback("InvariantQCWorker", was_concordant=False, confidence_score=0.50)
        assert len(engine.uncertainty_buffer) == 2

    def test_weight_bounds(self):
        engine = ActiveLearningEngine()
        # Record many discordant to push weight down
        for _ in range(20):
            engine.record_feedback("InvariantQCWorker", was_concordant=False, confidence_score=0.1)
        weights = engine.get_calibrated_weights()
        assert weights["InvariantQCWorker"] >= 0.2  # minimum bound

    def test_unknown_worker_handling(self):
        engine = ActiveLearningEngine()
        engine.record_feedback("UnknownWorker", was_concordant=True, confidence_score=0.8)
        weights = engine.get_calibrated_weights()
        assert "UnknownWorker" in weights


class TestDICOMMetadataDeidAgentPackage:
    """Test the dicom_metadata_deid_agent package modules."""

    def test_models_payload_creation(self):
        from dicom_metadata_deid_agent.models import ClinicalCasePayload, UrgencyLevel, ClinicalIntegrityStatus
        case = ClinicalCasePayload(
            case_id="TEST-001",
            patient_synthetic_id="SYNTH-001",
            primary_metric=15.0,
            secondary_metric=5.0,
            status_flag="NORMAL",
            is_stat=False,
        )
        assert case.case_id == "TEST-001"
        assert case.primary_metric == 15.0

    def test_models_alert_creation(self):
        from dicom_metadata_deid_agent.models import AgentAlert, UrgencyLevel
        alert = AgentAlert(
            alert_id="ALERT-001",
            sub_agent="TestAgent",
            urgency=UrgencyLevel.WARNING,
            title="Test Alert",
            clinical_finding="Test finding",
            actionable_recommendation="Test recommendation",
        )
        d = alert.to_dict()
        assert d["alert_id"] == "ALERT-001"
        assert d["urgency"] == "WARNING"

    def test_engine_primary_index(self):
        from dicom_metadata_deid_agent.engine import ClinicalDomainEngine
        result = ClinicalDomainEngine.evaluate_primary_index(25.0)
        assert result is not None
        assert "exceeds" in result["finding"]

    def test_engine_primary_index_normal(self):
        from dicom_metadata_deid_agent.engine import ClinicalDomainEngine
        result = ClinicalDomainEngine.evaluate_primary_index(15.0)
        assert result is None

    def test_engine_secondary_kinetics(self):
        from dicom_metadata_deid_agent.engine import ClinicalDomainEngine
        result = ClinicalDomainEngine.evaluate_secondary_kinetics(15.0, is_stat=True)
        assert result is not None
        assert "STAT" in result["finding"]

    def test_engine_biomarker_concordance(self):
        from dicom_metadata_deid_agent.engine import ClinicalDomainEngine
        result = ClinicalDomainEngine.evaluate_biomarker_concordance("DISCORDANT", {})
        assert result is not None
        assert "Discordance" in result["title"]

    def test_coordinator_process_case(self):
        from dicom_metadata_deid_agent.agents import DICOMDeIDCoordinator
        from dicom_metadata_deid_agent.models import ClinicalCasePayload
        coord = DICOMDeIDCoordinator()
        case = ClinicalCasePayload(
            case_id="COORD-001",
            patient_synthetic_id="SYNTH-001",
            primary_metric=10.0,
            secondary_metric=3.0,
            status_flag="NORMAL",
            is_stat=False,
        )
        dossier = coord.process_case(case)
        assert dossier["case_id"] == "COORD-001"
        assert dossier["overall_status"] == "CONCORDANT_NORMAL"

    def test_coordinator_critical_case(self):
        from dicom_metadata_deid_agent.agents import DICOMDeIDCoordinator
        from dicom_metadata_deid_agent.models import ClinicalCasePayload
        coord = DICOMDeIDCoordinator()
        case = ClinicalCasePayload(
            case_id="COORD-002",
            patient_synthetic_id="SYNTH-002",
            primary_metric=30.0,
            secondary_metric=15.0,
            status_flag="DISCORDANT",
            is_stat=True,
        )
        dossier = coord.process_case(case)
        assert dossier["overall_status"] == "CRITICAL_ACTION_REQUIRED"
        assert dossier["total_alerts"] > 0

    def test_coordinator_chat(self):
        from dicom_metadata_deid_agent.agents import DICOMDeIDCoordinator
        coord = DICOMDeIDCoordinator()
        response = coord.query_supervisory_chat("What is the status?")
        assert "tracking" in response or "online" in response

    def test_sub_agents(self):
        from dicom_metadata_deid_agent.agents import (
            TagConfidentialityAuditorAgent,
            SyntheticUIDGeneratorAgent,
            BurnedInPixelPHIScannerAgent,
        )
        from dicom_metadata_deid_agent.models import ClinicalCasePayload

        case = ClinicalCasePayload(
            case_id="AGENT-001",
            patient_synthetic_id="SYNTH-001",
            primary_metric=25.0,
            secondary_metric=5.0,
            status_flag="NORMAL",
            is_stat=False,
        )

        a1 = TagConfidentialityAuditorAgent()
        alerts1 = a1.audit(case)
        assert len(alerts1) == 1

        a2 = SyntheticUIDGeneratorAgent()
        alerts2 = a2.audit(case)
        assert len(alerts2) == 0  # secondary_metric=5.0 < 10.0, is_stat=False

        a3 = BurnedInPixelPHIScannerAgent()
        alerts3 = a3.audit(case)
        assert len(alerts3) == 0  # status_flag="NORMAL"
