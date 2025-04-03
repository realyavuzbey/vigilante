import requests
from .config import CONFIG

class Session:
    """
    Session wraps a requests.Session that is configured for Tor.
    It centralizes the session configuration (headers, timeout, and proxy).
    """
    def __init__(self):
        self.session = requests.Session()
        self.proxy = {
            "http": "socks5h://127.0.0.1:9150",
            "https": "socks5h://127.0.0.1:9150"
        }
        self.session.proxies.update(self.proxy)
        self.session.headers.update(CONFIG["HEADERS"])
        self.timeout = CONFIG["TIMEOUT"]

    def clone(self):
        """
        Clones session.
        """
        return Session()

    def get(self, url, **kwargs):
        """
        A wrapper around requests.Session.get that injects default timeout and headers.
        """
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", CONFIG["HEADERS"])
        return self.session.get(url, **kwargs)

    def head(self, url, **kwargs):
        """
        A wrapper around requests.Session.head that injects default timeout and headers.
        """
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", CONFIG["HEADERS"])
        return self.session.head(url, **kwargs)

    def generate_headers(self):
        """
        This method can be expanded to generate dynamic headers if needed.
        For now, returns the static headers from the config.
        """
        return CONFIG["HEADERS"]
