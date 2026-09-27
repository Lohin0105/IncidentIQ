import json
from pathlib import Path
from typing import List, Dict


class MockMemory:
    """
    Persistent local development memory backend.

    Memories are stored in:
        backend/data/memory.json

    This allows IncidentIQ to retain engineering experiences
    even when the FastAPI/Uvicorn server is restarted.

    This is still a local development memory backend.
    It is NOT Hindsight Cloud.
    """

    def __init__(self):
        # backend/app/memory/mock_memory.py
        # parents[0] = memory
        # parents[1] = app
        # parents[2] = backend
        self.backend_dir = Path(__file__).resolve().parents[2]

        self.memory_file = (
            self.backend_dir
            / "data"
            / "memory.json"
        )

        self.memories: List[Dict] = []

        self._load()

    # ---------------------------------------------------------
    # Load persisted memories
    # ---------------------------------------------------------

    def _load(self):
        """
        Load previously saved memories from memory.json.
        """

        try:
            if not self.memory_file.exists():
                self.memories = []
                return

            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            if isinstance(data, list):
                self.memories = data
            else:
                self.memories = []

        except (json.JSONDecodeError, OSError):
            # If the file is corrupted or unreadable,
            # start with empty development memory.
            self.memories = []

    # ---------------------------------------------------------
    # Save memories to disk
    # ---------------------------------------------------------

    def _save(self):
        """
        Persist all memories to memory.json.
        """

        try:
            self.memory_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                self.memory_file,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    self.memories,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

        except OSError as error:
            print(
                f"⚠️ Could not save local memory: {error}"
            )

    # ---------------------------------------------------------
    # Retain memory
    # ---------------------------------------------------------

    def retain(
        self,
        content: str,
        metadata: dict | None = None
    ):
        """
        Store a new engineering experience.

        Duplicate memories are ignored so accidentally clicking
        the save button multiple times does not create duplicates.
        """

        memory = {
            "content": content,
            "metadata": metadata or {}
        }

        # Prevent exact duplicate memories.
        for existing_memory in self.memories:

            if (
                existing_memory.get("content") == content
                and existing_memory.get("metadata", {}) == (
                    metadata or {}
                )
            ):
                return existing_memory

        self.memories.append(memory)

        self._save()

        return memory

    # ---------------------------------------------------------
    # Recall memories
    # ---------------------------------------------------------

    def recall(
        self,
        query: str
    ) -> List[Dict]:
        """
        Recall relevant memories using simple keyword matching.

        Results are ranked by the number of matching words.
        """

        query_words = set(
            query.lower().split()
        )

        results = []

        for memory in self.memories:

            content = memory.get(
                "content",
                ""
            ).lower()

            score = sum(
                1
                for word in query_words
                if len(word) > 3
                and word in content
            )

            if score > 0:

                results.append(
                    {
                        **memory,
                        "score": score
                    }
                )

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results[:5]