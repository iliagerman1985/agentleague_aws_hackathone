"""Recalculate agent statistics from finished games."""

import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import from app
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from game_api import GameType
from sqlalchemy import select

from app.services.game_env_registry import GameEnvRegistry
from common.ids import AgentId, AgentVersionId, PlayerId
from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
from shared_db.db import AsyncSessionLocal
from shared_db.models.agent import Agent, AgentStatisticsData
from shared_db.models.game import Game, GamePlayer, MatchmakingStatus


async def recalculate_statistics():
    """Recalculate all agent statistics from scratch."""
    async with AsyncSessionLocal() as db:
        stats_dao = AgentStatisticsDAO()
        agent_dao = AgentDAO()

        print("Resetting all agent statistics to defaults...")
        # Get all agents
        result = await db.execute(select(Agent))
        agents = result.scalars().all()

        for agent in agents:
            # Reset statistics to default
            default_stats = AgentStatisticsData()
            await stats_dao.update_statistics(db, agent_id=agent.id, updates=default_stats.model_dump())

        await db.commit()
        print(f"Reset statistics for {len(agents)} agents")

        # Get all finished games
        result = await db.execute(select(Game).where(Game.matchmaking_status == MatchmakingStatus.FINISHED).order_by(Game.created_at.asc()))
        games = result.scalars().all()

        print(f"\nFound {len(games)} finished games to process")

        # Process each game
        from app.schemas.scoring import GameRatingUpdateRequest
        from app.services.scoring_service import ScoringService
        from shared_db.crud.game import GameDAO

        game_dao = GameDAO()
        scoring_service = ScoringService(agent_dao, stats_dao, game_dao)
        registry = GameEnvRegistry.instance()

        for i, game in enumerate(games, 1):
            print(f"\nProcessing game {i}/{len(games)}: {game.id} ({game.game_type})")

            # Get game players
            result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == game.id))
            game_players = result.scalars().all()

            if not game_players:
                print("  Skipping - no players found")
                continue

            # Build agent mapping (player_id -> agent_id) and agent_version_mapping (agent_id -> agent_version_id)
            # Need to look up agent_id from agent_version_id
            agent_mapping: dict[PlayerId, AgentId] = {}
            agent_version_mapping: dict[AgentId, AgentVersionId] = {}
            player_ids: list[PlayerId] = []

            for gp in game_players:
                # Get the agent version to find the parent agent_id
                from shared_db.crud.agent import AgentVersionDAO

                agent_version_dao = AgentVersionDAO()
                agent_version = await agent_version_dao.get(db, gp.agent_version_id)
                if agent_version:
                    agent_mapping[gp.id] = agent_version.agent_id
                    agent_version_mapping[agent_version.agent_id] = gp.agent_version_id
                    player_ids.append(gp.id)

            if not agent_mapping:
                print("  Skipping - no agents found")
                continue

            # Parse game state to get result using the environment's extract_game_result method
            try:
                env_class = registry.get(game.game_type)

                # Parse state based on game type
                if game.game_type == GameType.CHESS:
                    from chess_game.chess_api import ChessState

                    state = ChessState.model_validate(game.state)
                elif game.game_type == GameType.TEXAS_HOLDEM:
                    from texas_holdem.texas_holdem_api import TexasHoldemState

                    state = TexasHoldemState.model_validate(game.state)
                else:
                    print(f"  Skipping - unknown game type: {game.game_type}")
                    continue

                # Extract game result
                game_result = env_class.extract_game_result(state)

                # Create rating update request
                request = GameRatingUpdateRequest(
                    game_id=game.id, game_type=game.game_type, player_ids=player_ids, agent_mapping=agent_mapping, agent_version_mapping=agent_version_mapping
                )

                # Update ratings
                response = await scoring_service.update_agent_ratings_after_game(db=db, request=request, game_result=game_result)

                print(f"  Updated ratings for {len(response.rating_updates)} agents")
                for agent_id, update in response.rating_updates.items():
                    print(f"    Agent {agent_id}: {update.old_rating:.0f} -> {update.new_rating:.0f} ({update.rating_change:+.0f})")

            except Exception as e:
                print(f"  Error processing game: {e}")
                import traceback

                traceback.print_exc()
                continue

        await db.commit()
        print("\n✅ Statistics recalculation complete!")


if __name__ == "__main__":
    asyncio.run(recalculate_statistics())
