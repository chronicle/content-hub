# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
