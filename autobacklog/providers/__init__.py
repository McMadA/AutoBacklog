"""
AI Providers Package
"""

from typing import Optional

from autobacklog.providers.agy import AntigravityProvider
from autobacklog.providers.base import BaseAIProvider
from autobacklog.providers.claude import ClaudeProvider


def get_ai_provider(provider_type: Optional[str] = "auto") -> BaseAIProvider:
    ptype = (provider_type or "auto").lower()

    if ptype == "agy":
        return AntigravityProvider()
    elif ptype == "claude":
        return ClaudeProvider()
    elif ptype == "auto":
        # Check available executables on PATH
        agy = AntigravityProvider()
        if agy.find_executable():
            return agy
        claude = ClaudeProvider()
        if claude.find_executable():
            return claude
        # Default fallback
        return agy
    else:
        raise ValueError(
            f"Onbekend provider type: '{provider_type}'. Kies uit 'auto', 'agy', of 'claude'."
        )


__all__ = [
    "BaseAIProvider",
    "AntigravityProvider",
    "ClaudeProvider",
    "get_ai_provider",
]
