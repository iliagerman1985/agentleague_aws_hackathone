"""LLM Usage CRUD operations."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import AgentId, AgentVersionId, GameId, LLMUsageId, UserId
from shared_db.models.agent import AgentVersion
from shared_db.models.llm_enums import LLMUsageScenario
from shared_db.models.llm_usage import LLMUsage
from shared_db.schemas.llm_usage import (
    AgentLLMCostSummary,
    LLMUsageByModel,
    LLMUsageByScenario,
    LLMUsageCostSummary,
    LLMUsageCreate,
    LLMUsageResponse,
    LLMUsageStats,
    LLMUsageSummary,
)


class LLMUsageDAO:
    """Data Access Object for LLM Usage operations.
    Returns Pydantic objects instead of SQLAlchemy models.
    """

    def __init__(self) -> None:
        pass

    async def create(self, db: AsyncSession, usage: LLMUsageCreate) -> LLMUsageResponse:
        """Create a new LLM usage record."""
        db_usage = LLMUsage(
            user_id=usage.user_id,
            agent_version_id=usage.agent_version_id,
            scenario=usage.scenario.value,
            model_used=usage.model_used,
            cost_usd=usage.cost_usd,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            execution_time_ms=usage.execution_time_ms,
            input_prompt=usage.input_prompt,
            output_response=usage.output_response,
            game_id=usage.game_id,
            tool_id=usage.tool_id,
            test_scenario_id=usage.test_scenario_id,
        )
        db.add(db_usage)
        await db.flush()
        return LLMUsageResponse.model_validate(db_usage)

    async def get(self, db: AsyncSession, id: LLMUsageId) -> LLMUsageResponse | None:
        """Get an LLM usage record by ID."""
        result = await db.execute(select(LLMUsage).where(LLMUsage.id == id))
        usage = result.scalar_one_or_none()
        return LLMUsageResponse.model_validate(usage) if usage else None

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: UserId,
        skip: int = 0,
        limit: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[LLMUsageSummary]:
        """Get LLM usage records for a specific user."""
        query = select(LLMUsage).where(LLMUsage.user_id == user_id)

        if start_date:
            query = query.where(LLMUsage.created_at >= start_date)
        if end_date:
            query = query.where(LLMUsage.created_at <= end_date)

        query = query.order_by(LLMUsage.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        usages = result.scalars().all()
        return [LLMUsageSummary.model_validate(usage) for usage in usages]

    async def get_by_agent(
        self,
        db: AsyncSession,
        agent_version_id: AgentVersionId,
        skip: int = 0,
        limit: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[LLMUsageSummary]:
        """Get LLM usage records for a specific agent version."""
        query = select(LLMUsage).where(LLMUsage.agent_version_id == agent_version_id)

        if start_date:
            query = query.where(LLMUsage.created_at >= start_date)
        if end_date:
            query = query.where(LLMUsage.created_at <= end_date)

        query = query.order_by(LLMUsage.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        usages = result.scalars().all()
        return [LLMUsageSummary.model_validate(usage) for usage in usages]

    async def get_by_scenario(
        self,
        db: AsyncSession,
        scenario: LLMUsageScenario,
        user_id: UserId | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LLMUsageSummary]:
        """Get LLM usage records for a specific scenario."""
        query = select(LLMUsage).where(LLMUsage.scenario == scenario.value)

        if user_id:
            query = query.where(LLMUsage.user_id == user_id)

        query = query.order_by(LLMUsage.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        usages = result.scalars().all()
        return [LLMUsageSummary.model_validate(usage) for usage in usages]

    async def get_by_game(
        self,
        db: AsyncSession,
        game_id: GameId,
    ) -> list[LLMUsageSummary]:
        """Get all LLM usage records for a specific game."""
        result = await db.execute(select(LLMUsage).where(LLMUsage.game_id == game_id).order_by(LLMUsage.created_at.asc()))
        usages = result.scalars().all()
        return [LLMUsageSummary.model_validate(usage) for usage in usages]

    async def get_stats(
        self,
        db: AsyncSession,
        user_id: UserId | None = None,
        agent_version_id: AgentVersionId | None = None,
        scenario: LLMUsageScenario | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> LLMUsageStats:
        """Get aggregated statistics for LLM usage."""
        query = select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
            func.sum(LLMUsage.total_tokens).label("total_tokens"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.cost_usd).label("average_cost_per_call"),
            func.avg(LLMUsage.total_tokens).label("average_tokens_per_call"),
            func.avg(LLMUsage.execution_time_ms).label("average_execution_time_ms"),
        )

        if user_id:
            query = query.where(LLMUsage.user_id == user_id)
        if agent_version_id:
            query = query.where(LLMUsage.agent_version_id == agent_version_id)
        if scenario:
            query = query.where(LLMUsage.scenario == scenario.value)
        if start_date:
            query = query.where(LLMUsage.created_at >= start_date)
        if end_date:
            query = query.where(LLMUsage.created_at <= end_date)

        result = await db.execute(query)
        row = result.one()

        return LLMUsageStats(
            total_calls=row.total_calls or 0,
            total_cost_usd=float(row.total_cost_usd or 0.0),
            total_tokens=row.total_tokens or 0,
            total_input_tokens=row.total_input_tokens or 0,
            total_output_tokens=row.total_output_tokens or 0,
            average_cost_per_call=float(row.average_cost_per_call or 0.0),
            average_tokens_per_call=float(row.average_tokens_per_call or 0.0),
            average_execution_time_ms=float(row.average_execution_time_ms or 0.0),
        )

    async def get_cost_summary(
        self,
        db: AsyncSession,
        user_id: UserId | None = None,
        agent_version_id: AgentVersionId | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> LLMUsageCostSummary:
        """Get comprehensive cost summary with breakdowns by scenario and model."""
        # Get overall stats
        overall_stats = await self.get_stats(db, user_id, agent_version_id, None, start_date, end_date)

        # Get stats by scenario
        by_scenario = []
        for scenario in LLMUsageScenario:
            scenario_stats = await self.get_stats(db, user_id, agent_version_id, scenario, start_date, end_date)
            if scenario_stats.total_calls > 0:
                by_scenario.append(LLMUsageByScenario(scenario=scenario, stats=scenario_stats))

        # Get stats by model
        query = select(LLMUsage.model_used).distinct()
        if user_id:
            query = query.where(LLMUsage.user_id == user_id)
        if agent_version_id:
            query = query.where(LLMUsage.agent_version_id == agent_version_id)
        if start_date:
            query = query.where(LLMUsage.created_at >= start_date)
        if end_date:
            query = query.where(LLMUsage.created_at <= end_date)

        result = await db.execute(query)
        models = result.scalars().all()

        by_model = []
        for model in models:
            # Get stats for this specific model
            model_query = select(
                func.count(LLMUsage.id).label("total_calls"),
                func.sum(LLMUsage.cost_usd).label("total_cost_usd"),
                func.sum(LLMUsage.total_tokens).label("total_tokens"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
                func.avg(LLMUsage.cost_usd).label("average_cost_per_call"),
                func.avg(LLMUsage.total_tokens).label("average_tokens_per_call"),
                func.avg(LLMUsage.execution_time_ms).label("average_execution_time_ms"),
            ).where(LLMUsage.model_used == model)

            if user_id:
                model_query = model_query.where(LLMUsage.user_id == user_id)
            if agent_version_id:
                model_query = model_query.where(LLMUsage.agent_version_id == agent_version_id)
            if start_date:
                model_query = model_query.where(LLMUsage.created_at >= start_date)
            if end_date:
                model_query = model_query.where(LLMUsage.created_at <= end_date)

            model_result = await db.execute(model_query)
            model_row = model_result.one()

            model_stats = LLMUsageStats(
                total_calls=model_row.total_calls or 0,
                total_cost_usd=float(model_row.total_cost_usd or 0.0),
                total_tokens=model_row.total_tokens or 0,
                total_input_tokens=model_row.total_input_tokens or 0,
                total_output_tokens=model_row.total_output_tokens or 0,
                average_cost_per_call=float(model_row.average_cost_per_call or 0.0),
                average_tokens_per_call=float(model_row.average_tokens_per_call or 0.0),
                average_execution_time_ms=float(model_row.average_execution_time_ms or 0.0),
            )

            by_model.append(LLMUsageByModel(model_used=model, stats=model_stats))

        return LLMUsageCostSummary(
            user_id=user_id,
            agent_version_id=agent_version_id,
            start_date=start_date,
            end_date=end_date,
            overall_stats=overall_stats,
            by_scenario=by_scenario,
            by_model=by_model,
        )

    async def get_agent_cost_summary(
        self,
        db: AsyncSession,
        agent_id: AgentId,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AgentLLMCostSummary:
        """Get cost summary for all versions of an agent."""
        # Get all agent version IDs for this agent
        version_query = select(AgentVersion.id).where(AgentVersion.agent_id == agent_id)
        version_result = await db.execute(version_query)
        version_ids = [row[0] for row in version_result.all()]

        if not version_ids:
            # No versions, return empty summary
            return AgentLLMCostSummary(
                total_cost=0.0,
                total_calls=0,
                total_tokens=0,
                avg_cost_per_call=0.0,
                avg_execution_time_ms=0.0,
                by_scenario=[],
            )

        # Build query for all versions
        query = select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.cost_usd).label("total_cost"),
            func.sum(LLMUsage.total_tokens).label("total_tokens"),
            func.avg(LLMUsage.cost_usd).label("avg_cost_per_call"),
            func.avg(LLMUsage.execution_time_ms).label("avg_execution_time_ms"),
        ).where(LLMUsage.agent_version_id.in_(version_ids))

        if start_date:
            query = query.where(LLMUsage.created_at >= start_date)
        if end_date:
            query = query.where(LLMUsage.created_at <= end_date)

        result = await db.execute(query)
        row = result.one()

        # Get stats by scenario
        by_scenario = []
        for scenario in LLMUsageScenario:
            scenario_query = select(
                func.count(LLMUsage.id).label("count"),
                func.sum(LLMUsage.cost_usd).label("total_cost"),
                func.sum(LLMUsage.total_tokens).label("total_tokens"),
            ).where(
                LLMUsage.agent_version_id.in_(version_ids),
                LLMUsage.scenario == scenario.value,
            )

            if start_date:
                scenario_query = scenario_query.where(LLMUsage.created_at >= start_date)
            if end_date:
                scenario_query = scenario_query.where(LLMUsage.created_at <= end_date)

            scenario_result = await db.execute(scenario_query)
            scenario_row = scenario_result.one()

            if scenario_row.count and scenario_row.count > 0:
                by_scenario.append(
                    {
                        "scenario": scenario.value,
                        "count": scenario_row.count,
                        "total_cost": float(scenario_row.total_cost or 0.0),
                        "total_tokens": scenario_row.total_tokens or 0,
                    }
                )

        return AgentLLMCostSummary(
            total_cost=float(row.total_cost or 0.0),
            total_calls=row.total_calls or 0,
            total_tokens=row.total_tokens or 0,
            avg_cost_per_call=float(row.avg_cost_per_call or 0.0),
            avg_execution_time_ms=float(row.avg_execution_time_ms or 0.0),
            by_scenario=by_scenario,
        )
