import json
import os
import re

from groq import Groq


class IncidentAgent:
    """
    LLM-powered incident response agent.

    The agent investigates a current incident using:
    1. Current incident evidence
    2. Historical engineering memory
    3. Successful and failed troubleshooting outcomes

    The agent is intentionally evidence-bounded:
    - It must not invent infrastructure components.
    - It must not introduce configuration settings that are absent
      from the supplied incident evidence or historical memory.
    - Unsupported infrastructure claims are removed during validation.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)
        self.model = "openai/gpt-oss-120b"

    # -------------------------------------------------------------
    # Evidence helpers
    # -------------------------------------------------------------

    @staticmethod
    def _build_evidence_text(incident: dict, memories: list) -> str:
        """
        Build a normalized text representation of all evidence.
        """

        parts = [
            json.dumps(incident, indent=2, default=str)
        ]

        for memory in memories:
            parts.append(
                memory.get("content", "")
            )

            parts.append(
                json.dumps(
                    memory.get("metadata", {}),
                    indent=2,
                    default=str
                )
            )

        return "\n".join(parts).lower()

    @staticmethod
    def _contains_concept(
        text: str,
        concept_patterns: list[str]
    ) -> bool:
        """
        Return True when at least one supplied concept pattern
        exists in the evidence text.
        """

        normalized = text.lower()

        return any(
            re.search(pattern, normalized)
            for pattern in concept_patterns
        )

    # -------------------------------------------------------------
    # Unsupported infrastructure protection
    # -------------------------------------------------------------

    def _sanitize_text(
        self,
        text: str,
        evidence_text: str
    ) -> str:
        """
        Remove or neutralize unsupported infrastructure claims.

        This provides a second layer of protection after the
        evidence-grounded LLM prompt.
        """

        if not text:
            return text

        sanitized = str(text)

        # ---------------------------------------------------------
        # PostgreSQL max_connections
        # ---------------------------------------------------------

        max_connections_patterns = [
            r"\bpostgres(?:ql)?\s+max[_\s-]?connections?\b",
            r"\bmax[_\s-]?connections?\b",
            r"\bpostgres(?:ql)?\s+connection\s+limit\b",
            r"\bpostgres(?:ql)?\s+server\s+connection\s+limit\b",
        ]

        has_max_connections_evidence = self._contains_concept(
            evidence_text,
            max_connections_patterns
        )

        if not has_max_connections_evidence:

            replacement_patterns = [
                r"PostgreSQL\s+max[_\s-]?connections",
                r"Postgres\s+max[_\s-]?connections",
                r"postgresql\s+max[_\s-]?connections",
                r"postgres\s+max[_\s-]?connections",
                r"max[_\s-]?connections",
                r"PostgreSQL\s+connection\s+limit",
                r"Postgres\s+connection\s+limit",
            ]

            for pattern in replacement_patterns:
                sanitized = re.sub(
                    pattern,
                    "unsupported database-server setting",
                    sanitized,
                    flags=re.IGNORECASE
                )

        # ---------------------------------------------------------
        # Other unsupported infrastructure settings
        # ---------------------------------------------------------

        protected_concepts = {
            "redis maxmemory": [
                r"\bredis\s+maxmemory\b",
                r"\bmaxmemory\b",
            ],
            "kubernetes cpu limits": [
                r"\bkubernetes\s+cpu\s+limits?\b",
                r"\bk8s\s+cpu\s+limits?\b",
            ],
            "kubernetes memory limits": [
                r"\bkubernetes\s+memory\s+limits?\b",
                r"\bk8s\s+memory\s+limits?\b",
            ],
            "nginx worker connections": [
                r"\bnginx\s+worker[_\s-]?connections?\b",
            ],
        }

        for _, patterns in protected_concepts.items():

            if not self._contains_concept(
                evidence_text,
                patterns
            ):

                for pattern in patterns:
                    sanitized = re.sub(
                        pattern,
                        "unsupported infrastructure setting",
                        sanitized,
                        flags=re.IGNORECASE
                    )

        return sanitized

    def _sanitize_result(
        self,
        result: dict,
        evidence_text: str
    ) -> dict:
        """
        Validate every user-visible LLM field.

        This ensures unsupported infrastructure claims cannot
        reach the frontend even if the model ignores the prompt.
        """

        string_fields = [
            "summary",
            "likely_root_cause",
            "reasoning",
        ]

        for field in string_fields:
            if isinstance(result.get(field), str):
                result[field] = self._sanitize_text(
                    result[field],
                    evidence_text
                )

        list_fields = [
            "historical_evidence",
            "recommended_actions",
            "warnings",
        ]

        for field in list_fields:

            values = result.get(field, [])

            if not isinstance(values, list):
                values = [str(values)]

            sanitized_values = []

            for value in values:

                if not isinstance(value, str):
                    value = str(value)

                value = self._sanitize_text(
                    value,
                    evidence_text
                )

                sanitized_values.append(value)

            result[field] = sanitized_values

        return result

    # -------------------------------------------------------------
    # Main investigation
    # -------------------------------------------------------------

    def investigate(
        self,
        incident: dict,
        memories: list
    ):

        # ---------------------------------------------------------
        # Prepare historical memory for the LLM
        # ---------------------------------------------------------

        if memories:

            memory_sections = []

            for index, memory in enumerate(
                memories,
                start=1
            ):

                content = memory.get(
                    "content",
                    ""
                )

                metadata = memory.get(
                    "metadata",
                    {}
                )

                memory_sections.append(
                    f"""
