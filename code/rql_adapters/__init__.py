"""Hypothesis PhysicalPlan → vendor request emit stub (strings/JSON only; never executed)."""

from .emit import AdapterError, emit_plan, emit_to_files, list_vendors, resolve_vendor

__all__ = [
    "AdapterError",
    "emit_plan",
    "emit_to_files",
    "list_vendors",
    "resolve_vendor",
]
