# shared_db/models/__init__.py
"""Import all models so Alembic can detect them for migrations."""

from shared_db.models.agent import (
    Agent,
    AgentExecutionSession,
    AgentIterationHistory,
    AgentStatistics,
    AgentVersion,
    AgentVersionTool,
    TestScenario,
    TestScenarioResult,
)
from shared_db.models.error_report import ErrorReport
from shared_db.models.game import Game, GameEvent, GamePlayer
from shared_db.models.llm_integration import LLMIntegration
from shared_db.models.llm_usage import LLMUsage
from shared_db.models.tool import Tool
from shared_db.models.user import User

__all__ = [
    "Agent",
    "AgentExecutionSession",
    "AgentIterationHistory",
    "AgentStatistics",
    "AgentVersion",
    "AgentVersionTool",
    "ErrorReport",
    "Game",
    "GameEvent",
    "GamePlayer",
    "LLMIntegration",
    "LLMUsage",
    "TestScenario",
    "TestScenarioResult",
    "Tool",
    "User",
]
