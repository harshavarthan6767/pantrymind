"""
PantryMind — Agents Package

Exports all agent definitions for use by the ADK runner and FastAPI
application.  The `root_agent` is the entry point for all user
interactions.

Usage:
    from agents import root_agent

    # For ADK Runner:
    runner = Runner(agent=root_agent, ...)

    # Individual sub-agents (for testing / direct invocation):
    from agents import (
        ingestion_agent,
        inventory_agent,
        financial_agent,
        dietary_agent,
        expiry_agent,
        analytics_agent,
    )
"""

from agents.root_agent import root_agent
from agents.ingestion_agent import ingestion_agent
from agents.inventory_agent import inventory_agent
from agents.financial_agent import financial_agent
from agents.dietary_agent import dietary_agent
from agents.expiry_agent import expiry_agent
from agents.analytics_agent import analytics_agent

__all__ = [
    "root_agent",
    "ingestion_agent",
    "inventory_agent",
    "financial_agent",
    "dietary_agent",
    "expiry_agent",
    "analytics_agent",
]
