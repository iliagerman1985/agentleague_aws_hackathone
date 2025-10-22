"""Service for handling game scoring and rating calculations."""

from game_api import GameResult, GameType
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.scoring import (
    AgentProfileData,
    AgentProfileStats,
    GameRatingUpdateRequest,
    GameRatingUpdateResponse,
    RatingUpdate,
)
from common.core.logging_service import get_logger
from common.ids import AgentId, AgentVersionId, GameId, PlayerId
from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
from shared_db.crud.game import GameDAO
from shared_db.crud.user import UserDAO
from shared_db.models.agent import AgentGameRating, AgentStatisticsData, RecentGameEntry

logger = get_logger(__name__)


class ScoringService:
    """Service for calculating and updating agent ratings based on game results."""

    def __init__(self, agent_dao: AgentDAO, agent_statistics_dao: AgentStatisticsDAO, game_dao: GameDAO, user_dao: UserDAO | None = None):
        self.agent_dao = agent_dao
        self.agent_statistics_dao = agent_statistics_dao
        self.game_dao = game_dao
        self.user_dao = user_dao or UserDAO()

    async def _get_game_duration_seconds(self, db: AsyncSession, game_id: GameId, agent_version_id: AgentVersionId) -> int | None:
        """Calculate game duration for a specific player.

        Args:
            db: Database session
            game_id: Game ID
            agent_version_id: Agent version ID

        Returns:
            Duration in seconds, or None if join_time or leave_time is missing
        """
        # Get all game players for this game (including those who have left)
        game_players = await self.game_dao.get_game_players(db, game_id, include_inactive=True)

        # Find the player with matching agent_version_id
        game_player = next((gp for gp in game_players if gp.agent_version_id == agent_version_id), None)

        if not game_player or not game_player.join_time or not game_player.leave_time:
            return None

        duration = (game_player.leave_time - game_player.join_time).total_seconds()
        return int(duration)

    async def update_agent_ratings_after_game(self, db: AsyncSession, request: GameRatingUpdateRequest, game_result: GameResult) -> GameRatingUpdateResponse:
        """Update agent ratings after a game completes.

        Args:
            db: Database session
            request: Rating update request with game info and agent mapping
            game_result: Game result with winner/draw information

        Returns:
            Response containing rating updates for all agents
        """
        # Import scoring classes here to avoid circular dependencies
        scoring_class = self._get_scoring_class(request.game_type)

        # Get current ratings for all agents in the game
        agent_ratings = await self._get_agent_ratings(db, list(request.agent_mapping.values()))

        # Calculate rating changes for each agent
        rating_updates: dict[AgentId, RatingUpdate] = {}

        for player_id in request.player_ids:
            if player_id not in request.agent_mapping:
                continue

            agent_id = request.agent_mapping[player_id]

            # Get current rating and games played
            current_stats = agent_ratings.get(agent_id)
            if current_stats and request.game_type in current_stats.game_ratings:
                game_rating = current_stats.game_ratings[request.game_type]
                current_rating = game_rating.rating
                games_played = game_rating.games_played
            else:
                current_rating = scoring_class.get_default_rating()
                games_played = 0

            # Build opponent ratings dictionary
            opponent_ratings: dict[PlayerId, float] = {}
            for opp_id in request.player_ids:
                if opp_id == player_id:
                    continue
                if opp_id in request.agent_mapping:
                    opp_agent_id = request.agent_mapping[opp_id]
                    opp_stats = agent_ratings.get(opp_agent_id)
                    if opp_stats and request.game_type in opp_stats.game_ratings:
                        opponent_ratings[opp_id] = opp_stats.game_ratings[request.game_type].rating
                    else:
                        opponent_ratings[opp_id] = scoring_class.get_default_rating()

            # Let the scoring class handle all the game-specific logic
            rating_change, new_rating = scoring_class.calculate_rating_update(
                result=game_result, player_id=player_id, current_rating=current_rating, games_played=games_played, opponent_ratings=opponent_ratings
            )

            rating_updates[agent_id] = RatingUpdate(agent_id=agent_id, rating_change=rating_change, new_rating=new_rating, old_rating=current_rating)

        # Update agent statistics in database
        await self._update_agent_statistics(
            db, request.game_id, request.game_type, game_result, request.agent_mapping, request.agent_version_mapping, rating_updates
        )

        return GameRatingUpdateResponse(game_id=request.game_id, game_type=request.game_type, rating_updates=rating_updates)

    def _get_scoring_class(self, game_type: GameType):
        """Get the appropriate scoring class for the game type."""
        if game_type == GameType.CHESS:
            from libs.game.chess_game.chess_scoring import ChessScoring

            return ChessScoring
        if game_type == GameType.TEXAS_HOLDEM:
            from libs.game.texas_holdem.texas_holdem_scoring import TexasHoldemScoring

            return TexasHoldemScoring
        raise ValueError(f"No scoring class implemented for game type: {game_type}")  # type: ignore[unreachable]

    async def _get_agent_ratings(self, db: AsyncSession, agent_ids: list[AgentId]) -> dict[AgentId, AgentStatisticsData]:
        """Get current statistics for multiple agents."""
        ratings = {}

        for agent_id in agent_ids:
            stats_response = await self.agent_statistics_dao.get_by_agent(db, agent_id)
            if stats_response:
                ratings[agent_id] = AgentStatisticsData.model_validate(stats_response.statistics)

        return ratings

    async def _update_agent_statistics(
        self,
        db: AsyncSession,
        game_id: GameId,
        game_type: GameType,
        game_result: GameResult,
        agent_mapping: dict[PlayerId, AgentId],
        agent_version_mapping: dict[AgentId, AgentVersionId],
        rating_updates: dict[AgentId, RatingUpdate],
    ) -> None:
        """Update agent statistics after a game."""
        scoring_class = self._get_scoring_class(game_type)

        # Helper function to normalize PlayerId to comparable format
        def normalize_player_id(pid: PlayerId | None) -> str | None:
            """Convert PlayerId to string representation for comparison."""
            if pid is None:
                return None
            return str(pid)

        # Normalize winner and winners for comparison
        normalized_winner = normalize_player_id(game_result.winner_id)
        normalized_winners = [normalize_player_id(w) for w in game_result.winners_ids]

        for player_id, agent_id in agent_mapping.items():
            # Normalize current player_id for comparison
            normalized_player = normalize_player_id(player_id)

            # Get current statistics
            stats_response = await self.agent_statistics_dao.get_by_agent(db, agent_id)
            if not stats_response:
                # Initialize statistics if they don't exist
                current_stats = AgentStatisticsData().model_dump()
            else:
                current_stats = stats_response.statistics

            # Parse into Pydantic model
            stats_data = AgentStatisticsData.model_validate(current_stats)

            # Get or create game-specific rating object
            default_rating = scoring_class.get_default_rating()
            if game_type not in stats_data.game_ratings:
                game_stats = AgentGameRating(
                    rating=default_rating, games_played=0, games_won=0, games_lost=0, games_drawn=0, highest_rating=default_rating, lowest_rating=default_rating
                )
            else:
                game_stats = stats_data.game_ratings[game_type]

            # Update rating
            old_rating = game_stats.rating
            new_rating = rating_updates[agent_id].new_rating
            game_stats.rating = max(new_rating, 0)  # Ensure minimum of 0

            # Update games played
            game_stats.games_played += 1

            # Determine if this player won, drew, or lost using normalized IDs
            is_winner = normalized_player == normalized_winner or normalized_player in normalized_winners
            # A draw only occurs if there's a draw_reason AND no winner/winners
            # If there's a winner, it's a win/loss regardless of draw_reason (e.g., forfeit should not be a draw)
            is_draw = game_result.draw_reason is not None and normalized_winner is None and len(normalized_winners) == 0

            # Update win/loss/draw counts
            if is_winner:
                game_stats.games_won += 1
            elif is_draw:
                game_stats.games_drawn += 1
            else:
                game_stats.games_lost += 1

            # Update highest/lowest ratings
            game_stats.highest_rating = max(game_stats.highest_rating, new_rating)
            game_stats.lowest_rating = min(game_stats.lowest_rating, new_rating)

            # Store the updated rating object back
            stats_data.game_ratings[game_type] = game_stats

            # Add to recent form (keep only last 10)
            result_str = "win" if is_winner else ("draw" if is_draw else "loss")
            from datetime import UTC, datetime

            recent_entry = RecentGameEntry(
                game_id=str(game_result.final_scores.get(player_id, 0)) if game_result.final_scores else None,
                game_type=game_type.value,
                result=result_str,
                rating_change=rating_updates[agent_id].rating_change,
                rating_after=new_rating,
                timestamp=datetime.now(UTC).isoformat(),
            )

            stats_data.recent_form.append(recent_entry)
            if len(stats_data.recent_form) > 10:
                stats_data.recent_form = stats_data.recent_form[-10:]

            # Update overall statistics
            stats_data.games_played += 1
            if is_winner:
                stats_data.games_won += 1
            elif is_draw:
                stats_data.games_drawn += 1
            else:
                stats_data.games_lost += 1

            # Calculate win rate
            if stats_data.games_played > 0:
                stats_data.win_rate = (stats_data.games_won / stats_data.games_played) * 100

            # Update game duration statistics (only for real games, not playground)
            if agent_id in agent_version_mapping:
                agent_version_id = agent_version_mapping[agent_id]
                game_duration = await self._get_game_duration_seconds(db, game_id, agent_version_id)

                logger.info(
                    f"Game duration for agent {agent_id}: {game_duration} seconds",
                    extra={"agent_id": str(agent_id), "game_id": str(game_id), "agent_version_id": str(agent_version_id), "duration_seconds": game_duration},
                )

                if game_duration is not None and game_duration > 0:
                    logger.info(
                        f"Before updating stats_data for agent {agent_id}",
                        extra={
                            "agent_id": str(agent_id),
                            "stats_data_id": id(stats_data),
                            "session_time_seconds_before": stats_data.session_time_seconds,
                            "longest_game_seconds_before": stats_data.longest_game_seconds,
                            "shortest_game_seconds_before": stats_data.shortest_game_seconds,
                        },
                    )

                    # Update total session time
                    stats_data.session_time_seconds += game_duration

                    # Update longest game
                    stats_data.longest_game_seconds = max(stats_data.longest_game_seconds, game_duration)

                    # Update shortest game
                    if stats_data.shortest_game_seconds is None or game_duration < stats_data.shortest_game_seconds:
                        stats_data.shortest_game_seconds = game_duration

                    logger.info(
                        f"After updating stats_data for agent {agent_id}",
                        extra={
                            "agent_id": str(agent_id),
                            "stats_data_id": id(stats_data),
                            "session_time_seconds_after": stats_data.session_time_seconds,
                            "longest_game_seconds_after": stats_data.longest_game_seconds,
                            "shortest_game_seconds_after": stats_data.shortest_game_seconds,
                        },
                    )
            else:
                logger.warning(
                    f"Agent {agent_id} not in agent_version_mapping - skipping game duration calculation",
                    extra={"agent_id": str(agent_id), "game_id": str(game_id), "agent_version_mapping_keys": [str(k) for k in agent_version_mapping]},
                )

            # Save updated statistics
            logger.info(
                f"Before model_dump for agent {agent_id}",
                extra={
                    "agent_id": str(agent_id),
                    "stats_data_id": id(stats_data),
                    "session_time_seconds": stats_data.session_time_seconds,
                    "longest_game_seconds": stats_data.longest_game_seconds,
                    "shortest_game_seconds": stats_data.shortest_game_seconds,
                },
            )

            stats_dict = stats_data.model_dump()

            logger.info(
                f"After model_dump for agent {agent_id}",
                extra={
                    "agent_id": str(agent_id),
                    "session_time_seconds_in_dict": stats_dict.get("session_time_seconds"),
                    "longest_game_seconds_in_dict": stats_dict.get("longest_game_seconds"),
                    "shortest_game_seconds_in_dict": stats_dict.get("shortest_game_seconds"),
                    "games_played": stats_dict.get("games_played"),
                },
            )
            _ = await self.agent_statistics_dao.update_statistics(db, agent_id=agent_id, updates=stats_dict)

            logger.info(
                f"Updated statistics for agent {agent_id}",
                extra={
                    "game_type": game_type.value,
                    "old_rating": old_rating,
                    "new_rating": new_rating,
                    "rating_change": rating_updates[agent_id].rating_change,
                    "total_games": stats_data.games_played,
                    "result": result_str,
                },
            )

    async def get_agent_game_rating(self, db: AsyncSession, agent_id: AgentId, game_type: GameType) -> AgentGameRating:
        """Get an agent's rating and statistics for a specific game type."""
        stats_response = await self.agent_statistics_dao.get_by_agent(db, agent_id)
        if not stats_response:
            scoring_class = self._get_scoring_class(game_type)
            default_rating = scoring_class.get_default_rating()
            return AgentGameRating(
                rating=default_rating, games_played=0, games_won=0, games_lost=0, games_drawn=0, highest_rating=default_rating, lowest_rating=default_rating
            )

        stats_data = AgentStatisticsData.model_validate(stats_response.statistics)

        # game_ratings values are AgentGameRating Pydantic objects, not dicts
        game_stats = stats_data.game_ratings.get(game_type)

        if game_stats:
            # Return existing rating data
            return game_stats

        # No rating data exists for this game type - return default
        scoring_class = self._get_scoring_class(game_type)
        default_rating = scoring_class.get_default_rating()
        return AgentGameRating(
            rating=default_rating, games_played=0, games_won=0, games_lost=0, games_drawn=0, highest_rating=default_rating, lowest_rating=default_rating
        )

    async def get_agent_profile_data(self, db: AsyncSession, agent_id: AgentId) -> AgentProfileData:
        """Get comprehensive profile data for an agent."""
        agent = await self.agent_dao.get(db, agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        stats_response = await self.agent_statistics_dao.get_by_agent(db, agent_id)
        stats_data = AgentStatisticsData.model_validate(stats_response.statistics) if stats_response else AgentStatisticsData()

        # Get ratings for all game types
        game_ratings: dict[str, AgentGameRating] = {}
        for game_type in GameType:
            rating_data = await self.get_agent_game_rating(db, agent_id, game_type)
            # Include rating for agent's game environment even if no games played (shows default rating)
            # For other game types, only include if games have been played
            if rating_data.games_played > 0 or (agent.game_environment and game_type.value == agent.game_environment):
                game_ratings[game_type.value] = rating_data

        # Recent form is already a list of RecentGameEntry objects
        recent_form: list[RecentGameEntry] = stats_data.recent_form

        overall_stats = AgentProfileStats(
            games_played=stats_data.games_played,
            games_won=stats_data.games_won,
            games_lost=stats_data.games_lost,
            games_drawn=stats_data.games_drawn,
            win_rate=stats_data.win_rate,
            recent_form=recent_form,
        )

        # Get username from user_id if available
        username = None
        if agent.user_id:
            user = await self.user_dao.get(db, agent.user_id)
            if user:
                username = user.username

        return AgentProfileData(
            agent_id=str(agent_id),
            name=agent.name,
            description=agent.description,
            game_environment=agent.game_environment,
            avatar_url=agent.avatar_url,
            avatar_type=agent.avatar_type.value if agent.avatar_type else "default",
            is_system=agent.is_system,
            created_at=agent.created_at,
            username=username,
            overall_stats=overall_stats,
            game_ratings=game_ratings,
        )
