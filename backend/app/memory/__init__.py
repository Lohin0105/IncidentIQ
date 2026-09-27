import os

from .mock_memory import MockMemory
from .hindsight_memory import HindsightMemory


_memory = None


def get_memory():
    global _memory

    if _memory is not None:
        return _memory

    # Default to MockMemory for local development.
    # Hindsight is enabled only when explicitly configured.
    backend = os.getenv("MEMORY_BACKEND", "mock").lower().strip()

    if backend == "mock":
        print("Using local MockMemory.")
        _memory = MockMemory()
        return _memory

    if backend == "hindsight":
        api_key = os.getenv("HINDSIGHT_API_KEY")

        if not api_key:
            print("Hindsight API key not configured.")
            print("Falling back to local MockMemory.")
            _memory = MockMemory()
            return _memory

        print("Hindsight memory configured.")
        _memory = HindsightMemory()
        return _memory

    # Unknown MEMORY_BACKEND value → safely use MockMemory
    print(f"Unknown MEMORY_BACKEND='{backend}'.")
    print("Falling back to local MockMemory.")
    _memory = MockMemory()
    return _memory