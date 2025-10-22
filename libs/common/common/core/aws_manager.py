"""AWS service manager with lifecycle management."""

from __future__ import annotations

from contextlib import AsyncExitStack
from functools import cached_property
from typing import TYPE_CHECKING, override

from aiobotocore.session import get_session
from dotenv import load_dotenv

from common.core.config_service import config_service
from common.core.deployment import Deployment
from common.core.lifecycle import Lifecycle
from common.utils.utils import cached_classmethod, get_logger

if TYPE_CHECKING:
    from types_aiobotocore_bedrock_runtime import BedrockRuntimeClient
    from types_aiobotocore_cognito_idp import CognitoIdentityProviderClient
    from types_aiobotocore_secretsmanager import SecretsManagerClient
    from types_aiobotocore_sqs import SQSClient

logger = get_logger()
load_dotenv()


class AwsManager(Lifecycle):
    """AWS service manager with lifecycle management for async clients."""

    def __init__(self) -> None:
        super().__init__()

        # When using IRSA, we don't need to set any credentials
        # The SDK will automatically pick up the web identity token
        self._session = get_session()
        self._exit_stack = AsyncExitStack()

        # Load AWS credentials from config service (which reads from secrets.yaml)
        self._aws_creds = config_service.aws

        self._secretsmanager_client: SecretsManagerClient | None = None
        self._sqs_client: SQSClient | None = None
        self._cognito_idp_client: CognitoIdentityProviderClient | None = None
        self._bedrock_runtime_client: BedrockRuntimeClient | None = None

    @cached_classmethod
    def instance(cls) -> AwsManager:
        return AwsManager()

    @cached_property
    def _aws_access_key_id(self) -> str:
        """Get AWS access key ID from config service."""
        return self._aws_creds.access_key_id

    @cached_property
    def _aws_secret_access_key(self) -> str:
        """Get AWS secret access key from config service."""
        return self._aws_creds.secret_access_key

    @cached_property
    def _aws_session_token(self) -> str:
        """Get AWS session token from config service."""
        return self._aws_creds.session_token

    @cached_property
    def _region_name(self) -> str:
        """Get AWS region from config service."""
        return self._aws_creds.region

    @property
    def secretsmanager_client(self) -> SecretsManagerClient:
        assert self._secretsmanager_client is not None
        return self._secretsmanager_client

    @property
    def sqs_client(self) -> SQSClient:
        assert self._sqs_client is not None
        return self._sqs_client

    @property
    def cognito_idp_client(self) -> CognitoIdentityProviderClient:
        assert self._cognito_idp_client is not None
        return self._cognito_idp_client

    @property
    def bedrock_runtime_client(self) -> BedrockRuntimeClient:
        assert self._bedrock_runtime_client is not None
        return self._bedrock_runtime_client

    @property
    def ses_client(self) -> SQSClient:
        assert self._sqs_client is not None
        return self._sqs_client

    @override
    async def _start(self) -> None:
        """Start AWS service clients."""
        if Deployment.is_cloud():
            # Cloud environments use real AWS services
            # Don't pass credentials - let boto3 use IAM roles/IRSA
            self._secretsmanager_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="secretsmanager",
                    region_name=self._region_name,
                ),
            )

            self._sqs_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="sqs",
                    region_name=self._region_name,
                ),
            )

            # Bedrock Runtime for Guardrails
            self._bedrock_runtime_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="bedrock-runtime",
                    region_name=self._region_name,
                ),
            )

            # Cognito is prod in both envs
            self._cognito_idp_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="cognito-idp",
                    region_name=self._region_name,
                ),
            )
        else:
            # Local development environment
            # Only pass credentials if explicitly provided in secrets.yaml
            # Otherwise let boto3 use default credential chain
            client_kwargs = {"region_name": self._region_name}
            if self._aws_creds.has_credentials():
                client_kwargs["aws_access_key_id"] = self._aws_access_key_id
                client_kwargs["aws_secret_access_key"] = self._aws_secret_access_key
                if self._aws_session_token:
                    client_kwargs["aws_session_token"] = self._aws_session_token

            # No secretmanager in localstack
            self._sqs_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="sqs",
                    endpoint_url="http://localhost:4566/",
                    use_ssl=False,
                    **client_kwargs,
                ),
            )

            # Bedrock Runtime for Guardrails (uses real AWS, not LocalStack)
            self._bedrock_runtime_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="bedrock-runtime",
                    **client_kwargs,
                ),
            )

            # Cognito is prod in both envs
            self._cognito_idp_client = await self._exit_stack.enter_async_context(
                self._session.create_client(  # type: ignore
                    service_name="cognito-idp",
                    **client_kwargs,
                ),
            )

    @override
    async def _stop(self) -> None:
        """Stop AWS service clients."""
        for client in [
            self._secretsmanager_client,
            self._sqs_client,
            self._cognito_idp_client,
            self._bedrock_runtime_client,
            self._sqs_client,
        ]:
            if client is not None:
                await client.close()
            await self._exit_stack.aclose()
