import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
from .utils import export_data, log, default_export_path
from .session import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

class Nightcrawler:
    """
        Nightcrawler
        =====
        
        Nightcrawler is a Tor-powered, modular dark web intelligence harvester that enables
        keyword-based reconnaissance across multiple hidden service search engines (e.g., Tordex, Tor66).

        It leverages onion routing to maintain operational anonymity, supports flexible export formats 
        (JSON, CSV, Markdown, TXT), and offers customizable search workflows through session injection 
        and parser overrides.

        Designed for OSINT analysts, security researchers, and threat intelligence operations, 
        Nightcrawler abstracts search engine quirks and standardizes output for post-processing or integration 
        into automated pipelines.

        Attributes:
            session (requests.Session): A Tor-routed HTTP session ensuring anonymized requests.
            export_as (str or None): The desired output format for results, supporting "json", "csv", "markdown", or "txt".
            export_path (str): Directory path where the final exported file will be saved; defaults are OS-aware.
            logger (callable): Hook for structured logging; uses centralized log() utility with debug-level control.
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
        anchors = soup.find_all("a", href=True)

        for a in anchors:
            href = a['href']
            if "url.php?u=" in href and ".onion" in href:
                try:
                    onion_url = href.split("url.php?u=")[1].split("&")[0]
                    title = a.get_text(strip=True) or "No Title"
                    domain = urlparse(onion_url).netloc or "Unknown"

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

    def is_alive(self, url):
        """
        Checks if the given URL is reachable over Tor.

        Args:
            url (str): The .onion URL to check.

        Returns:
            bool: True if reachable, False otherwise.
        """
        try:
            res = self.session.get(url, timeout=10, allow_redirects=True)
            return res.status_code < 500
        except Exception as e:
            return False

    def crawl(self, term, engine_overrides=None, check_alive=False):
        """
        Searches for the provided term across multiple dark web search engines.

        Args:
            term (str): The keyword or phrase to search for.
            engine_overrides (dict, optional): Overrides for the search engine configurations.
            check_alive (bool, optional): If True, verifies if each URL is reachable.

        Returns:
            dict: A dictionary with search engine names as keys and lists of search result dictionaries as values.
        """
        base_q = quote(term)
        all_results = {}

        search_engines = {
            "Tordex": {
                "url": f"http://tordexu73joywapk2txdr54jed4imqledpcvcuf75qsas2gwdgksvnyd.onion/search?query={base_q}",
                "parser": self._parse_tordex
            },
            "Tor66": {
                "url": f"http://kn3hl4xwon63tc6hpjrwza2npb7d4w5yhbzq7jjewpfzyhsd65tm6dad.onion/search.php?search={base_q}&submit=Search&rt=",
                "parser": self._parse_tor66
            }
        }

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

                if check_alive and page_results:
                    self.logger(f"[{name}] Checking {len(page_results)} links in parallel (20 threads)...", level="INFO")

                    def _check_single(result):
                        url = result["url"]
                        result["alive"] = self.is_alive(url)
                        return result

                    with ThreadPoolExecutor(max_workers=20) as executor:
                        future_to_result = {executor.submit(_check_single, r): r for r in page_results}
                        for future in as_completed(future_to_result):
                            result = future.result()
                            self.logger(f"[{name}] Checked: {result['url']} → {'LIVE' if result['alive'] else 'DEAD'}", level="DEBUG")

                results.extend(page_results)

                self.logger(f"[{name}] {len(results)} result(s) found.", level="INFO")
                all_results[name] = results
            except Exception as e:
                self.logger(f"[{name}] ERROR: {str(e)}", level="ERROR")
                all_results[name] = []

        if self.export_as:
            export_data(all_results, export_as=self.export_as, export_path=self.export_path, class_name="Nightcrawler")

        return all_results
