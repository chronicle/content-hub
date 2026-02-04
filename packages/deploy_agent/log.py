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
