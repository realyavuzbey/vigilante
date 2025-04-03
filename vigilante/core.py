import requests
from .config import CONFIG
from .nightcrawler import Nightcrawler
from .utils import rotate_ip, export_json_result


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
        tor_session (requests.Session): A session configured with Tor proxies.
        nightcrawler (Nightcrawler): Instance for crawling dark web search engines.
        ip_info (dict): Information about the current IP environment.
    """

    def __init__(self, security="1", export_json=False):
        """
        Initialize the Vigilante instance with security settings and a Tor session.

        Args:
            security (str, optional): The security level. Defaults to "1".
            export_json (bool, optional): If True, exports results in JSON. Defaults to False.
        """
        self.security = str(security)
        self.export_json = export_json

        # Load configuration from CONFIG
        self.headers = CONFIG["HEADERS"]
        self.timeout = CONFIG["TIMEOUT"]
        self.tor_enabled = True

        # Configure Tor proxy settings (adjust port if necessary)
        self.proxy = {
            "http": "socks5h://127.0.0.1:9150",
            "https": "socks5h://127.0.0.1:9150"
        }
        
        # Set IP type based on security level
        self.ip_type = "dynamic" if self.security in ["1", "2"] else "static"

        # Setup Tor-enabled session
        self.tor_session = requests.Session()
        self.tor_session.proxies.update(self.proxy)
        self.tor_session.headers.update(self.headers)

        # Initialize Nightcrawler with the Tor session
        self.nightcrawler = Nightcrawler(tor_session=self.tor_session)

        # Rotate IP if using dynamic IP security levels
        if self.security in ["1", "2"]:
            rotate_ip()

        # Check and store the current IP environment information
        self.ip_info = self._check_environment()

    def _check_environment(self):
        """
        Check the current network environment using an external IP service.

        Returns:
            dict: A dictionary containing IP information along with security level,
                  IP type, and proxy details.
        """
        try:
            ip_service = "https://api.ipify.org?format=json"
            kwargs = {
                "headers": self.headers,
                "timeout": self.timeout,
                "proxies": self.proxy
            }

            # Adjust settings for higher security level if needed
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
