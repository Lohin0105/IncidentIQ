import os

from .mock_memory import MockMemory
from .hindsight_memory import HindsightMemory


_memory = None


def get_memory():

    global _memory

    if _memory is not None:
        return _memory

    backend = os.getenv("MEMORY_BACKEND", "hindsight").lower()

    if backend == "mock":
        print("⚠️ Using local development memory.")
        _memory = MockMemory()
        return _memory

    api_key = os.getenv("HINDSIGHT_API_KEY")

    if not api_key:
        print("⚠️ Hindsight API key not configured.")
        print("⚠️ Using local development memory.")
        _memory = MockMemory()
        return _memory

    print("✓ Hindsight memory configured.")
    _memory = HindsightMemory()

    return _memory