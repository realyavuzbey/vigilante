import os
import re
import time
import json
import requests

from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .utils import basedir
from .config import DEFAULT_EXTENSION, AUTO_EXTENSIONS
from .session import Session
from tqdm import tqdm

downloads = basedir("downloads/websites")

class Scraptor:
    """
    Scraptor is a site-mirroring utility for extracting and downloading 
    full web pages including their assets like images, CSS, JS, video, and audio files.

    It can crawl a single page or the entire domain, preserving folder structures 
    for accurate offline browsing.
    """

    def __init__(self, downloads, session=None, debug=False):
        """
        Initializes the Scraptor instance.
        
        Args:
            downloads (str): Root directory where downloaded websites will be stored.
            session (requests.Session, optional): Custom or Tor-enabled session.
        """
        self.visited = set()
        self.session = session or Session().session
        self.downloads = downloads
        os.makedirs(self.downloads, exist_ok=True)
        self.soup = None
        self.last_url = None

    @classmethod
    def this(cls, url, download_source=False, downloads=None, session=None):
        """
        Download only the given page and its assets.

        Args:
            url (str): The URL to scrape.
            download_source (bool): Whether to download assets (CSS, images, etc.).
        """
        instance = cls(downloads or basedir("downloads/websites"), session=session)
        normalized_url = instance._normalize_url(url)
        instance._scrape_page(normalized_url, download_source=download_source)
        return instance

    @classmethod
    def all(cls, url, download_source=False, downloads=None, session=None):
        """
        Recursively crawl the given domain, downloading all internal pages and their assets.

        Args:
            url (str): The root URL to start crawling.
            download_source (bool): Whether to download assets (CSS, images, etc.).
        """
        instance = cls(downloads or basedir("downloads/websites"), session=session or requests.Session())
        normalized_url = instance._normalize_url(url)
        instance._crawl_all(normalized_url, download_source=download_source)
        return instance
    
    @staticmethod
    def _normalize_url(url):
        """
        Ensures the URL has a proper scheme. Defaults to http:// if missing.
        """
        parsed = urlparse(url)
        if not parsed.scheme:
            return "http://" + url
        return url
    
    def find(self, selector):
        """
        Perform a CSS-style selector query on the last loaded page.

        Args:
            selector (str): CSS selector.

        Returns:
            ScraptorResultSet: Object for .all() or .first() access.
        """
        if not self.soup:
            raise ValueError("No page loaded. Use `this()` or `all()` first.")
        return ScraptorResultSet(self.soup.select(selector))

    def _crawl_all(self, url, download_source):
        """
        Crawl and download all internal pages and assets of a domain.
        """
        queue = [url]
        while queue:
            current = queue.pop(0)
            if current in self.visited:
                continue
            self.visited.add(current)

            parsed = urlparse(current)
            base_domain = parsed.netloc
            save_path = os.path.join(self.downloads, base_domain)
            os.makedirs(save_path, exist_ok=True)

            try:
                response = self.session.get(current, timeout=15)
                if response.status_code != 200:
                    print(f"[Scraptor] Skipped {current} (status {response.status_code})")
                    continue

                self.last_url = current
                html = response.text
                self.soup = BeautifulSoup(html, "html.parser")

                local_path = self._save_page(current, html, save_path)

                if download_source:
                    self._download_assets(self.soup, current, save_path)

                links = self._extract_links(self.soup, current)
                queue.extend(links)

            except Exception as e:
                print(f"[Scraptor] ERROR crawling {current}: {e}")

    def _scrape_page(self, url, download_source):
        """
        Downloads a single page and optionally its assets.
        """
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                print(f"[Scraptor] HTTP {response.status_code}: {url}")
                return

            self.last_url = url
            html = response.text
            self.soup = BeautifulSoup(html, "html.parser")

            parsed = urlparse(url)
            base_domain = parsed.netloc
            save_path = os.path.join(self.downloads, base_domain)
            os.makedirs(save_path, exist_ok=True)

            self._save_page(url, html, save_path)

            if download_source:
                self._download_assets(self.soup, url, save_path)

        except Exception as e:
            print(f"[Scraptor] ERROR scraping {url}: {e}")

    def _save_page(self, url, html, root_path):
        """
        Saves the HTML content to local disk and records the path for later asset linking.
        """
        parsed = urlparse(url)
        path = parsed.path if parsed.path else "/"
        if path.endswith("/"):
            path += f"index{DEFAULT_EXTENSION}"
        elif not any(path.endswith(ext) for ext in AUTO_EXTENSIONS):
            path += DEFAULT_EXTENSION

        sanitized_path = self._sanitize_path(path.lstrip("/"))
        local_path = os.path.join(root_path, sanitized_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        self._save_page_path = local_path
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"[Scraptor] Saved page: {local_path}")
        return local_path

    def _sanitize_path(self, path):
        """
        Sanitize file path for filesystem safety (removes illegal characters).
        """
        return os.path.sep.join([
            re.sub(r'[<>:"\\|?*#]', '_', part) for part in path.split('/')
        ])

    def _download_assets(self, soup, base_url, root_path):
        """
        Downloads images, CSS, JS, video, and audio assets from the page.
        Rewrites HTML references to point to local versions.
        """
        tags = {
            "img": "src",
            "script": "src",
            "link": "href",
            "source": "src",
            "iframe": "src",
            "video": ["src", "poster"],
            "audio": "src"
        }
        downloaded = set()

        for tag, attrs in tags.items():
            if isinstance(attrs, str):
                attrs = [attrs]

            for el in soup.find_all(tag):
                for attr in attrs:
                    src = el.get(attr)
                    if not src:
                        continue
                    if src.startswith("blob:") or src.startswith("data:"):
                        print(f"[Scraptor] Skipped inline asset: {src[:40]}...")
                        continue

                    asset_url = urljoin(base_url, src)
                    parsed_url = urlparse(asset_url)
                    raw_path = parsed_url.path.lstrip("/")
                    sanitized_path = self._sanitize_path(raw_path)
                    local_path = os.path.join(root_path, sanitized_path)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    try:
                        response = self.session.get(asset_url, timeout=10)
                        if response.status_code == 200:
                            with open(local_path, "wb") as f:
                                f.write(response.content)
                            print(f"[Scraptor] Downloaded asset: {local_path}")
                            downloaded.add(asset_url)

                            relative_path = os.path.relpath(local_path, start=os.path.dirname(self._save_page_path)).replace("\\", "/")
                            el[attr] = relative_path
                    except Exception as e:
                        print(f"[Scraptor] Failed to download asset {asset_url}: {e}")

        # Save the modified HTML with updated paths
        with open(self._save_page_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

    def _extract_links(self, soup, base_url):
        """
        Extracts all internal links from the current page for recursive crawling.
        """
        links = []
        base_domain = urlparse(base_url).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(base_url, href)
            if urlparse(absolute).netloc == base_domain:
                links.append(absolute)
        return links

    def extract(self, url, output_dir="results"):
        """
        Crawls the site and exports structured HTML data from each page to a single JSON.

        Args:
            url (str): Root URL to start crawling.
            output_dir (str): Folder to save JSON output.

        Returns:
            str: Path to the saved JSON file.
        """
        self.visited = set()
        result = {}

        def scrape_data_from_soup(soup, current_url):
            return {
                "url": current_url,
                "title": soup.title.string if soup.title else None,
                "meta": [
                    {tag.get("name") or tag.get("property"): tag.get("content")}
                    for tag in soup.find_all("meta") if tag.get("content")
                ],
                "links": [a.get("href") for a in soup.find_all("a", href=True)],
                "images": [img.get("src") for img in soup.find_all("img", src=True)],
                "scripts": [s.get("src") for s in soup.find_all("script", src=True)],
                "stylesheets": [l.get("href") for l in soup.find_all("link", rel="stylesheet")],
                "forms": [f.get("action") for f in soup.find_all("form") if f.get("action")],
                "text": soup.get_text(separator=" ", strip=True)[:500]  # First 500 chars
            }

        queue = [self._normalize_url(url)]

        while queue:
            current = queue.pop(0)
            if current in self.visited:
                continue
            self.visited.add(current)

            try:
                response = self.session.get(current, timeout=15)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                result[current] = scrape_data_from_soup(soup, current)

                for a in soup.find_all("a", href=True):
                    href = urljoin(current, a["href"])
                    if urlparse(href).netloc == urlparse(url).netloc and href not in self.visited:
                        queue.append(href)

            except Exception as e:
                result[current] = {"error": str(e)}

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outpath = os.path.join(output_dir, f"Scraptor_{timestamp}.json")

        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        print(f"[Scraptor] Exported structured data to {outpath}")
        return outpath

class ScraptorResultSet:
    """
    A result wrapper for selected elements on a page.
    """

    def __init__(self, elements):
        self.elements = elements

    def all(self):
        """
        Returns all matched elements.
        """
        return self.elements

    def first(self):
        """
        Returns the first matched element, or None.
        """
        return self.elements[0] if self.elements else None
    
    def extract(self, attrs=None):
        """
        Extracts useful info from all elements.

        Args:
            attrs (list or str, optional): Specific attribute(s) to extract. 
                If None, returns text content. If list, pulls all specified attrs.

        Returns:
            list: Extracted text or attribute values from elements.
        """
        results = []

        for el in self.elements:
            if attrs is None:
                results.append(el.get_text(strip=True))
            elif isinstance(attrs, str):
                results.append(el.get(attrs, None))
            elif isinstance(attrs, list):
                results.append({attr: el.get(attr, None) for attr in attrs})

        return results
