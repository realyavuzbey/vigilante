from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from .utils import export_data
from .session import Session

class Nightcrawler:
    """
    Nightcrawler performs dark web keyword search via Tor,
    supports multiple engines and exports results in multiple formats.

    Attributes:
        tor (requests.Session): A Tor-enabled requests session.
        export_as (str or None): Export format - "json", "csv", "markdown", "txt" or None.
        logger (callable): Output function (default is print).
    """

    def __init__(self, tor_session=None, export_as=None):
        """
        Args:
            tor_session (requests.Session, optional): Custom Tor-enabled session.
                If not provided, a default Tor session will be used.
            export_as (str, optional): Output format for results.
                Supported values: "json", "csv", "markdown", "txt".
                If None, no export will be performed.
        """
        self.tor = tor_session if tor_session else Session().session
        self.export_as = export_as
        self.logger = print

    def _parse_tordex(self, html):
        """Parses HTML from Tordex and extracts structured results."""
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
        """Parses HTML from Ahmia and extracts structured results."""
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
        Searches for the provided term on supported dark web search engines.

        Args:
            term (str): Search keyword.
            engine_overrides (dict, optional): Custom headers or timeouts per engine.

        Returns:
            dict: Search results structured per engine.
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

                self.logger(f"[{name}] Fetching: {url}")
                response = self.tor.get(url, headers=engine_headers, timeout=engine_timeout)

                if response.status_code != 200:
                    self.logger(f"[{name}] HTTP {response.status_code}")
                    all_results[name] = []
                    continue

                html = response.text
                parser = getattr(self, f"_parse_{name.lower()}", None)
                parsed = parser(html) if parser else []

                self.logger(f"[{name}] {len(parsed)} result(s) found.")
                all_results[name] = parsed

            except Exception as e:
                self.logger(f"[{name}] ERROR: {str(e)}")
                all_results[name] = []

        if self.export_as:
            export_data(all_results, export_as=self.export_as, class_name="Nightcrawler")

        return all_results
