import logging
import sys

from colorlog import ColoredFormatter

from app.config.settings import LOG_FOLDER

LOG_FILE = LOG_FOLDER / "crawler.log"


def configure_logging():

    logger = logging.getLogger()

    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    console = logging.StreamHandler(sys.stdout)

    console.setFormatter(

        ColoredFormatter(

            "%(log_color)s"

            "%(asctime)s "

            "%(levelname)-8s "

            "%(message)s",

            datefmt="%H:%M:%S",

            log_colors={

                "DEBUG": "cyan",

                "INFO": "green",

                "WARNING": "yellow",

                "ERROR": "red",

                "CRITICAL": "bold_red",

            },

        )

    )

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf8"
    )

    file_handler.setFormatter(

        logging.Formatter(

            "%(asctime)s "

            "%(levelname)s "

            "%(name)s "

            "%(message)s"

        )

    )

    logger.addHandler(console)

    logger.addHandler(file_handler)

    return logger