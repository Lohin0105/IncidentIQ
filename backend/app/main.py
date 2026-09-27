import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models.action import IncidentAction
from .memory import get_memory
from .services.incident_service import incident_service
from .agents.incident_agent import IncidentAgent



app = FastAPI(
    title="IncidentIQ",
    description="Memory-powered AI incident response agent",
    version="0.1.0"
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
memory = get_memory()
agent = IncidentAgent()


@app.get("/")
def root():

    return {
        "name": "IncidentIQ",
        "status": "running",
        "message": "Memory-powered incident response agent"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


@app.get("/api/incidents")
def get_incidents():

    return {
        "count": len(incident_service.get_all_incidents()),
        "incidents": incident_service.get_all_incidents()
    }


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):

    incident = incident_service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident


@app.post("/api/incidents/{incident_id}/learn")
def learn_incident(incident_id: str):

    incident = incident_service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    result = incident_service.learn_from_incident(incident)

    return {
        "message": "Incident learned successfully",
        "incident_id": incident_id,
        "memory": result
    }


@app.post("/api/incidents/{incident_id}/investigate")
def investigate_incident(incident_id: str):

    incident = incident_service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    result = incident_service.investigate(incident)

    return result


@app.post("/memory/test")
def test_memory():

    memory.retain(
        content=(
            "Incident INC-1042 occurred in payment-service. "
            "The root cause was PostgreSQL connection pool exhaustion. "
            "Increasing the connection pool from 50 to 120 successfully "
            "resolved the incident."
        ),
        metadata={
            "incident_id": "INC-1042",
            "service": "payment-service",
            "type": "resolution"
        }
    )

    results = memory.recall(
        "payment-service ConnectionPoolTimeout PostgreSQL"
    )

    return {
        "memory_count": len(results),
        "results": results
    }
@app.post("/api/incidents/{incident_id}/actions")
def record_incident_action(
    incident_id: str,
    action_data: IncidentAction
):

    incident = incident_service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident_service.record_action(
        incident,
        action_data
    )
@app.post("/api/incidents/{incident_id}/agent-investigate")
def agent_investigate_incident(incident_id: str):
    incident = incident_service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    # Retrieve historical engineering experience
    query = (
        f"{incident['service']} "
        f"{incident['error_message']} "
        f"{incident['database'] or ''} "
        f"{incident['environment']}"
    )

    memories = incident_service.memory.recall(query)

    # Let the LLM reason over the incident + memory
    diagnosis = agent.investigate(
        incident=incident,
        memories=memories
    )

    return {
        "incident": incident,
        "memory_count": len(memories),
        "memories": memories[:10],
        "agent": diagnosis
    }