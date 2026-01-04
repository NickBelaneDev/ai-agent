import logging
import sys


def setup_logging(name: str = "ai_agents",
                  log_level: int = logging.INFO) -> logging.Logger:
    """
    Sets up and returns a logger with the specified name and level.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Check if handlers are already added to avoid duplicate logs
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

    return logger

# Create a default logger instance
logger = setup_logging(log_level=logging.DEBUG)
