import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    name: str = "signalforge",
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
