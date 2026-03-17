import logging
import os
from datetime import datetime

# Setup root logger
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("bot_logger")
logger.setLevel(logging.INFO)

# Make sure we don't add multiple handlers if imported multiple times
if not logger.handlers:
    # 1. File Handler (writes to bot.log)
    file_handler = logging.FileHandler("bot.log", mode='a', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler (fallback for terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

def get_logger():
    """Returns the configured logger instance."""
    return logger
