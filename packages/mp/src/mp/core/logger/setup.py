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

from __future__ import annotations

import atexit
import logging
import logging.config
import queue
from logging.handlers import QueueHandler, QueueListener
from typing import Any


def setup_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    """Set up logging for the mp CLI."""
    level: int = _get_logger_level(quiet=quiet, verbose=verbose)

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"rich_simple": {"format": "%(message)s", "datefmt": "[%X]"}},
        "handlers": {
            "console": {
                "class": "rich.logging.RichHandler",
                "level": level,
                "formatter": "rich_simple",
                "rich_tracebacks": True,
                "markup": True,
                "show_time": False,
                "show_level": False,
                "show_path": False,
            }
        },
        "loggers": {"root": {"level": level, "handlers": ["console"]}},
    }

    logging.config.dictConfig(config)

    root: logging.Logger = logging.getLogger()
    if not any(isinstance(h, QueueHandler) for h in root.handlers):
        _configure_queue_logging(root)

    _set_other_noisy_loggers_level(verbose=verbose)


def _get_logger_level(*, quiet: bool, verbose: bool) -> int:
    if verbose:
        return logging.DEBUG

    if quiet:
        return logging.WARNING

    return logging.INFO


def _configure_queue_logging(root: logging.Logger) -> None:
    existing_handlers: list[logging.Handler] = list(root.handlers)
    for handler in existing_handlers:
        root.removeHandler(handler)

    log_queue: queue.Queue = queue.Queue(-1)
    queue_handler: QueueHandler = QueueHandler(log_queue)
    root.addHandler(queue_handler)

    listener: QueueListener = QueueListener(
        log_queue,
        *existing_handlers,
        respect_handler_level=True,
    )
    listener.start()

    atexit.register(listener.stop)


def _set_other_noisy_loggers_level(*, verbose: bool) -> None:
    extra_level: int = logging.NOTSET if verbose else logging.WARNING
    for logger_name in ("google", "google_genai", "urllib3", "httpx"):
        logging.getLogger(logger_name).setLevel(extra_level)
