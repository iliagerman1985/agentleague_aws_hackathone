# backend/app/routers/__init__.py


from fastapi import APIRouter

from app.routers.game import game_router
from app.routers.game_chess import router as chess_router
from app.routers.game_matching import game_matching_router
from app.routers.game_poker import router as poker_router
from app.schemas.health import HealthCheckResponse
from common.core.config_service import ConfigService
from common.core.logging_service import get_logger

from .agents import agents_router
from .auth import auth_router
from .avatars import avatar_router
from .billing import router as billing_router
from .dev import dev_router
from .error_reports import error_reports_router
from .llm_integrations import router as llm_integrations_router
from .tool_creation_agent import router as tool_creation_agent_router
from .tools import tools_router

logger = get_logger(__name__)

config_service = ConfigService()

router = APIRouter()


# Health check endpoint
@router.get("/api/v1/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for monitoring and testing"""

    # Debug: log effective config values (avoid raw env duplication)
    env_info = {
        "environment": config_service.get_environment(),
        "use_mock_cognito": config_service.use_mock_cognito(),
        "is_testing": config_service.is_testing(),
        "effective_database_url": config_service.get_database_url(),
    }
    try:
        logger.info("[HEALTH DEBUG] Config info", extra=env_info)
    except Exception:
        pass

    return HealthCheckResponse(
        status="healthy",
        service="backend",
        environment=config_service.get_environment(),
        use_mock_cognito=config_service.use_mock_cognito(),
        is_testing=config_service.is_testing(),
        database_type="sqlite" if config_service.get_database_url().startswith("sqlite") else "postgresql",
    )


# Include route definitions
router.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
router.include_router(llm_integrations_router, prefix="/api/v1", tags=["llm-integrations"])
router.include_router(tools_router, prefix="/api/v1", tags=["tools"])
router.include_router(tool_creation_agent_router, prefix="/api/v1", tags=["tool-creation-agent"])
router.include_router(agents_router, prefix="/api/v1", tags=["agents"])
router.include_router(avatar_router, prefix="/api/v1", tags=["avatars"])
# Split per-environment game routes
router.include_router(game_router, prefix="/api/v1", tags=["games"])  # generic game routes
router.include_router(game_matching_router, prefix="/api/v1", tags=["game-matching"])  # matchmaking
router.include_router(chess_router, prefix="/api/v1", tags=["games-chess"])  # chess-specific
router.include_router(poker_router, prefix="/api/v1", tags=["games-poker"])  # poker-specific
router.include_router(billing_router, prefix="/api/v1", tags=["billing"])
router.include_router(dev_router, prefix="/api/v1/dev", tags=["development"])
router.include_router(error_reports_router, prefix="/api/v1", tags=["error-reports"])
