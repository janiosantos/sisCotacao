from pathlib import Path
from dotenv import load_dotenv

import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in (
        "1",
        "true",
        "yes",
        "on"
    )


BASE_URL = os.getenv(
    "BASE_URL",
    ""
)

HEADLESS = _bool(
    "HEADLESS",
    False
)

TIMEOUT = int(
    os.getenv(
        "TIMEOUT",
        30
    )
)

WINDOW_WIDTH = int(
    os.getenv(
        "WINDOW_WIDTH",
        1920
    )
)

WINDOW_HEIGHT = int(
    os.getenv(
        "WINDOW_HEIGHT",
        1080
    )
)

DOWNLOAD_IMAGES = _bool(
    "DOWNLOAD_IMAGES",
    True
)

MAX_RETRY = int(
    os.getenv(
        "MAX_RETRY",
        3
    )
)

WAIT_TIME = int(
    os.getenv(
        "WAIT_TIME",
        20
    )
)

USER_AGENT = os.getenv(
    "USER_AGENT",
    ""
)

REQUEST_DELAY = float(
    os.getenv(
        "REQUEST_DELAY",
        0.5
    ).replace(",", ".")
)

MAX_PAGES = int(
    os.getenv(
        "MAX_PAGES",
        0
    )
)

MAX_CATEGORIES = int(
    os.getenv(
        "MAX_CATEGORIES",
        0
    )
)

MAX_PRODUCTS = int(
    os.getenv(
        "MAX_PRODUCTS",
        0
    )
)

IMAGE_FOLDER = BASE_DIR / "images"

OUTPUT_FOLDER = BASE_DIR / "output"

LOG_FOLDER = BASE_DIR / "logs"

DATABASE_FOLDER = BASE_DIR / "database"

for folder in (
    IMAGE_FOLDER,
    OUTPUT_FOLDER,
    LOG_FOLDER,
    DATABASE_FOLDER,
):
    folder.mkdir(
        parents=True,
        exist_ok=True
    )