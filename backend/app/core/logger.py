import sys
from loguru import logger

_configured = False


def get_logger(name: str):
    global _configured
    if not _configured:
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{extra[name]}</cyan> | {message}",
            level="DEBUG",
        )
        logger.add(
            "logs/app.log",
            rotation="10 MB",
            retention="7 days",
            level="INFO",
        )
        _configured = True
    return logger.bind(name=name)
