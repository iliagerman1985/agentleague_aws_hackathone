from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.service_container import Services
from app.services.agent_iteration_service import AgentIterationService
from app.services.agent_prompt_service import AgentPromptService
from app.services.agent_service import AgentService
from app.services.agent_test_service import AgentTestService
from app.services.agent_version_service import AgentVersionService
from app.services.avatar_service import AvatarService
from app.services.chess_analysis_service import ChessAnalysisService
from app.services.error_report_service import ErrorReportService
from app.services.game_env_registry import GameEnvRegistry
from app.services.llm_integration_service import LLMIntegrationService
from app.services.payment_service import PaymentService
from app.services.scoring_service import ScoringService
from app.services.sqs_game_analysis_handler import SqsGameAnalysisHandler
from app.services.stripe_service import StripeService
from app.services.tool_creation_agent_service import ToolCreationAgentService
from app.services.tool_service import ToolService
from app.services.user_service import UserService
from common.core.base_llm_service import LLMServiceFactory
from common.core.config_service import ConfigService
from common.core.guardrails_service import GuardrailsService
from common.core.request_context import RequestContext
from common.core.service_factory import get_cognito_service, get_jwt_validator
from common.ids import AgentVersionId
from common.utils.utils import get_logger
from shared_db.crud.agent import AgentDAO, AgentExecutionSessionDAO, AgentIterationHistoryDAO, AgentStatisticsDAO, AgentVersionDAO, TestScenarioDAO
from shared_db.crud.error_report import ErrorReportDAO
from shared_db.crud.game import GameDAO
from shared_db.crud.llm_integration import LLMIntegrationDAO
from shared_db.crud.payments import PaymentLedgerDAO
from shared_db.crud.tool import ToolDAO
from shared_db.db import AsyncSessionLocal
from shared_db.models.agent import AgentVersion
from shared_db.models.user import UserRole
from shared_db.schemas.auth import TokenData
from shared_db.schemas.user import UserResponse

logger = get_logger()
services = Services.instance()

# Security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def get_request_context() -> RequestContext:
    return RequestContext.get()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_user_service() -> UserService:
    """Dependency for UserService instance."""
    return UserService(services.user_dao)


def get_payment_ledger_dao() -> PaymentLedgerDAO:
    """Dependency for PaymentLedgerDAO instance."""
    return PaymentLedgerDAO()


def get_payment_service(
    ledger_dao: PaymentLedgerDAO = Depends(get_payment_ledger_dao),
    user_service: UserService = Depends(get_user_service),
) -> PaymentService:
    """Dependency for PaymentService instance."""
    return PaymentService(ledger_dao, user_service)


def get_error_report_dao() -> ErrorReportDAO:
    """Dependency for ErrorReportDAO instance."""
    return ErrorReportDAO()


def get_error_report_service(
    error_report_dao: ErrorReportDAO = Depends(get_error_report_dao),
) -> ErrorReportService:
    """Dependency for ErrorReportService instance."""
    return ErrorReportService(error_report_dao)


def get_llm_integration_dao() -> LLMIntegrationDAO:
    """Dependency for LLMIntegrationDAO instance."""
    return LLMIntegrationDAO()


def get_llm_integration_service(
    llm_integration_dao: LLMIntegrationDAO = Depends(get_llm_integration_dao),
) -> LLMIntegrationService:
    """Dependency for LLMIntegrationService instance."""
    return LLMIntegrationService(llm_integration_dao, services.litellm_service)


def get_tool_dao() -> ToolDAO:
    """Dependency for ToolDAO instance."""
    return ToolDAO()


def get_tool_service(tool_dao: ToolDAO = Depends(get_tool_dao)) -> ToolService:
    """Dependency for ToolService instance."""
    return ToolService(tool_dao)


def get_agent_dao() -> AgentDAO:
    """Dependency for AgentDAO instance."""
    return AgentDAO()


def get_agent_version_dao() -> AgentVersionDAO:
    """Dependency for AgentVersionDAO instance."""
    return AgentVersionDAO()


def get_test_scenario_dao() -> TestScenarioDAO:
    """Dependency for TestScenarioDAO instance."""
    return TestScenarioDAO()


def get_game_dao() -> GameDAO:
    """Dependency for GameDAO instance."""
    return GameDAO()


