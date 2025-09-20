"""Compatibility shim: re-export agent implementation from app.agents.

This keeps existing imports (e.g. `from agent import SemanticKernelEcommerceAgent`) working
while the package migrates to the new layout.
"""
from app.agents.ecommerce_agent import SemanticKernelEcommerceAgent

__all__ = ["SemanticKernelEcommerceAgent"]
import logging
