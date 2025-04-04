import os
import sys
import requests
from .config import CONFIG
from .utils import rotate_ua, rotate_ip, is_mobile

class Session:
    """
    Session wraps a requests.Session configured for Tor and advanced recon.
    Features:
    - SOCKS5 proxy (Tor)
    - Custom headers
    - Timeout handling
    - Header rotation
    - IP rotation
    """

    def __init__(self, rotate_ua=True, rotate_ip_on_init=False):
        self.session = requests.Session()
        self.proxy_port = self._detect_tor_port()

        self.proxy = {
            "http": f"socks5h://127.0.0.1:{self.proxy_port}",
            "https": f"socks5h://127.0.0.1:{self.proxy_port}"
        }

        self.session.proxies.update(self.proxy)

        self.timeout = CONFIG["TIMEOUT"]
        self.rotate_ua = rotate_ua

        headers = self._generate_headers()
        self.session.headers.update(headers)

        if rotate_ip_on_init:
            self.rotate_identity()

    def _detect_tor_port(self):
        return 9050 if is_mobile() else 9150

    def _generate_headers(self):
        """
        Generates randomized headers. User-Agent rotation optional.
        """
        headers = CONFIG["HEADERS"].copy()
        if self.rotate_ua:
            headers["User-Agent"] = rotate_ua()
        return headers

    def rotate_identity(self):
        """
        Signals Tor to rotate IP (New Identity).
        """
        result = rotate_ip()
        return result

    def clone(self):
        """
        Returns a new Session instance with same configuration.
        """
        return Session(rotate_ua=self.rotate_ua)

    def get(self, url, **kwargs):
        """
        Wrapper for GET request with injected defaults.
        """
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", self._generate_headers())
        return self.session.get(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """
        Wrapper for POST requests.
        """
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", self._generate_headers())
        return self.session.post(url, data=data, json=json, **kwargs)

    def head(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", self._generate_headers())
        return self.session.head(url, **kwargs)

    def get_ip(self):
        """
        Returns the current public IP (useful for checking Tor routing).
        """
        try:
            resp = self.get("https://api.ipify.org?format=json")
            return resp.json()
        except:
            return {"error": "Could not fetch IP"}
