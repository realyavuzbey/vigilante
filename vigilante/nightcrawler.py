import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from .utils import export_data, log, default_export_path
from .session import Session

class Nightcrawler:
    """
    Nightcrawler performs dark web keyword searches using Tor,
    supports multiple search engines, and exports results in various formats.

    Attributes:
        session (requests.Session): A Tor-enabled session for making requests.
        export_as (str or None): The export format for the results ("json", "csv", "markdown", "txt").
        export_path (str): The directory where the exported file will be saved.
        logger (callable): A logging function that uses the global log() function.
    """

    def __init__(self, session=None, export_as=None, export_path=None, debug=False):
        """
        Initializes the Nightcrawler with an optional custom session, export format, export path, and debug flag.

        Args:
            session (requests.Session, optional): Custom Tor-enabled session.
                If not provided, a default Tor session is used.
            export_as (str, optional): Format to export results ("json", "csv", "markdown", "txt").
                If None, no export is performed.
            export_path (str, optional): Directory where the export file is saved.
                If None, defaults to the Desktop for Windows/Linux, or Downloads on mobile devices.
            debug (bool, optional): Enables debug logging when True.
        """
        self.session = session if session else Session().session
        self.export_as = export_as
        self.debug = debug
        self.logger = lambda msg, level="INFO": log(msg, level=level, debug=self.debug)
        self.export_path = export_path if export_path else default_export_path()

    def _parse_tordex(self, html):
        """
        Parses HTML content from Tordex and extracts structured search results.

        Args:
            html (str): HTML content to be parsed.

        Returns:
            list: A list of dictionaries containing the title, URL, description, and domain.
        """
        results = []
        soup = BeautifulSoup(html, "html.parser")
        # Each result is contained in a div with class 'result'
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
        """
        Parses HTML content from Ahmia and extracts structured search results.

        Args:
            html (str): HTML content to be parsed.

        Returns:
            list: A list of dictionaries containing the title, URL, description, and domain.
        """
        results = []
        soup = BeautifulSoup(html, "html.parser")
        # Each result is contained in a li element with class 'result'
        for li in soup.select("li.result"):
            title_tag = li.find("h4")
            desc_tag = li.find("p")
            cite_tag = li.find("cite")
            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            a_tag = title_tag.find("a") if title_tag else None
            raw_href = a_tag["href"] if a_tag and "href" in a_tag.attrs else ""
            # Build full URL if necessary
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

    def _parse_tor66(self, html):
        """
        Parses HTML content from Tor66 and extracts structured search results.

        Args:
            html (str): HTML content to be parsed.

        Returns:
            list: A list of dictionaries containing the title, URL, description, and domain.
        """
        results = []
        soup = BeautifulSoup(html, "html.parser")
        # Find all anchor tags with an href attribute
        anchors = soup.find_all("a", href=True)

        for a in anchors:
            href = a['href']
            # Check for specific URL patterns typical for Tor66 results
            if "url.php?u=" in href and ".onion" in href:
                try:
                    # Extract the onion URL from the query string
                    onion_url = href.split("url.php?u=")[1].split("&")[0]
                    title = a.get_text(strip=True) or "No Title"
                    domain = urlparse(onion_url).netloc or "Unknown"

                    # Get the description text that follows a <br> tag, if available
                    br_tag = a.find_next("br")
                    description = ""
                    if br_tag:
                        sibling = br_tag.next_sibling
                        if sibling and isinstance(sibling, str):
                            description = sibling.strip()
                    if not description:
                        description = "No Description"

                    results.append({
                        "title": title,
                        "url": onion_url,
                        "description": description,
                        "domain": domain
                    })
                except Exception:
                    continue

        return results

    def crawl(self, term, engine_overrides=None):
        """
        Searches for the provided term across multiple dark web search engines.

        Args:
            term (str): The keyword or phrase to search for.
            engine_overrides (dict, optional): Overrides for the search engine configurations.

        Returns:
            dict: A dictionary with search engine names as keys and lists of search result dictionaries as values.
        """
        base_q = quote(term)
        all_results = {}

        # Define search engines and their respective configurations
        search_engines = {
            "Ahmia": {
                "url": f"https://ahmia.fi/search/?q={base_q}",
                "parser": self._parse_ahmia
            },
            "Tordex": {
                "url": f"http://tordexu73joywapk2txdr54jed4imqledpcvcuf75qsas2gwdgksvnyd.onion/search?query={base_q}",
                "parser": self._parse_tordex
            },
            "Tor66": {
                "url": f"http://kn3hl4xwon63tc6hpjrwza2npb7d4w5yhbzq7jjewpfzyhsd65tm6dad.onion/search.php?search={base_q}&submit=Search&rt=",
                "parser": self._parse_tor66
            }
        }

        # Loop through each search engine and process the search
        for name, config in search_engines.items():
            if not config.get("active", True):
                continue

            parser = config["parser"]
            base_url = config["url"]
            results = []

            try:
                self.logger(f"[{name}] Fetching: {base_url}", level="INFO")
                response = self.session.get(base_url, timeout=15)

                if response.status_code != 200:
                    self.logger(f"[{name}] HTTP {response.status_code}", level="WARNING")
                    continue

                html = response.text
                page_results = parser(html) if parser else []
                results.extend(page_results)

                self.logger(f"[{name}] {len(results)} result(s) found.", level="INFO")
                all_results[name] = results
            except Exception as e:
                self.logger(f"[{name}] ERROR: {str(e)}", level="ERROR")
                all_results[name] = []

        # Export data if export format is specified
        if self.export_as:
            # The export_data function is expected to support the export_path parameter.
            export_data(all_results, export_as=self.export_as, export_path=self.export_path, class_name="Nightcrawler")

        return all_results
