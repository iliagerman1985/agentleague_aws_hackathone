/**
 * Tagged string types for all IDs to prevent mixing different ID types
 * and ensure type safety throughout the frontend.
 */

// Base branded type utility
type Brand<T, K> = T & { __brand: K };

// ID Types matching backend TSID format
export type AgentId = Brand<string, 'AgentId'>;
export type AgentVersionId = Brand<string, 'AgentVersionId'>;
export type PlayerId = Brand<string, 'PlayerId'>;
export type ToolId = Brand<string, 'ToolId'>;
export type UserId = Brand<string, 'UserId'>;
export type GameId = Brand<string, 'GameId'>;
export type TestScenarioId = Brand<string, 'TestScenarioId'>;
export type AgentStatisticsId = Brand<string, 'AgentStatisticsId'>;
export type AgentExecutionSessionId = Brand<string, 'AgentExecutionSessionId'>;
export type AgentIterationHistoryId = Brand<string, 'AgentIterationHistoryId'>;
export type LLMIntegrationId = Brand<string, 'LLMIntegrationId'>;
export type EventId = Brand<string, 'EventId'>;
export type ErrorReportId = Brand<string, 'ErrorReportId'>;