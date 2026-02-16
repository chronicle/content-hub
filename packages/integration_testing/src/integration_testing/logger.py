# Copyright 2025 Google LLC
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

import logging
from typing import Any

try:
    from TIPCommon.base.interfaces import Logger as LoggerInterface
except ImportError:
    LoggerInterface = object


class Logger(LoggerInterface):
    """Mocks a logger object with info, error, warn and debug methods."""

    def __init__(self, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Initialize the logger."""
        self.logger: logging.Logger = get_logger()
        self.log_rows: list[str] = []

    def debug(self, msg: str, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Log a debug message."""
        self.log_rows.append(msg)
        self.logger.debug(msg)

    def info(self, msg: str, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Log an info message."""
        self.log_rows.append(msg)
        self.logger.info(msg)

    def warn(self, msg: str, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Log a warning message."""
        self.log_rows.append(msg)
        self.logger.warning(msg)

    def error(self, msg: str, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Log an error message."""
        self.log_rows.append(msg)
        self.logger.error(msg)

    def exception(self, ex: Exception, *_: Any, **__: Any) -> None:  # noqa: ANN401
        """Log an exception object."""
        str_ex: str = str(ex)
        self.log_rows.append(str_ex)
        self.logger.error(str_ex)


def get_logger() -> logging.Logger:
    """Get a python logging logger object."""
    logger: logging.Logger = logging.getLogger(__name__)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())

    logger.addHandler(console_handler)
    return logger


class ColoredFormatter(logging.Formatter):
    def __init__(self) -> None:
        """Initialize the formatter."""
        super().__init__()
        self.white: str = "\x1b[2m"
        self.bold_white: str = "\x1b[1m"
        self.yellow: str = "\x1b[33m"
        self.red: str = "\x1b[31m"
        self.cyan: str = "\x1b[36m"
        self.reset: str = "\x1b[0m"

        self.format_: str = "[%(asctime)s | %(levelname)s]: %(message)s"

        self.formats: dict[int, str] = {
            logging.DEBUG: f"{self.bold_white}{self.format_}{self.reset}",
            logging.INFO: f"{self.white}{self.format_}{self.reset}",
            logging.WARNING: f"{self.yellow}{self.format_}{self.reset}",
            logging.ERROR: f"{self.red}{self.format_}{self.reset}",
            logging.CRITICAL: f"{self.cyan}{self.format_}{self.reset}",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record.

        Args:
            record: the log record to format

        Returns:
            the formatted log value

        """
        log_fmt: str | None = self.formats.get(record.levelno)
        formatter: logging.Formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
