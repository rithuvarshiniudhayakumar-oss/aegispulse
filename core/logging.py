"""Logging setup."""
import logging as _logging
import os
import sys


def get_logger(name: str) -> _logging.Logger:
    root = _logging.getLogger()
    if not root.handlers:
        _logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stdout,
        )
    return _logging.getLogger(name)
