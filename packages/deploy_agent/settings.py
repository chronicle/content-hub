from contextvars import ContextVar

from pydantic_settings import SettingsConfigDict

from .common import CommonSettings
from .jira import JiraSettings
from .secops import SecOpsSettings
from .servicenow import ServiceNowSettings
from .virustotal import VirusTotalSettings


class Settings(
    CommonSettings,
    ServiceNowSettings,
    JiraSettings,
    SecOpsSettings,
    VirusTotalSettings,
):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


_settings_ctx: ContextVar[Settings | None] = ContextVar("settings", default=None)


def get_settings() -> Settings:
    current_settings: Settings | None = _settings_ctx.get()
    if current_settings is None:
        current_settings = Settings()
        _settings_ctx.set(current_settings)
    return current_settings


def set_settings(new_settings: Settings) -> None:
    _settings_ctx.set(new_settings)
