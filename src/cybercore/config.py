"""CyberCore configuration loaded from environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Secrets are read from environment variables and are never rendered in output.
    """

    model_config = SettingsConfigDict(
        env_prefix="CYBERCORE_",
        case_sensitive=False,
        extra="ignore",
    )

    interserver_api_key: SecretStr | None = None
    interserver_base_url: str = "https://my.interserver.net/apiv2"
    http_timeout_seconds: float = 20.0

    @property
    def has_interserver_api_key(self) -> bool:
        return bool(self.interserver_api_key and self.interserver_api_key.get_secret_value())
