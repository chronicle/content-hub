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

import atexit
import logging
import logging.config
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from typing import Any

import yaml

type LogConfig = dict[str, Any]


def setup_logging(
    config_path: str = "logging.yaml",
    log_level: str | None = None,
) -> logging.Logger:
    path: Path = Path(__file__).parent / config_path

    if not path.exists():
        msg: str = f"Logging configuration file not found: {path}"
        raise FileNotFoundError(msg)

    with path.open(encoding="utf-8") as f:
        config: LogConfig = yaml.safe_load(f)

    if log_level:
        # Override levels in config if provided
        config["root"]["level"] = log_level.upper()
        if "handlers" in config and "console" in config["handlers"]:
            config["handlers"]["console"]["level"] = log_level.upper()

    logging.config.dictConfig(config)

    root: logging.Logger = logging.getLogger()
    target_handlers: list[logging.Handler] = list(root.handlers)

    log_queue: Queue[logging.LogRecord] = Queue(-1)
    queue_handler: QueueHandler = QueueHandler(log_queue)

    listener: QueueListener = QueueListener(
        log_queue,
        *target_handlers,
        respect_handler_level=True,
    )
    listener.start()

    root.handlers = [queue_handler]

    atexit.register(listener.stop)

    return logging.getLogger("product_agent_mesh")
