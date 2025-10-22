import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.dependencies import get_current_user
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers import router as api_router
from app.service_container import Services
from app.tasks.matchmaking_worker import start_matchmaking_worker, stop_matchmaking_worker
from app.utils.fastapi_utils import install_exception_handlers
from common.core.config_service import ConfigService, settings
from common.core.request_context import RequestContext
from common.logging import setup_logging
from common.utils.utils import get_logger
from shared_db.db.init_db import init_db
from shared_db.db.populate_db import populate_db
from shared_db.schemas.user import UserResponse

# Load environment variables BEFORE setting up logging
# This ensures LOG_JSON_FORMAT and other logging config is available
env = os.getenv("APP_ENV", "local")
base_dir = Path(__file__).resolve().parent.parent.parent / "libs" / "common"
if env == "local":
    env_file = base_dir / ".env.local"
else:
    env_file = base_dir / f".env.{env}"
if env_file.exists():
    _ = load_dotenv(env_file)

# Initialize logging AFTER loading environment variables
# This ensures structlog's ProcessorFormatter wraps records correctly to avoid 'str has no copy()' errors.
setup_logging()


# Configure logger after logging is set up
logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    # Startup logic
    logger.info("Starting application database setup")

    # Initialize database (create tables, run migrations)
    success = await init_db()
    if success:
        logger.info("Database setup completed successfully", service="database", status="initialized")
    else:
        logger.error("Database setup failed", service="database", status="failed")
        raise RuntimeError("Failed to initialize database")

    # Populate database with system data (idempotent)
    logger.info("Populating database with system data")
    populate_success = await populate_db()
    if populate_success:
        logger.info("Database population completed successfully", service="database", status="populated")
    else:
        logger.warning("Database population failed or skipped", service="database", status="warning")

    # Start matchmaking worker
    logger.info("Starting matchmaking worker")
    await start_matchmaking_worker()

    # Initialize and start services
    services = Services.instance()
    await services.start()

    yield

    # Shutdown logic
    logger.info("Application shutting down")

    # Stop matchmaking worker
    logger.info("Stopping matchmaking worker")
    await stop_matchmaking_worker()

    # Stop services
    await services.stop()


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A FastAPI backend for apartment management and customer service chatbot",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Support Team",
        "url": "http://example.com/contact/",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# 1. Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# 2. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # This is now a property that returns a list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware to set up RequestContext for all requests
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        with RequestContext.context() as request_context:
            request_context.endpoint = str(request.url)
            return await call_next(request)


app.add_middleware(RequestContextMiddleware)


# Custom exception handlers
install_exception_handlers(app)

# Include routers
app.include_router(api_router)


@app.get("/")
async def read_root(_current_user: Annotated[UserResponse, Depends(get_current_user)]) -> dict[str, str]:
    return {"message": "Welcome to the FastAPI application!"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    from common.core.config_service import ConfigService

    config_service = ConfigService()

    # Get host and port from configuration
    host = config_service.get("host", "0.0.0.0")
    port = config_service.get("port", 9998)

    logger.info(
        "Starting application server",
        host=host,
        port=port,
        environment=config_service.get_environment(),
    )

    uvicorn.run(app, host=host, port=port)
