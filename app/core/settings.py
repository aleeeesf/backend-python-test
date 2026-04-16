from pydantic import Field
from pydantic_settings import BaseSettings


class ExternalProviderSettings(BaseSettings):
    api_url: str = Field(
        default="http://localhost:3001",
        description="External provider API URL",
    )  # Only for this challenge setted as default, in production it should be loaded from environment variables
    api_key: str = Field(
        default="test-dev-2026",
        description="External provider API key",
    )  # Only for this challenge setted as default, in production it should be loaded from environment variables


class Settings(BaseSettings):
    external_provider: ExternalProviderSettings = ExternalProviderSettings()


settings = Settings()
