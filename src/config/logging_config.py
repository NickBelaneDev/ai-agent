import logging
import sys

import logging
import sys
import json
import time


class JsonFormatter(logging.Formatter):
    """
    Formats logs as JSON rows for better machine readability (Docker/ELK).
    """

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(name: str = "ai_agents",
                  log_level: int = logging.INFO) -> logging.Logger:
    _logger = logging.getLogger(name)
    _logger.setLevel(log_level)

    if not _logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        use_json = True

        if use_json:
            formatter = JsonFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)

    return _logger


# Create a default logger instance
logger = setup_logging(log_level=logging.DEBUG)
