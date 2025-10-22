"""Chess move analysis service using Stockfish and LLM."""

import asyncio
from typing import cast

import chess
import chess.engine
from chess_game.chess_api import ChessState, MoveAnalysisEvent
from game_api import BaseGameState
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_integration_service import LLMIntegrationService
from common.core.litellm_schemas import ChatMessage, MessageRole
from common.core.litellm_service import LiteLLMConfig, LiteLLMService
from common.enums import LLMProvider
from common.ids import GameId, PlayerId, UserId
from common.utils import JsonModel
from common.utils.utils import get_logger
from shared_db.crud.game import GameDAO
from shared_db.models.llm_enums import get_default_model_for_provider
from shared_db.schemas.llm_integration import LLMIntegrationWithKey

logger = get_logger(__name__)


class StockfishAnalysisResult(JsonModel):
    """Result from Stockfish analysis."""

    score_cp: int | None = Field(default=None, description="Position evaluation in centipawns")
    score_mate: int | None = Field(default=None, description="Mate in N moves")
    score_before_cp: int | None = Field(default=None, description="Evaluation before move")
    evaluation_change: int | None = Field(default=None, description="Change in evaluation")
    best_move_san: str | None = Field(default=None, description="Best move in SAN notation")


class MoveQualityClassification(JsonModel):
    """Classification of move quality."""

    is_blunder: bool = Field(default=False, description="Move loses significant advantage (>300cp)")
    is_mistake: bool = Field(default=False, description="Move loses moderate advantage (100-300cp)")
    is_inaccuracy: bool = Field(default=False, description="Move loses small advantage (50-100cp)")
    is_brilliant: bool = Field(default=False, description="Exceptional move that improves position significantly")
    is_good: bool = Field(default=False, description="Good move that improves position")


