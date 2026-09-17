"""Toy RQL text → LogicalPlan JSON parser (Hypothesis; tiny subset)."""

from .parser import ParseError, parse_rql, parse_rql_file

__all__ = ["ParseError", "parse_rql", "parse_rql_file"]
__version__ = "0.1.0-toy"
