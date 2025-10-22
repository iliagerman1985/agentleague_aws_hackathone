from __future__ import annotations

from datetime import timedelta

from game_api import GameType

from app.schemas.sqs_game_messages import GameAnalysisMessage, GameAnalysisSqsClient, GameTurnMessage, GameTurnSqsClient
from app.services.agent_execution_service import AgentExecutionService
from app.services.agent_runner_factory import AgentRunnerFactory
from app.services.chess_analysis_service import ChessAnalysisService
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_manager import GameManager
from app.services.game_matching_service import GameMatchingService
from app.services.llm_integration_service import LLMIntegrationService
from app.services.poker_analysis_service import PokerAnalysisService
from app.services.scoring_service import ScoringService
from app.services.sqs_game_analysis_handler import AnalysisServiceProtocol, SqsGameAnalysisHandler
from app.services.sqs_game_turn_handler import SqsGameTurnHandler
from common.core.aws_manager import AwsManager
from common.core.config_service import ConfigService
from common.core.lifecycle import Lifecycle
from common.core.litellm_service import LiteLLMService
from common.core.sqs_client import SqsClient, SqsClientConfig, SqsMessage
from common.utils.utils import cached_classmethod, get_logger
from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO, AgentVersionDAO
from shared_db.crud.game import GameDAO
from shared_db.crud.llm_integration import LLMIntegrationDAO
from shared_db.crud.tool import ToolDAO
from shared_db.crud.user import UserDAO

logger = get_logger()


