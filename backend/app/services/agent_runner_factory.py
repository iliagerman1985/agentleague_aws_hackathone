"""Factory for creating AgentRunner instances based on environment and configuration."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from app.services.agent_execution_service import AgentExecutionService
from app.services.agent_runner import AgentRunner
from app.services.agent_runner.agentcore_client import AgentCoreClient
from app.services.agent_runner.direct_agent_runner import DirectAgentRunner
from app.services.agent_runner.localhost_agentcore_client import LocalHostAgentCoreClient
from common.core.config_service import ConfigService
from common.core.deployment import Deployment
from common.utils.utils import get_logger

logger = get_logger()

config_service = ConfigService()


class AgentRunnerType(StrEnum):
    """Supported AgentRunner types."""

    DIRECT = "direct"
    LOCALHOST = "localhost"
    AGENTCORE = "agentcore"


class AgentRunnerFactory(Protocol):
    """Protocol for AgentRunner factory."""

    @staticmethod
    def create_runner(agent_execution_service: AgentExecutionService) -> AgentRunner:
        """Create an AgentRunner instance based on environment and configuration."""
        # Local environments support multiple runner types
        runner = config_service.get("agent_runner", AgentRunnerType.DIRECT).lower()
        if runner == AgentRunnerType.DIRECT:
            return DirectAgentRunner(agent_execution_service)
        elif runner == AgentRunnerType.LOCALHOST:
            return LocalHostAgentCoreClient(config_service)
        elif runner == AgentRunnerType.AGENTCORE:
            return AgentCoreClient(config_service)
        elif Deployment.is_cloud():
            # Cloud environments (AWS) use AgentCore
            return AgentCoreClient(config_service)
        else:
            raise ValueError(f"Invalid agent runner: {runner}. Supported types: {[t.value for t in AgentRunnerType]}")
