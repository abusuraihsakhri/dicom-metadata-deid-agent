import os
import sys
from pathlib import Path

# Set audit key before importing agents that initialize GLOBAL_AUDIT
os.environ.setdefault("AUDIT_SECRET_KEY", "test-audit-key-not-for-production")
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dicom_deid import TagConfidentialityAuditorAgent, SyntheticUIDGeneratorAgent, BurnedInPixelPHIScannerAgent, DICOMDeIDCoordinator, main


def test_sub_agents():
    a1 = TagConfidentialityAuditorAgent()
    alerts1 = a1.evaluate({"metric_primary": 35.0})
    assert len(alerts1) == 1

    a2 = SyntheticUIDGeneratorAgent()
    alerts2 = a2.evaluate({"critical_flag": True})
    assert len(alerts2) == 1

    a3 = BurnedInPixelPHIScannerAgent()
    alerts3 = a3.evaluate({"status_text": "DISCORDANT_FINDING"})
    assert len(alerts3) == 1


def test_coordinator():
    coord = DICOMDeIDCoordinator()
    dossier = coord.audit_case({"case_id": "TEST-100", "metric_primary": 10.0, "metric_secondary": 2.0})
    assert dossier["overall_status"] == "CONCORDANT_NORMAL"
    assert dossier["total_alerts"] == 0

    ans = coord.query_assistant("What are the guidelines?")
    assert "guidelines" in ans or "standards" in ans


def test_cli():
    assert main(["audit", "--case-id", "CLI-01"]) == 0
    assert main(["chat", "What", "is", "the", "system", "status?"]) == 0


def test_domain_registry():
    from dicom_deid import DomainKnowledgeRegistry
    assert DomainKnowledgeRegistry.ZERO_PHI_COMPLIANCE is False
    assert "PRO" in DomainKnowledgeRegistry.SYSTEM_VERSION