class Services(Lifecycle):
    aws_manager: AwsManager
    config_service: ConfigService

    game_dao: GameDAO
    agent_dao: AgentDAO
    agent_version_dao: AgentVersionDAO
    agent_statistics_dao: AgentStatisticsDAO
    tool_dao: ToolDAO
    llm_integration_dao: LLMIntegrationDAO
    user_dao: UserDAO

    litellm_service: LiteLLMService
    llm_integration_service: LLMIntegrationService
    chess_analysis_service: ChessAnalysisService

    game_env_registry: GameEnvRegistry
    game_manager: GameManager
    scoring_service: ScoringService
    agent_execution_service: AgentExecutionService
    sqs_game_turn_handler: SqsGameTurnHandler
    sqs_game_analysis_handler: SqsGameAnalysisHandler

    game_turn_sqs_client: GameTurnSqsClient
    game_analysis_sqs_client: GameAnalysisSqsClient

    game_matching_service: GameMatchingService

    def __init__(self) -> None:
        super().__init__()

        # Initialize core infrastructure
        self.aws_manager = self._create_aws_manager()
        self.config_service = self._create_config_service()

        # Initialize database access objects
        self.game_dao = self._create_game_dao()
        self.agent_dao = self._create_agent_dao()
        self.agent_version_dao = self._create_agent_version_dao()
        self.agent_statistics_dao = self._create_agent_statistics_dao()
        self.tool_dao = self._create_tool_dao()
        self.user_dao = self._create_user_dao()
        self.llm_integration_dao = self._create_llm_integration_dao()

        # Initialize LLM services
        self.litellm_service = self._create_litellm_service()
        self.llm_integration_service = self._create_llm_integration_service(litellm_service=self.litellm_service, llm_integration_dao=self.llm_integration_dao)

        # Initialize game-specific analysis services
        self.chess_analysis_service = self._create_chess_analysis_service(
            litellm_service=self.litellm_service,
            game_dao=self.game_dao,
            llm_integration_service=self.llm_integration_service,
            config_service=self.config_service,
        )
        self.poker_analysis_service = self._create_poker_analysis_service(config_service=self.config_service)

        # Initialize game services
        self.game_env_registry = self._create_game_env_registry()
        self.scoring_service = self._create_scoring_service(
            agent_dao=self.agent_dao, agent_statistics_dao=self.agent_statistics_dao, game_dao=self.game_dao, user_dao=self.user_dao
        )
        self.agent_execution_service = self._create_agent_execution_service(litellm_service=self.litellm_service)

        # Initialize SQS services
        self.game_turn_sqs_client = self._create_game_turn_sqs_client(aws_manager=self.aws_manager, config_service=self.config_service)
        self.game_analysis_sqs_client = self._create_game_analysis_sqs_client(aws_manager=self.aws_manager, config_service=self.config_service)

        # Create the SQS game analysis handler with all available analysis services
        self.sqs_game_analysis_handler = self._create_sqs_game_analysis_handler(
            sqs_client=self.game_analysis_sqs_client,
            game_dao=self.game_dao,
            analysis_services={
                GameType.CHESS: self.chess_analysis_service,
                GameType.TEXAS_HOLDEM: self.poker_analysis_service,
            },
        )

        # Now create game_manager
        self.game_manager = self._create_game_manager(
            game_env_registry=self.game_env_registry,
            agent_execution_service=self.agent_execution_service,
            game_dao=self.game_dao,
            agent_version_dao=self.agent_version_dao,
            agent_statistics_dao=self.agent_statistics_dao,
            tool_dao=self.tool_dao,
            llm_integration_service=self.llm_integration_service,
            scoring_service=self.scoring_service,
            sqs_game_analysis_handler=self.sqs_game_analysis_handler,
        )

        # Create the SQS game turn handler
        self.sqs_game_turn_handler = self._create_sqs_game_turn_handler(sqs_client=self.game_turn_sqs_client, game_manager=self.game_manager)

        # Create the game matching service
        self.game_matching_service = self._create_game_matching_service(
            game_dao=self.game_dao,
            agent_dao=self.agent_version_dao,
            game_manager=self.game_manager,
            user_dao=self.user_dao,
            sqs_game_turn_handler=self.sqs_game_turn_handler,
        )

    async def _start(self) -> None:
        await self.aws_manager.start()
        await self.game_turn_sqs_client.start()
        await self.game_analysis_sqs_client.start()

    async def _stop(self) -> None:
        await self.game_analysis_sqs_client.stop()
        await self.game_turn_sqs_client.stop()
        await self.aws_manager.stop()

    # Protected creation methods for dependency injection/overriding
    def _create_aws_manager(self) -> AwsManager:
        return AwsManager()

    def _create_config_service(self) -> ConfigService:
        return ConfigService()

    def _create_game_dao(self) -> GameDAO:
        return GameDAO()

    def _create_agent_dao(self) -> AgentDAO:
        return AgentDAO()

    def _create_agent_version_dao(self) -> AgentVersionDAO:
        return AgentVersionDAO()

    def _create_agent_statistics_dao(self) -> AgentStatisticsDAO:
        return AgentStatisticsDAO()

    def _create_tool_dao(self) -> ToolDAO:
        return ToolDAO()

    def _create_user_dao(self) -> UserDAO:
        return UserDAO()

    def _create_llm_integration_dao(self) -> LLMIntegrationDAO:
        return LLMIntegrationDAO()

    def _create_litellm_service(self) -> LiteLLMService:
        return LiteLLMService()

    def _create_llm_integration_service(self, litellm_service: LiteLLMService, llm_integration_dao: LLMIntegrationDAO) -> LLMIntegrationService:
        return LLMIntegrationService(llm_integration_dao=llm_integration_dao, litellm_service=litellm_service)

    def _create_chess_analysis_service(
        self, litellm_service: LiteLLMService, game_dao: GameDAO, llm_integration_service: LLMIntegrationService, config_service: ConfigService
    ) -> ChessAnalysisService:
        stockfish_path = config_service.get("chess.stockfish_path", "stockfish")
        analysis_depth = config_service.get("chess.stockfish_analysis_depth", 15)
        time_limit = config_service.get("chess.stockfish_analysis_time_limit", 1.0)
        enabled = config_service.get("chess.enable_chess_analysis", True)

        return ChessAnalysisService(
            litellm_service=litellm_service,
            game_dao=game_dao,
            llm_integration_service=llm_integration_service,
            stockfish_path=stockfish_path,
            analysis_depth=analysis_depth,
            time_limit=time_limit,
            enabled=enabled,
        )

    def _create_poker_analysis_service(self, config_service: ConfigService) -> PokerAnalysisService:
        """Create poker analysis service.

        Args:
            config_service: Configuration service

        Returns:
            Poker analysis service instance
        """
        enabled = config_service.get("ENABLE_POKER_ANALYSIS", "false").lower() == "true"
        return PokerAnalysisService(enabled=enabled)

    def _create_game_env_registry(self) -> GameEnvRegistry:
        return GameEnvRegistry.instance()

    def _create_scoring_service(self, agent_dao: AgentDAO, agent_statistics_dao: AgentStatisticsDAO, game_dao: GameDAO, user_dao: UserDAO) -> ScoringService:
        return ScoringService(agent_dao=agent_dao, agent_statistics_dao=agent_statistics_dao, game_dao=game_dao, user_dao=user_dao)

    def _create_agent_execution_service(self, litellm_service: LiteLLMService) -> AgentExecutionService:
        return AgentExecutionService(litellm_service=litellm_service)

    def _create_game_manager(
        self,
        game_env_registry: GameEnvRegistry,
        agent_execution_service: AgentExecutionService,
        game_dao: GameDAO,
        agent_version_dao: AgentVersionDAO,
        agent_statistics_dao: AgentStatisticsDAO,
        tool_dao: ToolDAO,
        llm_integration_service: LLMIntegrationService,
        scoring_service: ScoringService,
        sqs_game_analysis_handler: SqsGameAnalysisHandler,
    ) -> GameManager:
        agent_runner = AgentRunnerFactory.create_runner(agent_execution_service)

        return GameManager(
            registry=game_env_registry,
            agent_execution_service=agent_execution_service,
            game_dao=game_dao,
            agent_version_dao=agent_version_dao,
            agent_statistics_dao=agent_statistics_dao,
            tool_dao=tool_dao,
            llm_integration_service=llm_integration_service,
            agent_runner=agent_runner,
            scoring_service=scoring_service,
            sqs_game_analysis_handler=sqs_game_analysis_handler,
        )

    def _create_sqs_game_turn_handler(
        self,
        sqs_client: GameTurnSqsClient,
        game_manager: GameManager,
    ) -> SqsGameTurnHandler:
        return SqsGameTurnHandler(
            sqs_client=sqs_client,
            game_manager=game_manager,
        )

    def _create_game_matching_service(
        self,
        game_dao: GameDAO,
        agent_dao: AgentVersionDAO,
        game_manager: GameManager,
        user_dao: UserDAO,
        sqs_game_turn_handler: SqsGameTurnHandler,
    ) -> GameMatchingService:
        return GameMatchingService(
            game_dao=game_dao,
            agent_dao=agent_dao,
            game_manager=game_manager,
            user_dao=user_dao,
            sqs_game_turn_handler=sqs_game_turn_handler,
            analysis_handler=self.sqs_game_analysis_handler,
        )

    def _create_game_turn_sqs_client(self, aws_manager: AwsManager, config_service: ConfigService) -> GameTurnSqsClient:
        queue_url = config_service.get("sqs.game_turn_queue_url")
        if not queue_url:
            raise ValueError("GAME_TURN_SQS_QUEUE_URL environment variable is required")

        # Create a producer instance (no poll handler)
        sqs_config = SqsClientConfig(
            name="game_turns",
            queue_url=queue_url,
            visibility_timeout=timedelta(minutes=5),
            wait_time=timedelta(seconds=20),
            max_messages=10,
        )

        return SqsClient[GameTurnMessage](
            aws_manager=aws_manager,
            sqs_message_type=SqsMessage[GameTurnMessage],
            config=sqs_config,
            poll_handler=None,  # No poll handler for sending messages
        )

    def _create_game_analysis_sqs_client(self, aws_manager: AwsManager, config_service: ConfigService) -> GameAnalysisSqsClient:
        queue_url = config_service.get("sqs.game_analysis_queue_url")
        if not queue_url:
            raise ValueError("GAME_ANALYSIS_SQS_QUEUE_URL environment variable is required")

        # Create a producer/consumer instance
        sqs_config = SqsClientConfig(
            name="game_analysis",
            queue_url=queue_url,
            visibility_timeout=timedelta(minutes=5),  # 5 minutes for analysis processing
            wait_time=timedelta(seconds=20),
            max_messages=10,
        )

        return SqsClient[GameAnalysisMessage](
            aws_manager=aws_manager,
            sqs_message_type=SqsMessage[GameAnalysisMessage],
            config=sqs_config,
            poll_handler=None,  # Poll handler will be registered by SqsGameAnalysisHandler
        )

    def _create_sqs_game_analysis_handler(
        self,
        sqs_client: GameAnalysisSqsClient,
        game_dao: GameDAO,
        analysis_services: dict[GameType, AnalysisServiceProtocol],
    ) -> SqsGameAnalysisHandler:
        """Create SQS game analysis handler and register all analysis services.

        Args:
            sqs_client: SQS client for game analysis messages
            game_dao: Game DAO for database access
            analysis_services: Dict mapping game types to their analysis services

        Returns:
            Configured SQS game analysis handler
        """
        handler = SqsGameAnalysisHandler(
            sqs_client=sqs_client,
            game_dao=game_dao,
        )
        # Register all game-specific analysis services
        for game_type, service in analysis_services.items():
            handler.register_analysis_service(game_type, service)
        return handler

    @cached_classmethod
    def instance(cls) -> Services:
        """Get the singleton instance of Services."""
        return Services()
