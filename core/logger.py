import logging
import os
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

    # Console handler (Railway va Docker uchun asosiy)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (papka bo'lmasa yaratamiz, xato bo'lsa console bilan davom etamiz)
    try:
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler(
            'logs/bot.log',
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Log faylini yaratishda ogohlantirish: {e}")

    return logger


logger = setup_logger()
