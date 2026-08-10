"""Shared exception types with no natural home in one package."""

from __future__ import annotations


class ComingSoonError(Exception):
    """Raised by an extension point (a cloud provider, a language track) that is
    intentionally a placeholder in V1: declared in the interface, not faked as real."""
