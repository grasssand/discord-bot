import logging


def logger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s:%(lineno)s: %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    log.addHandler(handler)

    return log
