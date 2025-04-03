import requests
from .config import CONFIG
from .nightcrawler import Nightcrawler
from .utils import rotate_ip

class Vigilante:
    def __init__(self, security="1", export_json=False):
        self.security = str(security)
        self.export_json = export_json

        self.headers = CONFIG["HEADERS"]
        self.timeout = CONFIG["TIMEOUT"]
        self.tor_enabled = True
        self.proxy = self._get_working_tor_proxy()
        self.ip_type = "dynamic" if self.security in ["1", "2"] else "static"
        
        tor_session = requests.Session()
        if self.proxy:
            tor_session.proxies.update(self.proxy)
            tor_session.headers.update(self.headers)
        self.nightcrawler = Nightcrawler(tor_session=tor_session, parent=self)

        if self.security in ["1", "2"] and self.proxy:
            rotate_ip()

        self.ip_info = self._check_environment()

    def _get_working_tor_proxy(self):
        proxy_list = CONFIG.get("TOR_PROXIES", [])
        for proxy_obj in proxy_list:
            scheme = proxy_obj["scheme"]
            proxy = proxy_obj["proxy"]
            try:
                res = requests.get(
                    "http://check.torproject.org",
                    proxies={scheme: proxy},
                    headers=self.headers,
                    timeout=self.timeout
                )
                if "Congratulations" in res.text:
                    return {scheme: proxy}
            except:
                continue
        return None

    def _check_environment(self):
        try:
            ip_service = "https://api.ipify.org?format=json"
            kwargs = {
                "headers": self.headers,
                "timeout": self.timeout
            }
            if self.tor_enabled and self.proxy:
                kwargs["proxies"] = self.proxy
                if self.security == "2":
                    kwargs["timeout"] += 5
                    kwargs["headers"]["X-Security-Level"] = "High"

            res = requests.get(ip_service, **kwargs)
            ip_data = res.json() if res.status_code == 200 else {}
            ip_data["security_level"] = self.security
            ip_data["ip_type"] = self.ip_type
            ip_data["proxy_used"] = self.proxy
            return ip_data

        except Exception as e:
            return {
                "error": str(e),
                "security_level": self.security,
                "ip_type": self.ip_type,
                "proxy_used": self.proxy
            }