Memory {index}

Content:
{content}

Metadata:
{json.dumps(metadata, indent=2, default=str)}
""".strip()
                )

            memory_text = "\n\n".join(
                memory_sections
            )

        else:

            memory_text = (
                "No historical engineering memory was found."
            )

        # ---------------------------------------------------------
        # Separate successful and failed experience
        # ---------------------------------------------------------

        successful_memories = []
        failed_memories = []

        for memory in memories:

            content = memory.get(
                "content",
                ""
            )

            metadata = memory.get(
                "metadata",
                {}
            )

            result = str(
                metadata.get(
                    "result",
                    ""
                )
            ).lower()

            content_lower = content.lower()

            if (
                result == "success"
                or "outcome: success" in content_lower
            ):

                successful_memories.append(
                    content
                )

            elif (
                result == "failed"
                or "outcome: failed" in content_lower
            ):

                failed_memories.append(
                    content
                )

        successful_text = (
            "\n".join(
                f"- {item}"
                for item in successful_memories
            )
            if successful_memories
            else (
                "No explicitly successful historical "
                "actions were found."
            )
        )

        failed_text = (
            "\n".join(
                f"- {item}"
                for item in failed_memories
            )
            if failed_memories
            else (
                "No explicitly failed historical "
                "actions were found."
            )
        )

        # ---------------------------------------------------------
        # Build evidence boundary
        # ---------------------------------------------------------

        evidence_text = self._build_evidence_text(
            incident,
            memories
        )

        # ---------------------------------------------------------
        # Evidence-grounded prompt
        # ---------------------------------------------------------

        prompt = f"""
You are IncidentIQ, an AI production incident response engineer.

Your job is to investigate a production incident using ONLY:

1. CURRENT INCIDENT EVIDENCE
2. HISTORICAL ENGINEERING MEMORY
3. SUCCESSFUL HISTORICAL ACTIONS
4. FAILED HISTORICAL ACTIONS

IncidentIQ's central capability is learning from previous
engineering outcomes.

==================================================
STRICT EVIDENCE BOUNDARY
==================================================

You are NOT allowed to introduce a technical component,
configuration setting, infrastructure limit, metric, numeric value,
or system behavior unless it is supported by the supplied evidence.

The supplied evidence is the ONLY source of technical facts.

If a technical concept does not appear in the current incident
or historical memory, do not introduce it.

Do not fill missing information using general infrastructure
knowledge.

If something is unknown, say that it is unknown.

==================================================
CONNECTION POOL DISTINCTION
==================================================

The incident may contain an APPLICATION DATABASE CONNECTION POOL.

For example:

50 -> 120 -> 160

This refers to the application's connection-pool configuration.

Do NOT automatically interpret this as a PostgreSQL server
configuration.

Specifically:

- Application connection pool != PostgreSQL server max_connections.
- Application pool size != database server connection limit.
- A successful application pool adjustment does NOT prove that
  PostgreSQL max_connections is the problem.
- Do NOT mention PostgreSQL max_connections unless the exact
  concept is explicitly present in the supplied evidence.
- Do NOT recommend changing PostgreSQL max_connections unless
  the supplied evidence explicitly supports that recommendation.

==================================================
GENERAL RULES
==================================================

1. Do NOT invent facts.

2. Do NOT invent infrastructure components.

3. Do NOT invent configuration settings.

4. Do NOT invent metrics.

5. Do NOT invent numeric values.

6. Do NOT claim that a component is the root cause unless the
   evidence supports it.

7. Clearly distinguish:
   - current incident evidence
   - historical evidence
   - inference

8. Historical incidents are evidence, not proof that the current
   incident has exactly the same root cause.

9. Prefer troubleshooting actions that previously succeeded when
   the current incident has the same or closely related symptoms.

10. Warn about historical actions that failed when they are
    relevant.

11. Do not recommend an action simply because it sounds technically
    reasonable.

12. Every recommendation must be connected to evidence.

13. Every warning must be connected to evidence or explicitly
    stated uncertainty.

