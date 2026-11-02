import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "entellibot", level: int = logging.INFO) -> logging.Logger:
    """Logger sozlamasi"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Agar handlerlar allaqachon qo'shilgan bo'lsa, qaytaramiz
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        'logs/bot.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
