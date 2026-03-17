import logging
import os
from datetime import datetime

os.makedirs("logs", exist_ok=True)

_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
_log_file = f"logs/session_{_session_id}.log"

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("bot_logger")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(_log_file, encoding="utf-8")
    fh.setFormatter(_fmt)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(_fmt)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)


def get_logger():
    return logger


def get_log_file():
    return _log_file
