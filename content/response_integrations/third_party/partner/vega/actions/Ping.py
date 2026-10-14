from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Iterator

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@contextmanager
def _mute_siemplify_logs(siemplify: SiemplifyAction) -> Iterator[None]:
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


def _clear_captured_output(siemplify: SiemplifyAction) -> None:
    """Test connectivity shows DebugOutput (printed logs), not only end()."""
    logger = getattr(siemplify, "LOGGER", None)
    rows = getattr(logger, "_log_rows", None) if logger is not None else None
    if isinstance(rows, list):
        rows.clear()
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "truncate") and hasattr(stdout, "seek"):
        try:
            stdout.truncate(0)
            stdout.seek(0)
        except Exception:
            pass


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    from ..core.constants import (
        INTEGRATION_NAME,
        PARAM_ACCESS_KEY,
        PARAM_ACCESS_KEY_ID,
        PARAM_API_ROOT,
        PING_SCRIPT_NAME,
    )
    from ..core.VegaManager import VegaManager

    siemplify.script_name = PING_SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    try:
        with _mute_siemplify_logs(siemplify):
            conf = siemplify.get_configuration(INTEGRATION_NAME) or {}
        _clear_captured_output(siemplify)
        manager = VegaManager(
            api_root=conf.get(PARAM_API_ROOT),
            access_key_id=conf.get(PARAM_ACCESS_KEY_ID),
            access_key=conf.get(PARAM_ACCESS_KEY),
        )
        manager.test_connection()
        output_message = (
            f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters!"
        )
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to connect to the {INTEGRATION_NAME} server! Error is {error}"
        _clear_captured_output(siemplify)
    if result_value:
        siemplify.LOGGER.info(output_message)
    else:
        siemplify.LOGGER.error(output_message)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
