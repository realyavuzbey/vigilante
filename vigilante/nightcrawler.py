import requests
from urllib.parse import urljoin, urlparse
import time
from .config import TOR_PROXY

class Nightcrawler:
    """
    Nightcrawler is a class for deep web crawling.

    Attributes:
        start_url (str): The URL from which to start crawling.
        depth (int): The depth of crawling.
        use_tor (bool): Whether to route requests via the Tor network for anonymity.
        stealth_mode (bool): Whether to run in stealth mode to avoid detection.
    """

    def __init__(self, start_url, depth=1, use_tor=False, stealth_mode=False):
        self.start_url = start_url
        self.depth = depth
        self.use_tor = use_tor
        self.stealth_mode = stealth_mode
        self.visited = set()

        # Set session with optional Tor proxy
        self.session = requests.Session()
        if self.use_tor:
            self.session.proxies.update(TOR_PROXY)

        logging.info(f"Nightcrawler initialized with URL: {self.start_url}")

    def hunt(self, keywords=None):
        """
        Starts crawling from the start URL.

        Args:
            keywords (list, optional): A list of keywords to search for.

        Returns:
            list: A list of simulated crawl results or keyword matches.
        """
        logging.info(f"Starting hunt at {self.start_url} (depth={self.depth})")

        if self.use_tor:
            logging.info("Tor routing enabled.")

        if self.stealth_mode:
            logging.info("Stealth mode is ON. Delay and headers will be applied.")

        if keywords:
            logging.info(f"Looking for keywords: {keywords}")
        else:
            logging.info("No keywords provided. Performing general crawl.")

        results = self._crawl(self.start_url, self.depth, keywords)
        return results

    def _crawl(self, url, depth, keywords):
        """
        Internal recursive crawler function.

        Args:
            url (str): URL to crawl.
            depth (int): Remaining depth.
            keywords (list): Keywords to search for.

        Returns:
            list: Found items.
        """
        if depth == 0 or url in self.visited:
            return []

        logging.debug(f"Crawling {url}")
        self.visited.add(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VigilanteBot/1.0; +https://pypi.org/project/vigilante/)"
        }

        try:
            if self.stealth_mode:
                time.sleep(2)

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text

            found = []
            if keywords:
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        found.append((url, keyword))
                        logging.info(f"Keyword '{keyword}' found at: {url}")
            else:
                found.append(url)

            # Example: You could parse links here for deeper crawling
            # (Skipped for simplicity)

            return found

        except requests.RequestException as e:
            logging.warning(f"Request failed for {url}: {e}")
            return []

    def __repr__(self):
        return (
            f"<Nightcrawler(start_url='{self.start_url}', depth={self.depth}, "
            f"use_tor={self.use_tor}, stealth_mode={self.stealth_mode})>"
        )