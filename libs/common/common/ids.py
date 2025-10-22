from __future__ import annotations

from typing import NewType

from common.utils import TSID

RequestId = NewType("RequestId", TSID)
SqsMessageId = NewType("SqsMessageId", TSID)
UserId = NewType("UserId", TSID)
GameId = NewType("GameId", TSID)
GameEventId = NewType("GameEventId", TSID)
PlayerId = NewType("PlayerId", TSID)
AgentId = NewType("AgentId", TSID)
AgentVersionId = NewType("AgentVersionId", TSID)
AgentVersionToolId = NewType("AgentVersionToolId", TSID)
AgentStatisticsId = NewType("AgentStatisticsId", TSID)
AgentExecutionSessionId = NewType("AgentExecutionSessionId", TSID)
AgentIterationHistoryId = NewType("AgentIterationHistoryId", TSID)
TestScenarioId = NewType("TestScenarioId", TSID)
TestScenarioResultId = NewType("TestScenarioResultId", TSID)
ToolId = NewType("ToolId", TSID)
LLMIntegrationId = NewType("LLMIntegrationId", TSID)
LLMUsageId = NewType("LLMUsageId", TSID)
EventId = NewType("EventId", TSID)
ErrorReportId = NewType("ErrorReportId", TSID)