def get_guardrails_service() -> GuardrailsService:
    """Dependency for GuardrailsService instance.

    Uses the centralized AwsManager from service container for AWS client management.
    """
    return GuardrailsService(aws_manager=services.aws_manager)


def get_tool_creation_agent_service(
    llm_integration_service: LLMIntegrationService = Depends(get_llm_integration_service),
    guardrails_service: GuardrailsService = Depends(get_guardrails_service),
) -> ToolCreationAgentService:
    """Dependency for ToolCreationAgentService instance.

    The service no longer needs DAO dependencies since the agent doesn't
    interact with the database - it only generates and validates code.
    """

    return ToolCreationAgentService(
        llm_integration_service=llm_integration_service,
        game_env_registry=GameEnvRegistry.instance(),
        guardrails_service=guardrails_service,
    )


def get_agent_statistics_dao() -> AgentStatisticsDAO:
    """Dependency for AgentStatisticsDAO instance."""
    return AgentStatisticsDAO()


def get_execution_session_dao() -> AgentExecutionSessionDAO:
    """Dependency for AgentExecutionSessionDAO instance."""
    return AgentExecutionSessionDAO()


def get_iteration_history_dao() -> AgentIterationHistoryDAO:
    """Dependency for AgentIterationHistoryDAO instance."""
    return AgentIterationHistoryDAO()


# New specialized service dependencies
def get_agent_version_service(
    agent_dao: AgentDAO = Depends(get_agent_dao),
    agent_version_dao: AgentVersionDAO = Depends(get_agent_version_dao),
    guardrails_service: GuardrailsService = Depends(get_guardrails_service),
) -> AgentVersionService:
    """Dependency for AgentVersionService instance."""
    return AgentVersionService(agent_dao, agent_version_dao, guardrails_service)


def get_agent_iteration_service() -> AgentIterationService:
    """Dependency for AgentIterationService instance."""
    return AgentIterationService()


def get_agent_prompt_service(tool_dao: ToolDAO = Depends(get_tool_dao)) -> AgentPromptService:
    """Dependency for AgentPromptService instance."""
    return AgentPromptService(tool_dao)


def get_agent_test_service(
    agent_dao: AgentDAO = Depends(get_agent_dao),
    test_scenario_dao: TestScenarioDAO = Depends(get_test_scenario_dao),
    llm_integration_service: LLMIntegrationService = Depends(get_llm_integration_service),
) -> AgentTestService:
    """Dependency for AgentTestService instance."""
    return AgentTestService(agent_dao, test_scenario_dao, llm_integration_service, services.litellm_service)


def get_agent_service(
    agent_dao: AgentDAO = Depends(get_agent_dao),
    agent_statistics_dao: AgentStatisticsDAO = Depends(get_agent_statistics_dao),
    llm_integration_service: LLMIntegrationService = Depends(get_llm_integration_service),
    # Specialized services
    agent_version_service: AgentVersionService = Depends(get_agent_version_service),
    agent_test_service: AgentTestService = Depends(get_agent_test_service),
    agent_prompt_service: AgentPromptService = Depends(get_agent_prompt_service),
    agent_iteration_service: AgentIterationService = Depends(get_agent_iteration_service),
    guardrails_service: GuardrailsService = Depends(get_guardrails_service),
) -> AgentService:
    """Dependency for AgentService instance."""
    return AgentService(
        agent_dao,
        agent_statistics_dao,
        llm_integration_service,
        services.litellm_service,
        agent_version_service,
        agent_test_service,
        agent_prompt_service,
        agent_iteration_service,
        guardrails_service,
    )


def get_cognito_service_dependency() -> object:
    """Dependency for Cognito service instance (mock or real based on configuration)."""
    svc = get_cognito_service()
    logger = get_logger(__name__)
    try:
        logger.info(f"Resolved Cognito service: {type(svc).__name__}")
    except Exception:
        # Be conservative: logging must not break dependency resolution
        pass
    return svc


# Global service instances for LLM factory
_llm_factory: LLMServiceFactory | None = None


def get_llm_factory() -> LLMServiceFactory:
    """Get global LLM service factory instance."""
    global _llm_factory
    if _llm_factory is None:
        config_service = ConfigService()
        _llm_factory = LLMServiceFactory(config_service)

        # Set the base LiteLLM service
        _llm_factory.set_base_service(services.litellm_service)  # type: ignore

    return _llm_factory


