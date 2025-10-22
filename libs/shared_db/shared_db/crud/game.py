"""Game CRUD operations with lease-based processing."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from game_api import BaseGameConfig, BaseGameEvent, BaseGameState, GameType
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from common.core.app_error import Errors
from common.ids import AgentId, AgentVersionId, GameId, RequestId, UserId
from common.utils.tsid import TSID
from common.utils.utils import get_now
from shared_db.models.agent import Agent, AgentVersion
from shared_db.models.game import Game, GameEvent, GamePlayer, MatchmakingStatus
from shared_db.models.user import User, UserRole


# Result of attempting to join a game atomically
class JoinResult(StrEnum):
    JOINED = "joined"
    ALREADY_JOINED = "already_joined"
    FULL = "full"


class GameDAO:
    async def get_version(self, db: AsyncSession, game_id: GameId) -> int | None:
        """Get just the version number of a game (lightweight query for polling)."""
        query = select(Game.version).filter(Game.id == game_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_requesting_user_id(self, db: AsyncSession, game_id: GameId) -> UserId | None:
        """Get just the requesting_user_id of a game (lightweight query for analysis)."""
        query = select(Game.requesting_user_id).filter(Game.id == game_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_game_type(self, db: AsyncSession, game_id: GameId) -> GameType | None:
        """Get just the game_type of a game (lightweight query)."""
        query = select(Game.game_type).filter(Game.id == game_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_events(self, db: AsyncSession, game_id: GameId) -> list[GameEvent]:
        """Get all events for a game."""
        query = select(GameEvent).filter(GameEvent.game_id == game_id).order_by(GameEvent.created_at)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, game_id: GameId, version: int | None = None, processing_request_id: RequestId | None = None) -> Game | None:
        """Get a game by ID with eagerly loaded agent relationships and events."""
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent).joinedload(Agent.statistics),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .filter(Game.id == game_id)
        )

        if version is not None:
            query = query.filter(Game.version == version)
        if processing_request_id is not None:
            query = query.filter(Game.processing_request_id == processing_request_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def insert(
        self,
        db: AsyncSession,
        game_id: GameId,
        game_type: GameType,
        state: BaseGameState,
        config: BaseGameConfig,
        players: list[GamePlayer],
        events: list[BaseGameEvent],
        requesting_user_id: UserId,
        is_playground: bool = False,
    ) -> Game:
        game_events = [
            GameEvent(
                id=event.id,
                game_id=game_id,
                type=type(event).__name__,  # Use the class name as event type
                data=event.to_dict(mode="json"),
            )
            for event in events
        ]

        game = Game(
            id=game_id,
            game_type=game_type,
            state=state.to_dict(mode="json"),
            config=config.to_dict(mode="json"),
            requesting_user_id=requesting_user_id,
            version=0,
            is_playground=is_playground,
            events=game_events,
            game_players=players,
        )
        db.add(game)

        # FIXME: Temp solution because the game is expected to actually be in the db, because it gets fetched again. Fix by removing the double fetch.
        await db.flush()

        return game

    async def start_processing(
        self,
        db: AsyncSession,
        request_id: RequestId,
        game_id: GameId,
        processing_timeout: timedelta,
        heartbeat_timeout: timedelta,
        expected_turn: int | None,
    ) -> Game:
        """Claim a game for processing by setting processing_started_at.

        Args:
            db: Database session
            request_id: ID of the request to claim
            game_id: ID of the game to claim
            timeout_duration: Timeout duration for considering a processing lock stale
            expected_turn: Expected turn number for validation (optional)

        Returns:
            Full Game object with updated processing_started_at and version

        Raises:
            STILL_PROCESSING: If another worker claimed the game or game doesn't exist
            TURN_ADVANCEMENT_CONFLICT: If turn number doesn't match (when expected_turn is provided)
        """
        now = datetime.now(UTC)

        where_clause = and_(
            Game.id == game_id,
            or_(
                Game.processing_request_id.is_(None),  # Not being processed
                Game.processing_started_at < now - processing_timeout,  # Processing took too long
                Game.updated_at < now - heartbeat_timeout,  # Heartbeat expired
            ),
        )
        if expected_turn is not None:
            where_clause = and_(where_clause, Game.turn == expected_turn)

        # Atomic update: claim the game if it's not being processed or the lock is stale
        result = await db.execute(
            update(Game)
            .where(where_clause)
            .values(
                processing_started_at=now,
                processing_request_id=request_id,
                version=Game.version + 1,
                updated_at=now,  # Initial heartbeat
            )
            .returning(Game.version)
        )

        row = result.fetchone()
        if row is None:
            # Check if game exists
            existing_game = await self.get(db, game_id)
            if not existing_game:
                raise Errors.Game.NOT_FOUND.create(details={"game_id": game_id})

            # Check if turn number mismatch (only when expected_turn is provided)
            if expected_turn is not None and existing_game.turn != expected_turn:
                raise Errors.Game.TURN_ADVANCEMENT_CONFLICT.create(
                    message=f"Turn advancement conflict: expected {expected_turn}, current {existing_game.turn}",
                    details={
                        "game_id": game_id,
                        "expected_turn": expected_turn,
                        "current_turn": existing_game.turn,
                    },
                )

            # Game is being processed by another active request
            raise Errors.Game.ALREADY_PROCESSING.create(details={"game_id": game_id})

        # Now fetch the full game with relationships
        game = await self.get(db, game_id, processing_request_id=request_id, version=row.version)
        if not game:
            raise Errors.Game.CONCURRENT_PROCESSING.create(details={"game_id": game_id, "expected_version": row.version})

        return game

    async def finish_processing(self, db: AsyncSession, request_id: RequestId, game_id: GameId) -> None:
        """Release the processing lock on a game."""
        _ = await db.execute(
            update(Game)
            .where(Game.id == game_id, Game.processing_started_at.isnot(None), Game.processing_request_id == request_id)
            .values(
                processing_started_at=None,
                processing_request_id=None,
                version=Game.version + 1,
            )
        )

        # Do not fail on concurrent processing, it means another worker is on it

    async def update_game(self, db: AsyncSession, game: Game) -> None:
        """Update game state with optimistic concurrency control."""
        # First increment the version, which verifies it wasn't updated by anyone else
        await self._increment_version(db, game)

        # TODO: Do this as part of the above
        db.add(game)

    async def _increment_version(self, db: AsyncSession, game: Game) -> None:
        """Increment game version with optimistic locking."""
        result = await db.execute(update(Game).where(Game.id == game.id, Game.version == game.version).values(version=Game.version + 1))

        if result.rowcount == 0:
            raise Errors.Game.CONCURRENT_PROCESSING.create(details={"game_id": game.id})

        # DO NOT increment the version in the game object, it is done automatically by SQLAlchemy

    async def set_player(
        self,
        db: AsyncSession,
        game_id: GameId,
        agent_version_id: AgentVersionId,
        user_id: UserId,
        env: GameType,
        join_time: datetime | None = None,
    ) -> GamePlayer:
        """Create or update a game participant record using upsert."""
        if join_time is None:
            join_time = datetime.now(UTC)

        # Use PostgreSQL's ON CONFLICT for upsert functionality
        stmt = insert(GamePlayer).values(
            game_id=game_id,
            agent_version_id=agent_version_id,
            user_id=user_id,
            env=env,
            join_time=join_time,
            leave_time=None,  # Reset leave_time in case participant is rejoining
        )

        # Handle conflict on the unique constraint (game_id, agent_version_id)
        stmt = stmt.on_conflict_do_update(
            constraint="unique_game_agent_version",
            set_={
                "join_time": stmt.excluded.join_time,
                "leave_time": None,  # Reset leave_time for rejoining participants
                "updated_at": stmt.excluded.updated_at,
            },
        )

        # Execute the upsert
        _ = await db.execute(stmt)

        # Fetch the GamePlayer with eagerly loaded relationships
        query = (
            select(GamePlayer)
            .options(joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent))
            .filter(GamePlayer.game_id == game_id, GamePlayer.agent_version_id == agent_version_id)
        )
        result = await db.execute(query)
        participant = result.scalar_one()
        return participant

    async def set_leave_time(
        self,
        db: AsyncSession,
        game_id: GameId,
        agent_version_id: AgentVersionId,
        leave_time: datetime | None = None,
    ) -> None:
        """Set the leave time for a participant."""
        if leave_time is None:
            leave_time = datetime.now(UTC)

        _ = await db.execute(
            update(GamePlayer)
            .where(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.agent_version_id == agent_version_id,
                )
            )
            .values(leave_time=leave_time)
        )

    async def set_leave_time_for_game(self, db: AsyncSession, game_id: GameId, leave_time: datetime | None = None) -> None:
        """Set leave time for all participants in a game (when game ends)."""
        if leave_time is None:
            leave_time = datetime.now(UTC)

        _ = await db.execute(
            update(GamePlayer)
            .where(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.leave_time.is_(None),
                )
            )
            .values(leave_time=leave_time)
        )

    async def get_games_by_user(
        self,
        db: AsyncSession,
        user_id: UserId,
        env: GameType | None = None,
        from_game_id: GameId | None = None,
        limit: int = 100,
        only_active: bool = True,
    ) -> list[Game]:
        """Get games for a user by querying the participants table.

        This is the efficient way to get user's games using cursor-based pagination.

        Args:
            db: Database session
            user_id: User ID to filter games by
            env: Optional game environment filter
            from_game_id: Get games after this game ID for cursor-based pagination
            limit: Maximum number of records to return
            only_active: If True, only return active games; if False, return all games

        Returns:
            List of games where user is participating
        """
        # Build query that joins games with participants
        # Use selectinload for collections to avoid row duplication issues
        # Use joinedload for agent relationships since they're one-to-one from game player perspective
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .join(GamePlayer, Game.id == GamePlayer.game_id)
            .filter(GamePlayer.user_id == user_id)
        )

        # Filter by environment if specified
        if env:
            query = query.filter(GamePlayer.env == env)

        # Filter by active status if specified
        if only_active:
            query = query.filter(
                GamePlayer.leave_time.is_(None),  # Only active participants
                Game.matchmaking_status.in_([MatchmakingStatus.WAITING, MatchmakingStatus.IN_PROGRESS]),  # Exclude finished/cancelled games
            )

        # Apply cursor-based pagination
        if from_game_id:
            query = query.filter(Game.id > from_game_id)

        # Order by game ID descending for proper cursor pagination
        query = query.distinct(Game.id).order_by(Game.id.desc())

        # Apply limit
        query = query.limit(limit)

        result = await db.execute(query.execution_options(populate_existing=True))
        return list(result.scalars().all())

    async def count_games_by_user(
        self,
        db: AsyncSession,
        user_id: UserId,
        env: GameType | None = None,
        only_active: bool = True,
    ) -> int:
        """Return a lightweight count of user's games without loading events/state."""
        q = select(func.count(func.distinct(Game.id))).join(GamePlayer, Game.id == GamePlayer.game_id).where(GamePlayer.user_id == user_id)
        if env:
            q = q.where(GamePlayer.env == env)
        if only_active:
            q = q.where(
                GamePlayer.leave_time.is_(None),
                Game.matchmaking_status.in_([MatchmakingStatus.WAITING, MatchmakingStatus.IN_PROGRESS]),
            )
        res = await db.execute(q)
        return int(res.scalar() or 0)

    async def get_games_by_agent(
        self,
        db: AsyncSession,
        agent_id: AgentId,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Game]:
        """Get games where a specific agent participated.

        Only returns competitive (non-playground) games.

        Args:
            db: Database session
            agent_id: Agent ID to filter games by
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of games where the agent participated
        """
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .join(GamePlayer, Game.id == GamePlayer.game_id)
            .join(AgentVersion, GamePlayer.agent_version_id == AgentVersion.id)
            .where(
                AgentVersion.agent_id == agent_id,
                Game.is_playground == False,  # Filter out playground games
            )
            .distinct(Game.id)
            .order_by(Game.id.desc(), Game.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query.execution_options(populate_existing=True))
        return list(result.scalars().unique().all())

    async def cancel_user_playgrounds_except(self, db: AsyncSession, user_id: UserId, exclude_game_id: GameId) -> None:
        """Cancel all playground games for a user except the specified one."""
        stmt = (
            update(Game)
            .where(
                and_(
                    Game.is_playground.is_(True),
                    Game.requesting_user_id == user_id,
                    Game.id != exclude_game_id,
                )
            )
            .values(
                matchmaking_status=MatchmakingStatus.CANCELLED,
                version=Game.version + 1,
            )
        )
        _ = await db.execute(stmt)

    async def get_player_owner_roles(self, db: AsyncSession, game_id: GameId) -> dict[str, tuple[UserId, UserRole]]:
        """Return mapping of GamePlayer.id -> (owner_user_id, owner_user_role).

        This avoids async lazy-loading issues in routers by resolving owner info via joins.
        """
        query = (
            select(GamePlayer.id, User.id, User.role)
            .join(AgentVersion, AgentVersion.id == GamePlayer.agent_version_id)
            .join(User, User.id == AgentVersion.user_id)
            .where(GamePlayer.game_id == game_id)
        )
        result = await db.execute(query)
        mapping: dict[str, tuple[UserId, UserRole]] = {}
        for gp_id, user_id, role in result.all():
            mapping[str(gp_id)] = (user_id, role)
        return mapping

    # Matchmaking-specific methods

    async def join_game_atomically(
        self,
        db: AsyncSession,
        game_id: GameId,
        agent_version_id: AgentVersionId,
        user_id: UserId,
        env: GameType,
        *,
        is_system_player: bool = False,
    ) -> tuple[JoinResult, GamePlayer | None, int]:
        """Attempt to join a game with proper locking and version bump.

        Returns (result, game_player, new_count)
        - JOINED: player was added, game_player is the new row
        - ALREADY_JOINED: player already present (active), returns existing row
        - FULL: no slot available, returns (FULL, None, current_count)
        """
        # Lock the game row to prevent races
        game_row = await db.execute(select(Game).where(Game.id == game_id).with_for_update())
        game = game_row.scalar_one_or_none()
        if not game:
            return (JoinResult.FULL, None, 0)

        # Check if player already active in this game
        existing_q = await db.execute(
            select(GamePlayer).where(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.agent_version_id == agent_version_id,
                    GamePlayer.leave_time.is_(None),
                )
            )
        )
        existing_player = existing_q.scalar_one_or_none()
        if existing_player:
            return (JoinResult.ALREADY_JOINED, existing_player, game.current_player_count or 0)

        # Enforce capacity if max_players is set
        max_allowed = game.max_players_allowed or 0
        current_count = game.current_player_count or 0
        if max_allowed and current_count >= max_allowed:
            return (JoinResult.FULL, None, current_count)

        # Create participant
        participant = GamePlayer(
            id=TSID.create(),
            game_id=game_id,
            agent_version_id=agent_version_id,
            user_id=user_id,
            env=env,
            join_time=get_now(),
            is_system_player=is_system_player,
        )
        db.add(participant)
        # Increment counters and bump version
        _ = await db.execute(
            update(Game)
            .where(Game.id == game_id)
            .values(
                current_player_count=(Game.current_player_count + 1),
                version=Game.version + 1,
            )
        )

        # Optionally, return the participant with relationships
        await db.flush()

        # Compute new count locally to avoid an extra SELECT
        new_count = current_count + 1
        return (JoinResult.JOINED, participant, new_count)

    async def find_open_games(
        self,
        db: AsyncSession,
        game_type: GameType,
        exclude_user_id: UserId | None = None,
    ) -> list[Game]:
        """Find games in waiting status that aren't full.

        Args:
            db: Database session
            game_type: Type of game to find
            exclude_user_id: Exclude games where this user already has an agent

        Returns:
            List of open games, ordered by player count (fullest first)
        """
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .filter(
                and_(
                    Game.game_type == game_type,
                    Game.matchmaking_status == MatchmakingStatus.WAITING,
                    Game.waiting_deadline > datetime.now(UTC),
                    Game.current_player_count < Game.max_players_allowed,
                )
            )
            .order_by(Game.current_player_count.desc())  # Fill fuller games first
        )

        result = await db.execute(query)
        games = list(result.scalars().all())

        # Filter out games where user already has an agent
        if exclude_user_id:
            games = [g for g in games if not any(gp.user_id == exclude_user_id and gp.leave_time is None for gp in g.game_players)]

        return games

    async def find_discoverable_games(
        self,
        db: AsyncSession,
        statuses: list[MatchmakingStatus],
        allowed_game_types: list[GameType],
        limit: int = 50,
        offset: int = 0,
    ) -> list[Game]:
        """Find public/spectatable games for discovery lists.

        Returns non-playground games matching provided statuses and allowed environments.
        Ordered by most recently started, then by id desc.
        """
        if not statuses:
            return []
        query = (
            select(Game)
            .filter(
                and_(
                    Game.is_playground.is_(False),
                    Game.game_type.in_(allowed_game_types),
                    Game.matchmaking_status.in_(statuses),
                )
            )
            .order_by(Game.started_at.desc(), Game.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create_waiting_game_with_first_player(
        self,
        db: AsyncSession,
        *,
        game_id: GameId,
        game_type: GameType,
        config_dict: dict[str, Any],
        requesting_user_id: UserId,
        waiting_deadline: datetime,
        allows_midgame_joining: bool,
        min_players_required: int,
        max_players_allowed: int,
        first_agent_version_id: AgentVersionId,
        first_user_id: UserId,
        is_system_player: bool = False,
    ) -> Game:
        """Create a WAITING game and insert the first player in a single method.

        The initial state is empty ({}). Version starts at 0.
        """
        # Create Game row
        game = Game(
            id=game_id,
            game_type=game_type,
            state={},
            config=config_dict,
            requesting_user_id=requesting_user_id,
            matchmaking_status=MatchmakingStatus.WAITING,
            waiting_deadline=waiting_deadline,
            allows_midgame_joining=allows_midgame_joining,
            current_player_count=1,
            min_players_required=min_players_required,
            max_players_allowed=max_players_allowed,
            is_playground=False,
        )
        db.add(game)

        # Create first GamePlayer
        player = GamePlayer(
            id=TSID.create(),
            game_id=game_id,
            agent_version_id=first_agent_version_id,
            user_id=first_user_id,
            env=game_type,
            join_time=get_now(),
            is_system_player=is_system_player,
        )
        db.add(player)

        # Flush so the rows are visible to subsequent queries
        await db.flush()

        # Return the ORM instance (relationships can be refreshed by caller)
        return game

    async def find_timed_out_games(self, db: AsyncSession) -> list[Game]:
        """Find games whose waiting deadline has passed.

        Returns:
            List of games that have timed out
        """
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .filter(
                and_(
                    Game.matchmaking_status == MatchmakingStatus.WAITING,
                    Game.waiting_deadline <= datetime.now(UTC),
                )
            )
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_user_waiting_game(
        self,
        db: AsyncSession,
        user_id: UserId,
        agent_version_id: AgentVersionId,
    ) -> Game | None:
        """Get any active game (WAITING or IN_PROGRESS) for a specific agent."""
        query = (
            select(Game)
            .options(
                selectinload(Game.game_players).joinedload(GamePlayer.agent_version).joinedload(AgentVersion.agent),
                selectinload(Game.game_players).joinedload(GamePlayer.user),
                selectinload(Game.events),
            )
            .join(GamePlayer, Game.id == GamePlayer.game_id)
            .filter(
                and_(
                    GamePlayer.user_id == user_id,
                    GamePlayer.agent_version_id == agent_version_id,
                    GamePlayer.leave_time.is_(None),
                    Game.matchmaking_status.in_([MatchmakingStatus.WAITING, MatchmakingStatus.IN_PROGRESS]),
                )
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_player_count(self, db: AsyncSession, game_id: GameId) -> int:
        """Update the current player count for a game and return the value.

        Args:
            db: Database session
            game_id: Game ID

        Returns:
            Number of active players still in the game.
        """
        # Count active players (leave_time is NULL)
        count_query = select(func.count(GamePlayer.id)).filter(
            and_(
                GamePlayer.game_id == game_id,
                GamePlayer.leave_time.is_(None),
            )
        )
        result = await db.execute(count_query)

        count = int(result.scalar() or 0)

        # Update the game
        _ = await db.execute(update(Game).where(Game.id == game_id).values(current_player_count=count))

        return count

    async def get_player_agent_ids(self, db: AsyncSession, game_id: GameId) -> list[AgentVersionId]:
        """Get all agent version IDs for players in a game.

        Args:
            db: Database session
            game_id: Game ID

        Returns:
            List of agent version IDs
        """
        query = select(GamePlayer.agent_version_id).filter(
            and_(
                GamePlayer.game_id == game_id,
                GamePlayer.leave_time.is_(None),  # Only active players
            )
        )
        result = await db.execute(query)

        return list(result.scalars().all())

    async def bump_version(self, db: AsyncSession, game_id: GameId) -> None:
        """Increment the version without changing other fields (notify pollers)."""
        _ = await db.execute(update(Game).where(Game.id == game_id).values(version=Game.version + 1))

    async def get_game_players(self, db: AsyncSession, game_id: GameId, include_inactive: bool = False) -> list[GamePlayer]:
        """Get game players for a game.

        Args:
            db: AsyncSession
            game_id: Game ID
            include_inactive: If True, include players who have left (leave_time is not None)

        Returns:
            List of GamePlayer objects
        """
        if include_inactive:
            # Get all players regardless of leave_time
            query = select(GamePlayer).filter(GamePlayer.game_id == game_id)
        else:
            # Get only active players (leave_time is NULL)
            query = select(GamePlayer).filter(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.leave_time.is_(None),
                )
            )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def add_events(self, db: AsyncSession, game_id: GameId, events: list[BaseGameEvent]) -> None:
        """Add game events to the database (no version bump)."""
        from common.utils.utils import get_logger

        logger = get_logger()

        for event in events:
            event_class_name = type(event).__name__

            # Log reasoning events BEFORE serialization
            if event_class_name == "AgentReasoningEvent":
                # Check if event has tool_calls attribute
                tool_calls_attr = getattr(event, "tool_calls", None)
                logger.info(
                    "Reasoning event BEFORE serialization",
                    game_id=game_id,
                    event_class_name=event_class_name,
                    has_tool_calls_attr=tool_calls_attr is not None,
                    tool_calls_attr_value=tool_calls_attr,
                    tool_calls_count=len(tool_calls_attr) if tool_calls_attr else 0,
                    event_repr=repr(event),
                )

            event_data = event.to_dict(mode="json")

            # Log reasoning events AFTER serialization
            if event_class_name == "AgentReasoningEvent":
                logger.info(
                    "Reasoning event AFTER serialization",
                    game_id=game_id,
                    event_class_name=event_class_name,
                    event_type_field=event_data.get("type"),
                    has_tool_calls="tool_calls" in event_data or "toolCalls" in event_data,
                    tool_calls_count=len(event_data.get("tool_calls", event_data.get("toolCalls", []))),
                    event_data_keys=list(event_data.keys()),
                    event_data=event_data,
                )

            game_event = GameEvent(
                id=TSID.create(),
                game_id=game_id,
                type=event_class_name,
                data=event_data,
                created_at=get_now(),
            )
            db.add(game_event)

    # --- Versioned mutation helpers (A2) ---

    async def set_status(self, db: AsyncSession, game_id: GameId, status: MatchmakingStatus) -> None:
        """Set matchmaking status and bump version atomically."""
        _ = await db.execute(update(Game).where(Game.id == game_id).values(matchmaking_status=status, version=Game.version + 1))

    async def add_events_without_bumping_version(self, db: AsyncSession, game_id: GameId, events: list[BaseGameEvent]) -> None:
        """Append events without bumping game version in one transaction."""
        # Insert events without bumping version
        for event in events:
            game_event = GameEvent(
                id=TSID.create(),
                game_id=game_id,
                type=type(event).__name__,
                data=event.to_dict(mode="json"),
                created_at=get_now(),
            )
            db.add(game_event)

    async def find_old_waiting_games(self, db: AsyncSession, cutoff_time: datetime) -> list[Game]:
        """Find WAITING games created before cutoff_time."""
        query = select(Game).where(
            and_(
                Game.matchmaking_status == MatchmakingStatus.WAITING,
                Game.created_at < cutoff_time,
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def cancel_old_waiting_games(self, db: AsyncSession, cutoff_time: datetime) -> int:
        """Mark old WAITING games as CANCELLED instead of deleting them.

        Returns number of games cancelled.
        """
        stmt = (
            update(Game)
            .where(
                and_(
                    Game.matchmaking_status == MatchmakingStatus.WAITING,
                    Game.created_at < cutoff_time,
                )
            )
            .values(
                matchmaking_status=MatchmakingStatus.CANCELLED,
                version=Game.version + 1,
            )
        )
        result = await db.execute(stmt)
        return int(result.rowcount or 0)
