import json
from pathlib import Path

from ..memory import get_memory


DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "incidents.json"


class IncidentService:

    def __init__(self):
        self.memory = get_memory()
        self.incidents = self._load_incidents()

    def _load_incidents(self):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_all_incidents(self):
        return self.incidents

    def get_incident(self, incident_id: str):

        for incident in self.incidents:
            if incident["incident_id"] == incident_id:
                return incident

        return None

    def build_memory_text(self, incident):

        return (
            f"Incident {incident['incident_id']} occurred in "
            f"{incident['service']} in {incident['environment']}. "
            f"Error: {incident['error_message']}. "
            f"Description: {incident['description']}. "
            f"Root cause: {incident.get('root_cause', 'Unknown')}. "
            f"Resolution: {incident.get('resolution', 'Unknown')}. "
            f"Successful: {incident.get('successful', False)}."
        )

    def learn_from_incident(self, incident):

        content = self.build_memory_text(incident)

        return self.memory.retain(
            content=content,
            metadata={
                "incident_id": incident["incident_id"],
                "service": incident["service"],
                "environment": incident["environment"],
                "severity": incident["severity"],
                "type": "incident_resolution"
            }
        )

    def investigate(self, incident):
        query = (
            f"{incident['service']} "
            f"{incident['error_message']} "
            f"{incident['database'] or ''} "
            f"{incident['environment']}"
        )

        memories = self.memory.recall(query)

        recommendations = []
        successful_actions = []
        failed_actions = []

        for memory in memories[:10]:
            content = memory.get("content", "")
            content_lower = content.lower()

            # Identify learned troubleshooting outcomes
            if "outcome: success" in content_lower:
                successful_actions.append(content)

            elif "outcome: failed" in content_lower:
                failed_actions.append(content)

            # Also support incident-resolution memories
            if "connection pool" in content_lower:
                if "increase" in content_lower:
                    recommendations.append(
                        "Check database connection pool utilization "
                        "and compare it with the previously successful capacity adjustment."
                    )

        # Remove duplicate recommendations
        recommendations = list(dict.fromkeys(recommendations))

        if memories:
            recommendations.insert(
                0,
                "Historical engineering experience was found for this incident pattern."
            )

        if failed_actions:
            recommendations.append(
                "Avoid previously failed troubleshooting actions unless "
                "new evidence suggests the situation is different."
            )

        if successful_actions:
            recommendations.append(
                "Prioritize troubleshooting approaches that previously "
                "resolved a similar incident."
            )

        if not memories:
            recommendations = [
                "No relevant historical incident was found.",
                "Begin investigation with service logs and metrics.",
                "Check recent deployments and infrastructure changes."
            ]

        return {
            "incident": incident,
            "memory_found": len(memories),
            "memories": memories[:10],
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "recommendations": recommendations
        }
    def record_action(self, incident, action_data):

        result = action_data.result
        action = action_data.action
        reason = action_data.reason or "No reason provided."

        outcome_text = (
            f"During incident {incident['incident_id']} in "
            f"{incident['service']}, the engineer attempted: "
            f"{action}. "
            f"Outcome: {result}. "
            f"Reason: {reason}"
        )

        memory_result = self.memory.retain(
            content=outcome_text,
            metadata={
                "incident_id": incident["incident_id"],
                "service": incident["service"],
                "type": "troubleshooting_action",
                "result": result
            }
        )

        return {
            "incident_id": incident["incident_id"],
            "action": action,
            "result": result,
            "reason": reason,
            "learned": True,
            "memory": memory_result
        }

incident_service = IncidentService()