"""
FastAPI REST API Server for Dicom Metadata Deid Agent.
"""
from typing import Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Dicom Metadata Deid Agent API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


@app.exception_handler(SecurityException)
async def on_rejected_identifier(request: Request, exc: SecurityException):
    # Never echo potentially identifying input in an HTTP response.
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": "Possible identifier detected; request rejected."})


@app.get("/", include_in_schema=False)
def index():
    """Serve the local console from a source checkout or Docker image."""
    path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Web console not installed.")
    return FileResponse(path)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "dicom-metadata-deid-agent", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
