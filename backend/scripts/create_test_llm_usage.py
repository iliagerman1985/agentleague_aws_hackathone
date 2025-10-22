"""Create test LLM usage data for development."""

import asyncio

from sqlalchemy import select

from shared_db.crud.llm_usage import LLMUsageDAO
from shared_db.db import AsyncSessionLocal
from shared_db.models.agent import Agent, AgentVersion
from shared_db.models.llm_enums import LLMUsageScenario
from shared_db.models.user import User
from shared_db.schemas.llm_usage import LLMUsageCreate


async def create_test_data():
    """Create test LLM usage data."""
    async with AsyncSessionLocal() as db:
        # Get first user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No users found. Please create a user first.")
            return

        # Get first agent
        result = await db.execute(select(Agent).where(Agent.user_id == user.id).limit(1))
        agent = result.scalar_one_or_none()
        if not agent:
            print("No agents found. Please create an agent first.")
            return

        # Get agent version
        result = await db.execute(select(AgentVersion).where(AgentVersion.agent_id == agent.id).limit(1))
        agent_version = result.scalar_one_or_none()
        if not agent_version:
            print("No agent versions found.")
            return

        print(f"Creating test LLM usage data for user {user.email}, agent {agent.name}")

        llm_usage_dao = LLMUsageDAO()

        # Create some test usage records
        test_usages = [
            LLMUsageCreate(
                user_id=user.id,
                agent_version_id=agent_version.id,
                scenario=LLMUsageScenario.AGENT_MOVE,
                model_used="claude-3-5-sonnet-20241022",
                cost_usd=0.0025,
                input_tokens=1500,
                output_tokens=500,
                total_tokens=2000,
                execution_time_ms=1200,
                input_prompt="Test prompt for agent move",
                output_response="Test response for agent move",
            ),
            LLMUsageCreate(
                user_id=user.id,
                agent_version_id=agent_version.id,
                scenario=LLMUsageScenario.AGENT_MOVE,
                model_used="claude-3-5-sonnet-20241022",
                cost_usd=0.0030,
                input_tokens=1800,
                output_tokens=600,
                total_tokens=2400,
                execution_time_ms=1400,
                input_prompt="Test prompt for agent move 2",
                output_response="Test response for agent move 2",
            ),
            LLMUsageCreate(
                user_id=user.id,
                agent_version_id=agent_version.id,
                scenario=LLMUsageScenario.STATE_GENERATION,
                model_used="claude-3-5-sonnet-20241022",
                cost_usd=0.0015,
                input_tokens=1000,
                output_tokens=300,
                total_tokens=1300,
                execution_time_ms=800,
                input_prompt="Test prompt for state generation",
                output_response="Test response for state generation",
            ),
            LLMUsageCreate(
                user_id=user.id,
                agent_version_id=agent_version.id,
                scenario=LLMUsageScenario.TOOL_GENERATION,
                model_used="gpt-4o",
                cost_usd=0.0020,
                input_tokens=1200,
                output_tokens=400,
                total_tokens=1600,
                execution_time_ms=1000,
                input_prompt="Test prompt for tool generation",
                output_response="Test response for tool generation",
            ),
        ]

        for usage in test_usages:
            await llm_usage_dao.create(db, usage)

        await db.commit()
        print(f"Created {len(test_usages)} test LLM usage records")


if __name__ == "__main__":
    asyncio.run(create_test_data())