def get_llm_factory_dependency() -> LLMServiceFactory:
    """Dependency for LLM service factory instance."""
    return get_llm_factory()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Dependency to get current user token data from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        jwt_validator = get_jwt_validator()
        token_data = jwt_validator.validate_token(token)

        if token_data.username is None and token_data.user_sub is None:
            raise credentials_exception

        return token_data
    except Exception as e:
        raise credentials_exception from e


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Dependency to get current user from database.
    Returns UserResponse (Pydantic model) instead of SQLAlchemy model.
    """
    user = None

    # Try to find user by cognito_sub first, then by username
    if token_data.user_sub:
        user = await user_service.get_user_by_cognito_sub(db, cognito_sub=token_data.user_sub)

    if not user and token_data.username:
        user = await user_service.get_user_by_username(db, username=token_data.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Dependency to get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """Dependency to get current admin user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def require_role(required_role: UserRole) -> Callable[..., Awaitable[UserResponse]]:
    """Dependency factory to require specific user role."""

    async def role_checker(current_user: UserResponse = Depends(get_current_active_user)) -> UserResponse:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role.value} required",
            )
        return current_user

    return role_checker


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse | None:
    """Dependency to optionally resolve the current user.

    Returns the authenticated user if a valid bearer token is supplied.
    Otherwise returns None without raising.
    """

    if credentials is None:
        return None

    try:
        jwt_validator = get_jwt_validator()
        token_data = jwt_validator.validate_token(credentials.credentials)
    except Exception:
        return None

    if not token_data.user_sub and not token_data.username:
        return None

    user = None
    if token_data.user_sub:
        user = await user_service.get_user_by_cognito_sub(db, cognito_sub=token_data.user_sub)

    if user is None and token_data.username:
        user = await user_service.get_user_by_username(db, username=token_data.username)

    if user is None or not user.is_active:
        return None

    return user


def get_scoring_service(agent_dao: AgentDAO = Depends(get_agent_dao), game_dao: GameDAO = Depends(get_game_dao)) -> ScoringService:
    """Dependency for ScoringService instance."""
    from shared_db.crud.user import UserDAO

    return ScoringService(agent_dao=agent_dao, agent_statistics_dao=AgentStatisticsDAO(), game_dao=game_dao, user_dao=UserDAO())


def get_stripe_service() -> StripeService:
    """Dependency for StripeService instance."""
    config = ConfigService()
    return StripeService(config)


def get_avatar_service() -> AvatarService:
    """Dependency for AvatarService instance."""
    return AvatarService()


def get_chess_analysis_service(
    llm_integration_service: LLMIntegrationService = Depends(get_llm_integration_service),
) -> ChessAnalysisService:
    """Dependency for ChessAnalysisService instance."""
    config = ConfigService()
    return ChessAnalysisService(
        litellm_service=services.litellm_service,
        game_dao=services.game_dao,
        llm_integration_service=llm_integration_service,
        stockfish_path=config.get("STOCKFISH_PATH", "stockfish"),
        analysis_depth=int(config.get("STOCKFISH_ANALYSIS_DEPTH", "15")),
        time_limit=float(config.get("STOCKFISH_ANALYSIS_TIME_LIMIT", "1.0")),
        enabled=config.get("ENABLE_CHESS_ANALYSIS", "true").lower() == "true",
    )


def get_sqs_game_analysis_handler() -> SqsGameAnalysisHandler:
    """Dependency for SqsGameAnalysisHandler instance."""
    return services.sqs_game_analysis_handler


async def get_brain_bot_agent_version(
    db: AsyncSession = Depends(get_db),
) -> AgentVersionId:
    """Dependency to get the Brain bot's agent version ID for playground games."""
    brain_bot_agent_id = 800000000000001007  # PREDEFINED_IDS["agent_chess_stockfish"]

    # Get the latest version of the Brain bot
    result = await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == brain_bot_agent_id, AgentVersion.is_active == True).order_by(AgentVersion.version_number.desc())
    )
    agent_version = result.scalar_one_or_none()

    if agent_version is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Brain bot agent version not found. Please ensure the database has been populated."
        )

    return agent_version.id
