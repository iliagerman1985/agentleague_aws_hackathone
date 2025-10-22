"""Configuration service for the backend application.
Loads configuration from environment variables, AWS Secrets Manager, and secrets file.
"""

import logging
import os
from pathlib import Path
from typing import Any, cast

import boto3
import yaml
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from common.models.provider_models import ProviderConfigData

logger = logging.getLogger(__name__)


class StripeSection(BaseModel):
    api_key: str = ""
    webhook_secret: str = ""
    success_url: str = ""
    cancel_url: str = ""


class AWSCredentials(BaseModel):
    """AWS credentials configuration."""

    access_key_id: str = ""
    secret_access_key: str = ""
    session_token: str = ""
    region: str = "us-east-1"

    def has_credentials(self) -> bool:
        """Check if explicit credentials are provided.

        Returns:
            True if both access_key_id and secret_access_key are provided, False otherwise.
            When False, boto3/aiobotocore will use default credential chain (IAM roles, IRSA, etc.)
        """
        return bool(self.access_key_id and self.secret_access_key)


class ConfigService:
    """Service for loading and accessing application configuration.
    Combines environment variables, AWS Secrets Manager, and secrets from YAML file.
    """

    stripe: StripeSection
    aws: AWSCredentials

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._secrets: dict[str, Any] = {}
        self._aws_secrets: dict[str, Any] = {}

        self.stripe = StripeSection()
        self.aws = AWSCredentials()
        # Determine environment
        self._env = os.getenv("APP_ENV", "local")

        # Load configuration
        self._load_env_file()
        self._load_env_vars()
        self._load_aws_secrets()
        self._load_secrets()

        # Expose typed Stripe configuration as attribute access (self.stripe.api_key, ...)
        self.stripe = StripeSection(
            api_key=str(self.get("stripe.api_key") or ""),
            webhook_secret=str(self.get("stripe.webhook_secret") or ""),
            success_url=str(self.get("stripe.success_url") or ""),
            cancel_url=str(self.get("stripe.cancel_url") or ""),
        )

        # Expose typed AWS credentials as attribute access (self.aws.access_key_id, ...)
        # Priority: secrets.yaml > environment variables > empty (for IAM role fallback)
        self.aws = AWSCredentials(
            access_key_id=str(self.get("aws.access_key_id") or os.getenv("AWS_ACCESS_KEY_ID", "")),
            secret_access_key=str(self.get("aws.secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY", "")),
            session_token=str(self.get("aws.session_token") or os.getenv("AWS_SESSION_TOKEN", "")),
            region=str(os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION", "us-east-1")),
        )

    def _load_env_file(self) -> None:
        """Load the appropriate .env file based on environment"""
        base_dir = Path(__file__).resolve().parent.parent.parent

        # Priority order for environment files:
        # 1. .env.development when APP_ENV=development (AWS dev)
        # 2. .env.local as fallback only for development
        # 3. .env.{environment} for other envs

        # 4. .env (fallback)

        env_files_to_try: list[Path] = []

        if self._env == "local":
            env_files_to_try.append(base_dir / ".env.local")
        else:
            env_files_to_try.append(base_dir / f".env.{self._env}")

        # Generic fallback
        env_files_to_try.append(base_dir / ".env")

        # Load the first existing file
        for env_file in env_files_to_try:
            if env_file.exists():
                logger.info(f"Loading environment from {env_file}")
                _ = load_dotenv(env_file)  # Explicitly ignore return value
                return

        logger.warning("No environment file found. Using default values.")

    def _load_env_vars(self) -> None:
        """Load configuration from environment variables"""
        self._config = {
            "app_env": self._env,
            "debug": os.getenv("DEBUG", "True").lower() in ("true", "1", "t"),
            "api_prefix": os.getenv("API_PREFIX", "/api/v1"),
            "project_name": os.getenv("PROJECT_NAME", "Agent League"),
            "allowed_hosts": os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(
                ",",
            ),
            "cors_origins": os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5888,http://localhost:3000",
            ).split(","),
            "port": int(os.getenv("PORT", "9998")),
            "host": os.getenv("HOST", "0.0.0.0"),
            # Logging configuration
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            # Default to human-readable colorful logs unless explicitly set to True
            "log_json_format": os.getenv("LOG_JSON_FORMAT", "False").lower() in ("true", "1", "t"),
            "log_json_pretty": os.getenv("LOG_JSON_PRETTY", "False").lower() in ("true", "1", "t"),
            "log_console_output": os.getenv("LOG_CONSOLE_OUTPUT", "True").lower() in ("true", "1", "t"),
            "log_file_output": os.getenv("LOG_FILE_OUTPUT", "False").lower() in ("true", "1", "t"),
            "log_file_path": os.getenv("LOG_FILE_PATH", "logs/app.log"),
            "log_rotation": os.getenv("LOG_ROTATION", "20 MB"),
            "log_retention": os.getenv("LOG_RETENTION", "1 week"),
            "log_compression": os.getenv("LOG_COMPRESSION", "zip"),
            # Stripe URLs from environment (non-secret)
            "stripe.success_url": os.getenv("STRIPE_SUCCESS_URL", ""),
            "stripe.cancel_url": os.getenv("STRIPE_CANCEL_URL", ""),
            "agent_runner": os.getenv("AGENT_RUNNER", ""),
            "agentcore.endpoint_url": os.getenv("AGENTCORE_ENDPOINT_URL", ""),
            "agentcore.runtime_arn": os.getenv("AGENTCORE_RUNTIME_ARN", ""),
            "sqs.game_turn_queue_url": os.getenv("GAME_TURN_SQS_QUEUE_URL", ""),
            "sqs.game_analysis_queue_url": os.getenv("GAME_ANALYSIS_SQS_QUEUE_URL", ""),
        }

    def _load_aws_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager if configured"""
        # Skip AWS Secrets Manager if explicitly disabled
        if self._env == "local":
            logger.info("Local environment detected (APP_ENV=local). Skipping AWS Secrets Manager.")
            return

        use_aws_secret_manager = os.getenv("USE_AWS_SECRET_MANAGER", "true").lower() == "true"
        if not use_aws_secret_manager:
            logger.info(
                "AWS Secrets Manager disabled (USE_AWS_SECRET_MANAGER=false). Skipping AWS Secrets Manager.",
            )
            return

        # Skip AWS Secrets Manager for local development (legacy support)
        use_localstack = os.getenv("USE_LOCALSTACK", "").lower() == "true"
        if use_localstack:
            logger.info(
                "Local development detected (USE_LOCALSTACK=true). Skipping AWS Secrets Manager.",
            )
            return

        # Check if AWS Secrets Manager is configured
        secret_name = os.getenv("AWS_SECRETS_MANAGER_SECRET_NAME")

        # Default secret names based on environment if not specified
        if not secret_name:
            if self._env == "production":
                secret_name = "prod_secret"
            elif self._env == "development":
                secret_name = "dev_secret"
            else:
                # For other environments (staging, test, etc.)
                secret_name = f"{self._env}_secret"

        # If still no secret name (shouldn't happen with above logic, but safety check)
        if not secret_name:
            logger.info(
                "AWS Secrets Manager not configured. Skipping AWS secrets loading.",
            )
            return

        try:
            # Get AWS region from environment or use default
            region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

            # Create a Secrets Manager client using default AWS credentials
            # This will use AWS profile, environment variables, or IAM role automatically
            session = boto3.Session()
            client = session.client(  # type: ignore[misc]
                service_name="secretsmanager",
                region_name=region_name,
            )

            logger.info(f"Loading secrets from AWS Secrets Manager: {secret_name}")

            # Get the secret value
            response: dict[str, Any] = client.get_secret_value(SecretId=secret_name)  # type: ignore[assignment]
            secret_string = cast(str, response["SecretString"])

            # Parse the secret as YAML (same format as local secrets.yaml)
            secrets_data: Any = yaml.safe_load(secret_string)
            self._aws_secrets = cast(dict[str, Any], secrets_data) if secrets_data else {}
            logger.info("Successfully loaded secrets from AWS Secrets Manager")

        except NoCredentialsError:
            logger.exception(
                "AWS credentials not found. Cannot load secrets from AWS Secrets Manager.",
            )
        except ClientError as e:
            error_response: dict[str, Any] = cast(dict[str, Any], e.response)
            error_code = error_response.get("Error", {}).get("Code", "Unknown")
            if error_code == "DecryptionFailureException":
                logger.exception(
                    "Secrets Manager can't decrypt the protected secret text using the provided KMS key.",
                )
            elif error_code == "InternalServiceErrorException":
                logger.exception("An error occurred on the server side.")
            elif error_code == "InvalidParameterException":
                logger.exception("You provided an invalid value for a parameter.")
            elif error_code == "InvalidRequestException":
                logger.exception(
                    "You provided a parameter value that is not valid for the current state of the resource.",
                )
            elif error_code == "ResourceNotFoundException":
                logger.exception(f"The requested secret {secret_name} was not found.")
            else:
                logger.exception(f"Error loading secrets from AWS Secrets Manager: {e}")
        except yaml.YAMLError:
            logger.exception(
                "Failed to parse secrets from AWS Secrets Manager. Expected YAML format.",
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error loading secrets from AWS Secrets Manager: {e}",
            )

    def _load_secrets(self) -> None:
        """Load secrets from YAML file"""
        # Determine the secrets file path based on environment
        base_dir = Path(__file__).resolve().parent.parent.parent

        # Standard secrets files priority order
        secrets_files_to_try: list[Path] = [base_dir / "secrets.yaml", base_dir / f"secrets.{self._env}.yaml", base_dir / "secrets.example.yaml"]

        # Find the first existing secrets file
        secrets_file: Path | None = None
        for file_path in secrets_files_to_try:
            if file_path.exists():
                secrets_file = file_path
                break

        # Load secrets from file
        if secrets_file:
            try:
                with open(secrets_file) as f:
                    self._secrets = yaml.safe_load(f)
                logger.info(f"Loaded secrets from {secrets_file}")
            except Exception as e:
                logger.exception(f"Error loading secrets file: {e}")
                self._secrets = {}
        else:
            logger.warning("No secrets file found. Using default values.")
            self._secrets = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.
        Priority order:
        1. Environment variables (from _config dict)
        2. AWS Secrets Manager
        3. Local secrets file
        4. Direct environment variable lookup (os.getenv)
        5. Default value
        """
        # Check if key exists in environment variables
        if key in self._config:
            return self._config[key]

        # Check if key exists in AWS Secrets Manager (supports nested keys with dot notation)
        if self._aws_secrets and "." in key:
            parts = key.split(".")
            value: Any = self._aws_secrets
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = cast("Any", value[part])
                else:
                    break
            else:
                return value

        # Check if key exists at top level of AWS secrets
        if self._aws_secrets and key in self._aws_secrets:
            return self._aws_secrets[key]

        # Check if key exists in local secrets file (supports nested keys with dot notation)
        if "." in key:
            parts = key.split(".")
            value: Any = self._secrets
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = cast("Any", value[part])
                else:
                    return default
            return value

        # Check if key exists at top level of local secrets
        if key in self._secrets:
            return self._secrets[key]

        # Fallback to direct environment variable lookup
        # This ensures that any environment variables loaded by load_dotenv()
        # but not explicitly added to self._config are still accessible
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        return default

    def get_database_url(self) -> str:
        """Get database URL from secrets or construct it from components.
        Priority:
        1. Full URL from environment (prioritized in test mode)
        2. Full URL from AWS Secrets Manager
        3. Full URL from local secrets
        4. Constructed from components
        """
        # In test mode, prioritize environment variable over secrets
        if self.is_testing():
            db_url = os.getenv("DATABASE_URL")
            if db_url:
                return db_url

        # Check if a full URL is provided in AWS secrets first
        if self._aws_secrets and "database" in self._aws_secrets and "url" in self._aws_secrets["database"]:
            return self._aws_secrets["database"]["url"]

        # Check if a full URL is provided in local secrets
        if self._secrets and "database" in self._secrets and "url" in self._secrets["database"]:
            return self._secrets["database"]["url"]

        # Check if a full URL is provided in environment
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Construct from components
        username = self.get("database.username", "postgres")
        password = self.get("database.password", "postgres")
        host = self.get("database.host", "localhost")
        port = self.get("database.port", 5432)
        name = self.get("database.name", "mydatabase")

        return f"postgresql://{username}:{password}@{host}:{port}/{name}"

    def get_secret_key(self) -> str:
        """Get the secret key for JWT tokens and other security features"""
        return self.get("security.secret_key", "your_secret_key_here")

    def get_aws_credentials(self) -> dict[str, str]:
        """Get AWS credentials from environment variables or AWS profile.
        This method returns empty strings to let boto3 use its default credential chain:
        1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. AWS credentials file (~/.aws/credentials)
        3. IAM roles (when running on EC2)
        """
        return {
            "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
            "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        }

    def get_cognito_config(self) -> dict[str, str]:
        """Get Cognito configuration from environment variables and secrets"""
        return {
            "user_pool_id": os.getenv("COGNITO_USER_POOL_ID", ""),
            "client_id": os.getenv("COGNITO_CLIENT_ID", ""),
            "client_secret": self.get("aws.cognito_client_secret", ""),  # Load from secrets.yaml
            "endpoint_url": os.getenv("COGNITO_ENDPOINT_URL", ""),
            "region": os.getenv(
                "COGNITO_REGION",
                os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            ),
            "domain": os.getenv("COGNITO_DOMAIN", ""),
            "callback_url": os.getenv("COGNITO_CALLBACK_URL", "http://localhost:5888/auth/callback"),
        }

    def is_localstack_enabled(self) -> bool:
        """Check if LocalStack is enabled for development"""
        return self.get("use_localstack", False)

    def is_development(self) -> bool:
        """Check if the application is running in development mode"""
        return self._env.lower() == "development"

    def is_hackathon(self) -> bool:
        """Check if the application is running in hackathon mode"""
        return self._env.lower() == "hackathon"

    def is_production(self) -> bool:
        """Check if the application is running in production mode"""
        return self._env.lower() == "production"

    def is_testing(self) -> bool:
        """Check if the application is running in test mode"""
        return self._env.lower() in ("test", "testing")

    def use_mock_cognito(self) -> bool:
        """Check if mock Cognito service should be used"""
        return os.getenv("USE_MOCK_COGNITO", "false").lower() == "true"

    def get_environment(self) -> str:
        """Get the current environment name"""
        return self._env

    def get_provider_config(self, provider_name: str) -> "ProviderConfigData | None":
        """Get provider configuration from llm_providers section.

        Args:
            provider_name: Name of the provider (e.g., "openai", "anthropic")

        Returns:
            ProviderConfigData instance or None if not found
        """
        # Import here to avoid circular imports
        from common.models import ProviderConfigData

        # Map provider names to config keys for backward compatibility
        config_key_map = {
            "google": "gemini",  # Google provider uses gemini config key
        }
        config_key = config_key_map.get(provider_name, provider_name)

        # First try to get from llm_providers section
        provider_config = self.get(f"llm_providers.{config_key}")

        if provider_config and isinstance(provider_config, dict):
            try:
                # Convert the config dict to ProviderConfigData
                # Cast dict to proper type for unpacking
                config_dict = cast("dict[str, Any]", provider_config)
                return ProviderConfigData(**config_dict)
            except Exception as e:
                logger.warning(f"Failed to parse provider config for {provider_name}: {e}")
                return None

        # Fallback to legacy format for backward compatibility
        if provider_name == "openai":
            api_key = self.get("openai.api_key")
            if api_key:
                # Create with just api_key, other fields will use defaults from the model
                # Type ignore needed because Pylance doesn't understand Pydantic default values correctly
                return ProviderConfigData(api_key=str(api_key))  # type: ignore[call-arg]

        return None


# Create a singleton instance
config_service = ConfigService()


# Determine the environment file path for Settings
def get_env_file_path() -> str:
    # Get the base directory for the backend
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Determine the environment
    env = os.getenv("APP_ENV", "development")

    # Set the environment file path
    env_file = base_dir / f".env.{env}"

    # If environment-specific file doesn't exist, fall back to development
    if not env_file.exists() and env != "development":
        logger.warning(
            f"Environment file {env_file} not found. Falling back to development.",
        )
        env_file = base_dir / ".env.development"

    # If still no file, try generic .env
    if not env_file.exists():
        env_file = base_dir / ".env"

    # If no environment file exists, log a warning
    if not env_file.exists():
        logger.warning("No environment file found. Using default values.")
        return ""
    else:
        logger.info(f"Using environment file: {env_file}")
        return str(env_file)


class Settings(BaseSettings):
    """Application settings that loads from environment variables and secrets file"""

    # API settings
    API_V1_STR: str = config_service.get("api_prefix", "/api/v1")
    PROJECT_NAME: str = config_service.get("project_name", "Agent League")

    # CORS settings
    CORS_ORIGINS: str = ",".join(
        config_service.get(
            "cors_origins",
            ["http://localhost:3000", "http://localhost:5888"],
        ),
    )

    # Database settings
    DATABASE_URL: str = config_service.get_database_url()
    DB_NAME: str = config_service.get("database.name", "mydatabase")

    # Security settings
    SECRET_KEY: str = config_service.get_secret_key()

    # Application settings
    DEBUG: bool = config_service.get("debug", True)
    LOG_LEVEL: str = config_service.get("log_level", "info")
    ALLOWED_HOSTS: str = ",".join(
        config_service.get("allowed_hosts", ["localhost", "127.0.0.1"]),
    )

    # AWS settings
    AWS_ACCESS_KEY_ID: str = config_service.get("aws.access_key_id", "")
    AWS_SECRET_ACCESS_KEY: str = config_service.get("aws.secret_access_key", "")

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        """Returns the CORS origins as a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def ALLOWED_HOSTS_LIST(self) -> list[str]:
        """Returns the allowed hosts as a list"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    class Config:
        env_file = get_env_file_path()
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment


# Create a singleton instance of Settings
settings = Settings()
