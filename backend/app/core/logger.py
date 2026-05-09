import sys
from loguru import logger


def get_logger(name: str):
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
        level="DEBUG",
    )
    logger.add(
        "logs/{name}.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
    )
    return logger.bind(name=name)
