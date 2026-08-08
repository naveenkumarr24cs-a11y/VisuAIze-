"""
VisuAIze - Step Generator
Thin wrapper that delegates to ai_provider.py.
This file is kept for backwards compatibility.
"""

from ai_provider import generate_steps  # noqa: F401

# Re-export so main.py doesn't need changes
__all__ = ["generate_steps"]
