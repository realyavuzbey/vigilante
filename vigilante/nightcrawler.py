import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from .utils import export_data
from .session import Session

class Nightcrawler:
    """
    Nightcrawler searches for a given term on dark web search engines (Tordex and Ahmia)
    using a Tor-enabled session. It parses the HTML results and returns structured data.

    Attributes:
        tor (requests.Session): The Tor-enabled session used for sending HTTP requests.
        export_as (str): Format to export the results ("json", "csv", "markdown").
        logger (callable): Logger function for outputting messages (default is print).
    """

    def __init__(self, tor_session=None, export_as=None):
        """
        Initialize the Nightcrawler instance.

        Args:
            tor_session (requests.Session, optional): The session configured with Tor proxies.
                If None, a default session will be created.
            export_as (str, optional): Format to export results ("json", "csv", "markdown").
                Defaults to None (no export).
        """
        if tor_session is None:
            self.tor = Session().session
        else:
            self.tor = tor_session
        self.export_as = export_as
        self.logger = print

    def _parse_tordex(self, html):
        results = []
        soup = BeautifulSoup(html, "html.parser")
        for block in soup.select("div.result"):
            title_tag = block.find("h5")
            link_tag = block.find("h6")
            a_tag = link_tag.find("a") if link_tag else None
            desc_tag = block.find("p")

            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            url_text = a_tag.get_text(strip=True) if a_tag else ""
            description = desc_tag.get_text(strip=True) if desc_tag else "No Description"
            domain = urlparse(url_text).netloc or "Unknown"

            results.append({
                "title": title,
                "url": url_text,
                "description": description,
                "domain": domain
            })
        return results

    def _parse_ahmia(self, html):
        results = []
        soup = BeautifulSoup(html, "html.parser")
        for li in soup.select("li.result"):
            title_tag = li.find("h4")
            desc_tag = li.find("p")
            cite_tag = li.find("cite")

            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            a_tag = title_tag.find("a") if title_tag else None
            raw_href = a_tag["href"] if a_tag and "href" in a_tag.attrs else ""
            full_url = f"https://ahmia.fi{raw_href}" if raw_href.startswith("/") else raw_href
            description = desc_tag.get_text(strip=True) if desc_tag else "No Description"
            domain = cite_tag.get_text(strip=True) if cite_tag else "Unknown"

            results.append({
                "title": title,
                "url": full_url,
                "description": description,
                "domain": domain
            })
        return results

    def crawl(self, term, engine_overrides=None):
        """
        Crawl the dark web search engines for the given term.

        Args:
            term (str): The search term to query.
            engine_overrides (dict, optional): Optional headers/timeouts per engine.

        Returns:
            dict: A dictionary with engine names as keys and lists of search results as values.
        """
        engines = {
            "Tordex": f"http://tordexu73joywapk2txdr54jed4imqledpcvcuf75qsas2gwdgksvnyd.onion/search?query={quote(term)}",
            "Ahmia": f"https://ahmia.fi/search/?q={quote(term)}"
        }

        all_results = {}

        for name, url in engines.items():
            try:
                overrides = engine_overrides.get(name, {}) if engine_overrides else {}
                engine_headers = overrides.get("headers", {})
                engine_timeout = overrides.get("timeout", 15)

                self.logger(f"[{name}] Sending request: {url}")
                response = self.tor.get(url, headers=engine_headers, timeout=engine_timeout)

                if response.status_code != 200:
                    self.logger(f"[{name}] HTTP {response.status_code}")
                    all_results[name] = []
                    continue

                html = response.text

                if name == "Tordex":
                    parsed = self._parse_tordex(html)
                elif name == "Ahmia":
                    parsed = self._parse_ahmia(html)
                else:
                    parsed = []

                self.logger(f"[{name}] {len(parsed)} results found.")
                all_results[name] = parsed

            except Exception as e:
                self.logger(f"[{name}] ERROR: {str(e)}")
                all_results[name] = []

        if self.export_as:
            export_data(all_results, export_as=self.export_as, class_name="Nightcrawler")

        return all_results