14. If evidence is insufficient, say so.

15. Give practical investigation steps an engineer could actually
    perform.

16. Keep reasoning concise and technically precise.

17. Never introduce unrelated infrastructure settings.

18. Never turn an inference into a confirmed fact.

==================================================
CURRENT INCIDENT
==================================================

{json.dumps(incident, indent=2, default=str)}

==================================================
HISTORICAL ENGINEERING MEMORY
==================================================

{memory_text}

==================================================
HISTORICALLY SUCCESSFUL ACTIONS
==================================================

{successful_text}

==================================================
HISTORICALLY FAILED ACTIONS
==================================================

{failed_text}

==================================================
FINAL VALIDATION BEFORE ANSWERING
==================================================

Before returning JSON, verify every statement.

For every recommendation ask:

"Which supplied evidence supports this?"

For every warning ask:

"Which supplied evidence supports this?"

For every infrastructure setting ask:

"Was this setting explicitly present in the supplied evidence?"

If the answer is no, REMOVE the statement.

Do not introduce PostgreSQL max_connections unless it explicitly
appears in the supplied evidence.

Do not introduce unrelated infrastructure configuration.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY a valid JSON object with exactly these fields:

{{
  "summary": "Short explanation of what appears to be happening.",
  "likely_root_cause": "Most likely cause based only on available evidence. Clearly state if this is uncertain.",
  "confidence": "high, medium, or low",
  "historical_evidence": [
    "Relevant historical lesson 1",
    "Relevant historical lesson 2"
  ],
  "recommended_actions": [
    "Concrete evidence-based action 1",
    "Concrete evidence-based action 2"
  ],
  "warnings": [
    "Relevant warning based on failed historical actions or uncertainty"
  ],
  "reasoning": "Explain how the current evidence and historical experience led to these recommendations."
}}

The confidence value MUST be exactly one of:

"high"

"medium"

"low"
"""

        # ---------------------------------------------------------
        # Ask Groq
        # ---------------------------------------------------------

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful production incident "
                        "response engineer. "
                        "Return valid JSON only. "
                        "Use only supplied evidence. "
                        "Never invent infrastructure facts, "
                        "settings, limits, metrics, or components."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()

        # ---------------------------------------------------------
        # Parse JSON safely
        # ---------------------------------------------------------

        try:

            # Handle Markdown code fences.
            if content.startswith("```"):

                content = re.sub(
                    r"^```(?:json)?\s*",
                    "",
                    content,
                    flags=re.IGNORECASE
                )

                content = re.sub(
                    r"\s*```$",
                    "",
                    content
                )

                content = content.strip()

            result = json.loads(content)

            # -----------------------------------------------------
            # Normalize confidence
            # -----------------------------------------------------

            confidence = str(
                result.get(
                    "confidence",
                    "low"
                )
            ).lower().strip()

            if confidence not in {
                "high",
                "medium",
                "low",
            }:

                confidence = "low"

            # -----------------------------------------------------
            # Ensure expected fields exist
            # -----------------------------------------------------

            normalized_result = {
                "summary": result.get(
                    "summary",
                    ""
                ),

                "likely_root_cause": result.get(
                    "likely_root_cause",
                    "Unable to determine from available evidence."
                ),

                "confidence": confidence,

                "historical_evidence": result.get(
                    "historical_evidence",
                    []
                ),

                "recommended_actions": result.get(
                    "recommended_actions",
                    []
                ),

                "warnings": result.get(
                    "warnings",
                    []
                ),

                "reasoning": result.get(
                    "reasoning",
                    ""
                ),
            }

            # -----------------------------------------------------
            # Final evidence-boundary validation
            # -----------------------------------------------------

            normalized_result = self._sanitize_result(
                normalized_result,
                evidence_text
            )

            # -----------------------------------------------------
            # Safety fallback
            # -----------------------------------------------------

            if not isinstance(
                normalized_result["historical_evidence"],
                list
            ):

                normalized_result["historical_evidence"] = []

            if not isinstance(
                normalized_result["recommended_actions"],
                list
            ):

                normalized_result["recommended_actions"] = []

            if not isinstance(
                normalized_result["warnings"],
                list
            ):

                normalized_result["warnings"] = []

            return normalized_result

        except json.JSONDecodeError:

            return {
                "summary": content,

                "likely_root_cause": (
                    "Unable to determine because the LLM "
                    "response was not valid JSON."
                ),

                "confidence": "low",

                "historical_evidence": [],

                "recommended_actions": [],

                "warnings": [
                    (
                        "The AI response could not be parsed "
                        "into the expected structured format."
                    )
                ],

                "reasoning": (
                    "The LLM returned a response that was "
                    "not valid JSON."
                ),
            }