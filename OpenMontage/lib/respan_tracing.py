"""Respan tracing for model calls made through the OpenAI / Google GenAI SDKs.

Tracing is opt-in. Nothing is initialised until RESPAN_API_KEY is set, so local
runs, CI and the zero-key pipelines behave exactly as they did before.

``init_respan()`` is called once at startup (tool discovery, before any tool
imports an LLM SDK). The ``Respan`` constructor reads RESPAN_API_KEY — and the
optional RESPAN_BASE_URL — from the environment and auto-instruments the
installed SDKs; it never reroutes a call to another gateway.
"""

from __future__ import annotations

import atexit
import os
from typing import Any, Optional

_respan: Optional[Any] = None


def init_respan(app_name: str = "openmontage") -> Optional[Any]:
    """Start Respan tracing once and return the client, or None when it is off."""
    global _respan
    if _respan is not None:
        return _respan
    if not os.environ.get("RESPAN_API_KEY"):
        return None

    from respan import Respan

    _respan = Respan(app_name=app_name)
    atexit.register(shutdown)
    return _respan


def shutdown() -> None:
    """Flush pending spans and stop tracing (registered to run at exit)."""
    global _respan
    if _respan is None:
        return
    respan, _respan = _respan, None
    respan.shutdown()
