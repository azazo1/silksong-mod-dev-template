import logging

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
        _configured = True
    return logging.getLogger(name)