class ChessAnalysisService:
    """Service for analyzing chess moves using Stockfish and LLM."""

    def __init__(
        self,
        litellm_service: LiteLLMService,
        game_dao: GameDAO,
        llm_integration_service: LLMIntegrationService,
        stockfish_path: str = "stockfish",
        analysis_depth: int = 15,
        time_limit: float = 1.0,
        enabled: bool = True,
    ) -> None:
        self.litellm_service = litellm_service
        self.game_dao = game_dao
        self.llm_integration_service = llm_integration_service
        self.stockfish_path = stockfish_path
        self.analysis_depth = analysis_depth
        self.time_limit = time_limit
        self.enabled = enabled

    async def analyze_move(
        self,
        db: AsyncSession,
        game_id: GameId,
        round_number: int,
        player_id: PlayerId,
        move_san: str,
        state_before: BaseGameState,
        state_after: BaseGameState,
    ) -> None:
        """Analyze a chess move and store the analysis event.

        Args:
            db: Database session
            game_id: Game ID
            round_number: Round number
            player_id: Player ID
            move_san: Move in SAN notation
            state_before: Game state before the move
            state_after: Game state after the move
        """
        if not self.enabled:
            logger.info("Chess analysis disabled, skipping")
            return

        # Extract FEN strings from chess states
        state_before_chess = cast(ChessState, state_before)
        state_after_chess = cast(ChessState, state_after)

        try:
            # Fetch requesting user ID for LLM integration
            requesting_user_id = await self.game_dao.get_requesting_user_id(db, game_id)
            if requesting_user_id is None:
                logger.warning(f"Game {game_id} not found, skipping analysis")
                return

            integration: LLMIntegrationWithKey | None = None
            try:
                integration_response = await self.llm_integration_service.get_user_default_integration(db, requesting_user_id)
                if integration_response:
                    integration = await self.llm_integration_service.get_integration_for_use(db, integration_response.id)
            except Exception:
                logger.exception(
                    "Failed to load user LLM integration",
                    extra={"user_id": str(requesting_user_id)},
                )

            if integration is None:
                logger.warning(f"No LLM integration found for user {requesting_user_id}, using fallback")

            logger.info(
                "Starting chess move analysis",
                extra={
                    "game_id": str(game_id),
                    "round_number": round_number,
                    "move_san": move_san,
                },
            )

            # Run Stockfish analysis in thread pool (CPU-bound)
            analysis = await asyncio.to_thread(
                self._run_stockfish_analysis,
                fen_before=state_before_chess.fen,
                fen_after=state_after_chess.fen,
            )

            # Generate narrative using LLM
            narrative = await self._generate_narrative(
                analysis=analysis,
                move_san=move_san,
                integration=integration,
                requesting_user_id=requesting_user_id,
            )

            # Classify move quality
            classification = self._classify_move(analysis)

            # Create analysis event
            event = MoveAnalysisEvent(
                turn=round_number,
                round_number=round_number,
                player_id=player_id,
                move_san=move_san,
                evaluation_cp=analysis.score_cp,
                evaluation_mate=analysis.score_mate,
                best_move_san=analysis.best_move_san,
                narrative=narrative,
                is_blunder=classification.is_blunder,
                is_mistake=classification.is_mistake,
                is_inaccuracy=classification.is_inaccuracy,
                is_brilliant=classification.is_brilliant,
                is_good=classification.is_good,
            )

            # Store in database and bump version to notify long-polling clients
            await self.game_dao.add_events_without_bumping_version(db, game_id, [event])

            logger.info(
                "Chess move analysis completed and stored",
                extra={
                    "game_id": str(game_id),
                    "move_san": move_san,
                    "evaluation_cp": analysis.score_cp,
                    "classification": classification.model_dump(),
                    "round_number": round_number,
                },
            )

        except Exception:
            logger.exception(
                "Failed to analyze chess move",
                extra={"game_id": str(game_id), "move_san": move_san},
            )
            raise

    def _run_stockfish_analysis(self, fen_before: str, fen_after: str) -> StockfishAnalysisResult:
        """Run Stockfish analysis (blocking, should be called in thread pool)."""
        try:
            # Create board from FEN
            board_before = chess.Board(fen_before)
            board_after = chess.Board(fen_after)

            # Initialize Stockfish engine
            with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
                # Analyze position before move
                info_before = engine.analyse(
                    board_before,
                    chess.engine.Limit(depth=self.analysis_depth, time=self.time_limit),
                )

                # Analyze position after move
                info_after = engine.analyse(
                    board_after,
                    chess.engine.Limit(depth=self.analysis_depth, time=self.time_limit),
                )

                # Get best move from before position
                result = engine.play(
                    board_before,
                    chess.engine.Limit(depth=self.analysis_depth, time=self.time_limit),
                )
                best_move = result.move

                # Extract scores
                score_before = info_before.get("score")
                score_after = info_after.get("score")

                # Convert scores to centipawns (from perspective of side to move)
                score_before_cp = self._score_to_cp(score_before, board_before.turn)
                score_after_cp = self._score_to_cp(score_after, board_after.turn)

                # Calculate evaluation change (only if both scores are available)
                evaluation_change: int | None = None
                if score_after_cp is not None and score_before_cp is not None:
                    evaluation_change = score_after_cp - score_before_cp

                return StockfishAnalysisResult(
                    score_cp=score_after_cp,
                    score_mate=self._extract_mate_score(score_after),
                    score_before_cp=score_before_cp,
                    evaluation_change=evaluation_change,
                    best_move_san=board_before.san(best_move) if best_move else None,
                )

        except Exception:
            logger.exception("Stockfish analysis failed")
            return StockfishAnalysisResult(
                score_cp=None,
                score_mate=None,
                score_before_cp=None,
                evaluation_change=None,
                best_move_san=None,
            )

    def _score_to_cp(self, score: chess.engine.PovScore | None, turn: bool) -> int | None:
        """Convert Stockfish score to centipawns from perspective of side to move."""
        if score is None:
            return None

        # Get score relative to white
        white_score = score.white()

        # If it's a mate score, convert to large centipawn value
        if white_score.is_mate():
            mate_in = white_score.mate()
            if mate_in is None:
                return None
            # Positive mate = white wins, negative = black wins
            # Convert to large centipawn value (10000 per mate)
            cp_value = 10000 if mate_in > 0 else -10000
        else:
            cp_value = white_score.score()
            if cp_value is None:
                return None

        # Flip sign if it's black's turn
        return cp_value if turn == chess.WHITE else -cp_value

    def _extract_mate_score(self, score: chess.engine.PovScore | None) -> int | None:
        """Extract mate-in-N value from score."""
        if score is None:
            return None

        white_score = score.white()
        if white_score.is_mate():
            return white_score.mate()

        return None

    async def _generate_narrative(
        self,
        analysis: StockfishAnalysisResult,
        move_san: str,
        integration: LLMIntegrationWithKey | None,
        requesting_user_id: UserId,
    ) -> str:
        """Generate human-readable narrative using LLM (fast model, 500 tokens max)."""
        try:
            if not integration:
                return self._generate_fallback_narrative(analysis, move_san)

            # Build prompt
            prompt = self._build_analysis_prompt(analysis, move_san)

            # Use FAST model for quick analysis
            fast_model = get_default_model_for_provider(LLMProvider(integration.provider))

            # Create config with token limit
            config = LiteLLMConfig(
                max_tokens=500,  # Limit to 500 tokens for speed
                temperature=0.7,  # Slightly creative but focused
            )

            # Call LLM - pass API key directly for all providers (including Bedrock)
            response = await self.litellm_service.chat_completion(
                provider=LLMProvider(integration.provider),
                model=fast_model,
                messages=[ChatMessage(role=MessageRole.USER, content=prompt)],
                api_key=integration.api_key,
                output_type=str,
                config=config,
            )

            # Handle None or empty content
            if not response.content:
                logger.warning("LLM returned empty content for analysis narrative", extra={"user_id": requesting_user_id})
                return self._generate_fallback_narrative(analysis, move_san)

            return response.content.strip()

        except Exception:
            logger.exception("Failed to generate analysis narrative", extra={"user_id": requesting_user_id})
            return self._generate_fallback_narrative(analysis, move_san)

    def _build_analysis_prompt(self, analysis: StockfishAnalysisResult, move_san: str) -> str:
        """Build engaging prompt for LLM - optimized for concise output."""
        eval_change = analysis.evaluation_change
        score_cp = analysis.score_cp
        best_move = analysis.best_move_san

        prompt = f"""You are a chess commentator. Analyze this move in 2-3 SHORT sentences (max 100 words).

Move played: {move_san}
"""

        if score_cp is not None:
            prompt += f"Position evaluation: {score_cp / 100:.2f} pawns\n"

        if eval_change is not None:
            prompt += f"Evaluation change: {eval_change / 100:+.2f} pawns\n"

        if best_move and best_move != move_san:
            prompt += f"Best move was: {best_move}\n"

        prompt += """
Be concise and engaging. Classify the move (blunder/mistake/inaccuracy/good/brilliant) and explain why briefly.
Example: "Nf3 is a solid developing move (+0.15). However, e4 would have been stronger (+0.50), seizing more central space. This is a minor inaccuracy."
"""

        return prompt

    def _generate_fallback_narrative(self, analysis: StockfishAnalysisResult, move_san: str) -> str:
        """Generate basic narrative without LLM."""
        score_cp = analysis.score_cp
        eval_change = analysis.evaluation_change
        best_move = analysis.best_move_san

        # Simple template-based narrative
        if eval_change is not None:
            if eval_change < -300:
                quality = "a blunder"
            elif eval_change < -100:
                quality = "a mistake"
            elif eval_change < -50:
                quality = "an inaccuracy"
            elif eval_change >= 50:
                quality = "a good move"
            else:
                quality = "a reasonable move"
        else:
            quality = "a move"

        narrative = f"{move_san} is {quality}."

        if score_cp is not None:
            narrative += f" Position evaluation: {score_cp / 100:.2f}"

        if best_move and best_move != move_san:
            narrative += f". Best move was {best_move}."

        return narrative

    def _classify_move(self, analysis: StockfishAnalysisResult) -> MoveQualityClassification:
        """Classify move quality based on evaluation change."""
        eval_change = analysis.evaluation_change

        if eval_change is None:
            return MoveQualityClassification(
                is_blunder=False,
                is_mistake=False,
                is_inaccuracy=False,
                is_brilliant=False,
                is_good=False,
            )

        return MoveQualityClassification(
            is_blunder=eval_change < -300,
            is_mistake=-300 <= eval_change < -100,
            is_inaccuracy=-100 <= eval_change < -50,
            is_brilliant=eval_change >= 200,
            is_good=50 <= eval_change < 200,
        )
