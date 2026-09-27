import os

from hindsight_client import Hindsight


class HindsightMemory:

    def __init__(self):

        self.api_url = os.getenv(
            "HINDSIGHT_API_URL",
            "https://api.hindsight.vectorize.io"
        )

        self.api_key = os.getenv("HINDSIGHT_API_KEY")

        self.bank_id = os.getenv(
            "HINDSIGHT_BANK_ID",
            "incidentiq-engineering"
        )

        self.client = Hindsight(
            base_url=self.api_url,
            api_key=self.api_key
        )

    def retain(
        self,
        content: str,
        metadata: dict | None = None
    ):

        return self.client.retain(
            bank_id=self.bank_id,
            content=content,
            metadata=metadata or {}
        )

    def recall(self, query: str):

        response = self.client.recall(
            bank_id=self.bank_id,
            query=query
        )

        # Hindsight SDK 0.10.x returns a RecallResponse
        # containing typed RecallResult objects.
        results = getattr(response, "results", [])

        normalized = []

        for item in results:

            # Convert Pydantic RecallResult to a normal dict
            if hasattr(item, "model_dump"):
                data = item.model_dump()

            elif isinstance(item, dict):
                data = item

            else:
                data = {
                    "text": str(item)
                }

            content = (
                data.get("text")
                or data.get("content")
                or ""
            )

            metadata = data.get(
                "metadata",
                {}
            )

            if not isinstance(metadata, dict):
                metadata = {}

            normalized.append(
                {
                    "content": content,
                    "metadata": metadata,
                    "type": data.get("type")
                }
            )

        return normalized

    def reflect(self, query: str):

        return self.client.reflect(
            bank_id=self.bank_id,
            query=query
        )