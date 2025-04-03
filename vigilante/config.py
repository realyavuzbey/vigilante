"""
Vigilante Global Configuration
"""

import os
from fake_useragent import UserAgent

ua = UserAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

random_ua = ua.random

GLOBAL_TIMEOUT = 15

IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico"
)

VIDEO_EXTENSIONS = (
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".3gp", ".m4v"
)

CONFIG = {
    "VERSION": "0.1.0",
    "DEFAULT_MODE": "balanced",
    "DEFAULT_TYPE": "text",
    "DIR": BASE_DIR,
    "OUTPUT_DIR": os.path.join(BASE_DIR, "..", "output"),
    "USER_AGENT": random_ua,
    "HEADERS": {
        "User-Agent": random_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "DNT": "1",
        "Pragma": "no-cache",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    },
    "TIMEOUT": 10,
    "MAX_THREADS": 50,
    "TOR_ENABLED": False
}
