from __future__ import annotations

import sys
from contextlib import contextmanager, suppress
from typing import Any, Iterator

from TIPCommon.base.action import Action

from ..core.constants import (
    INTEGRATION_NAME,
    PARAM_ACCESS_KEY,
    PARAM_ACCESS_KEY_ID,
    PARAM_API_ROOT,
    PARAM_VERIFY_SSL,
    PING_SCRIPT_NAME,
)
from ..core.utils import truthy
from ..core.VegaManager import VegaClientConfig, VegaManager


@contextmanager
def _mute_siemplify_logs(siemplify: Any) -> Iterator[None]:
    logger = getattr(siemplify, "LOGGER", None)
    if logger is None:
        yield
        return
    names = ("info", "error", "warning", "warn", "debug", "exception")
    original = {name: getattr(logger, name, None) for name in names}

    def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    for name, method in original.items():
        if callable(method):
            setattr(logger, name, _noop)
    try:
        yield
    finally:
        for name, method in original.items():
            if method is not None:
                setattr(logger, name, method)


def _clear_captured_output(siemplify: Any) -> None:
    """Test connectivity shows DebugOutput (printed logs), not only end()."""
    logger = getattr(siemplify, "LOGGER", None)
    rows = getattr(logger, "_log_rows", None) if logger is not None else None
    if isinstance(rows, list):
        rows.clear()
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "truncate") and hasattr(stdout, "seek"):
        with suppress(Exception):
            stdout.truncate(0)
            stdout.seek(0)


class Ping(Action):
    """Validate Vega API Root, Access Key, and Access Key ID."""

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters!"
        )
        self.error_output_message = f"Failed to connect to the {INTEGRATION_NAME} server!"

    def _init_api_clients(self) -> VegaManager:
        soar = self.soar_action
        with _mute_siemplify_logs(soar):
            conf = soar.get_configuration(INTEGRATION_NAME) or {}
        _clear_captured_output(soar)
        return VegaManager(
            VegaClientConfig(
                api_root=conf.get(PARAM_API_ROOT),
                access_key_id=conf.get(PARAM_ACCESS_KEY_ID),
                access_key=conf.get(PARAM_ACCESS_KEY),
                verify_ssl=truthy(conf.get(PARAM_VERIFY_SSL, True)),
            )
        )

    def _perform_action(self, _=None) -> None:
        try:
            self.api_client.test_connection()
        except Exception:
            _clear_captured_output(self.soar_action)
            raise


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
