from __future__ import annotations
import dataclasses

from TIPCommon.base.interfaces import ScriptLogger


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    api_token: str
    verify_ssl: bool
    siemplify_logger: ScriptLogger
