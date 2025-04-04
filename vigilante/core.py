import os
import time
import shutil
import requests
import platform
import threading

from .config import CONFIG
from .nightcrawler import Nightcrawler
from .utils import rotate_ip, export_data, rotate_ua, basedir
from .session import Session
from .scraptor import Scraptor

class Vigilante:
    """
    Vigilante is a dark web search orchestrator that utilizes a Tor-enabled session
    to perform secure searches and manage IP rotation based on security levels.
    
    Attributes:
        security (str): The security level ("1", "2", etc.).
        export_json (bool): Flag indicating whether to export results in JSON format.
        headers (dict): HTTP headers configuration.
        timeout (int): Timeout setting for HTTP requests.
        tor_enabled (bool): Indicates if Tor is enabled.
        proxy (dict): Proxy configuration for Tor connections.
        ip_type (str): Type of IP to use ('dynamic' or 'static').
        session (requests.Session): A session configured with Tor proxies.
        nightcrawler (Nightcrawler): Instance for crawling dark web search engines.
        ip_info (dict): Information about the current IP environment.
        
    Methods:
        whois(): A styled mission statement along with platform and Python info.
        crawl(term): Returns structured search results from Ahmia, Tordex and more data.
    """

    def __init__(self, security="1", export_as=None, debug=False):
        """
        Initialize the Vigilante instance with security settings and a Tor session.

        Args:
            security (str, optional): The security level. Defaults to "1".
            export_as (str, optional): Export format. One of "json", "csv", "markdown", or "txt". Defaults to None.
            debug (bool, optional): Just a simple debug.
        """
        self.security = str(security)
        self.export_as = export_as
        self.debug = debug

        # Load configuration from CONFIG
        self.headers = CONFIG["HEADERS"]
        self.timeout = CONFIG["TIMEOUT"]
        self.tor_enabled = True

        # Initialize session wrapper and obtain default Tor session
        self.session_wrapper = Session()
        self.session = self.session_wrapper.session

        # Set up the proxy based on the platform (mobile or desktop)
        self.proxy = self._set_proxy()
        self.session.proxies.update(self.proxy)
        self.session.headers.update(self.headers)

        # Initialize Nightcrawler with the Tor session
        self.nightcrawler = Nightcrawler(session=self.session, export_as=self.export_as)
        self.scraptor = Scraptor(downloads=basedir("downloads/websites"), session=self.session)

        # Set IP type based on security level
        self.ip_type = "dynamic" if self.security in ["1", "2"] else "static"

        # Security adjustments
        if self.security == "2":
            self.timeout += 5
            self.headers["X-Security-Level"] = "Medium"
        elif self.security == "3":
            self.timeout += 10
            self.headers["X-Security-Level"] = "High"
            self.headers["User-Agent"] = rotate_ua()
        elif self.security == "4":
            self.timeout += 15
            self.headers["X-Security-Level"] = "Ultra"
            self.headers["User-Agent"] = rotate_ua()
            self.enable_honeypot_protection = True

        if self.security in ["1", "2"]:
            rotate_ip()
        if self.security in ["3", "4"]:
            self._renew_tor_identity()

        # Check and store the current IP environment information
        self.ip_info = self._check_environment()
        self._start_pycache_cleaner(interval=60)

    def _set_proxy(self):
        """
        Determine and set the SOCKS proxy based on the platform.

        Returns:
            dict: Proxy configuration for Tor connections.
        """
        system = platform.system().lower()
        if "android" in system:
            # Mobile platform uses port 9050
            return {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            }
        elif "windows" in system or "darwin" in system or "linux" in system:
            # Desktop platforms use port 9150 (or fallbacks if needed)
            proxy_port = self._determine_proxy_port()
            return {
                "http": f"socks5h://127.0.0.1:{proxy_port}",
                "https": f"socks5h://127.0.0.1:{proxy_port}"
            }
        else:
            # Safe default for other platforms
            return {
                "http": "socks5h://127.0.0.1:9150",
                "https": "socks5h://127.0.0.1:9150"
            }

    def _determine_proxy_port(self):
        """
        Determine which SOCKS port to use based on the platform.
        For desktops, try 9150, then 9250, then 9350.
        """
        system = platform.system().lower()
        if "android" in system:
            return 9050
        elif "windows" in system or "darwin" in system or "linux" in system:
            for port in [9150, 9250, 9350]:
                if self._test_port(port):
                    return port
            return 9150
        else:
            return 9150

    def _test_port(self, port):
        """
        Test if a port is open on localhost.
        """
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except:
            return False

    def whois(self):
        """
        Returns a styled mission statement of the Vigilante OSINT Suite with system info.
        """
        message = (
            "\nVigilante OSINT Suite\n"
            "────────────────────────────────────────────\n"
            "Vigilante is a high-security, Tor-powered OSINT suite\n"
            "designed to crawl, analyze, and monitor dark web intelligence.\n"
            "From passive recon to active content extraction,\n"
            "Vigilante is your entry point into the underground.\n"
            "\n"
            f"- Python Version: {platform.python_version()}\n"
            f"- Platform: {platform.system()} {platform.release()}\n"
            "────────────────────────────────────────────\n"
        )
        return message

    def _renew_tor_identity(self):
        """
        Renews the Tor circuit to obtain a new exit node.
        """
        import stem.control
        try:
            with stem.control.Controller.from_port(port=9051) as controller:
                controller.authenticate(password="tor_password")
                controller.signal(stem.Signal.NEWNYM)
                print("[Vigilante] Tor circuit renewed.")
        except Exception as e:
            print(f"[ERROR] Failed to renew Tor circuit: {e}")

    def _check_environment(self):
        """
        Checks the current network environment using an external IP service.

        Returns:
            dict: Contains IP information, security level, IP type, and proxy details.
        """
        try:
            ip_service = "https://api.ipify.org?format=json"
            kwargs = {
                "headers": self.headers,
                "timeout": self.timeout,
                "proxies": self.proxy
            }
            if self.security == "2":
                kwargs["timeout"] += 5
                kwargs["headers"]["X-Security-Level"] = "High"
            response = requests.get(ip_service, **kwargs)
            ip_data = response.json() if response.status_code == 200 else {}
            ip_data.update({
                "security_level": self.security,
                "ip_type": self.ip_type,
                "proxy_used": self.proxy
            })
            return ip_data
        except Exception as e:
            return {
                "error": str(e),
                "security_level": self.security,
                "ip_type": self.ip_type,
                "proxy_used": self.proxy
            }
        
    def _delete_pycache_dirs(self, base_dir):
        """
        Recursively deletes all __pycache__ directories inside given base_dir.
        """
        for root, dirs, files in os.walk(base_dir):
            for dir_name in dirs:
                if dir_name == "__pycache__":
                    pycache_path = os.path.join(root, dir_name)
                    shutil.rmtree(pycache_path)

    def _start_pycache_cleaner(self, interval=60):
        """
        Starts a background thread that deletes __pycache__ folders every 'interval' seconds.
        """
        def cleaner():
            while True:
                self._delete_pycache_dirs(os.getcwd())
                time.sleep(interval)

        t = threading.Thread(target=cleaner, daemon=True)
        t.start()
