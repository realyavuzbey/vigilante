import os
import re
import time
import requests
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from .utils import basedir
from .config import DEFAULT_EXTENSION, AUTO_EXTENSIONS
from .session import Session

downloads = basedir("downloads/websites")

class Scraptor:
    def __init__(self, downloads, session=None):
        self.visited = set()
        self.session = session or Session().session
        self.downloads = downloads
        os.makedirs(self.downloads, exist_ok=True)
        self.soup = None
        self.last_url = None

    @classmethod
    def this(cls, url, download_source=False, downloads=None, session=None):
        instance = cls(downloads or basedir("downloads/websites"), session=session)
        normalized_url = instance._normalize_url(url)
        instance._scrape_page(normalized_url, download_source=download_source)
        return instance

    @classmethod
    def all(cls, url, download_source=False, downloads=None, session=None):
        instance = cls(downloads or basedir("downloads/websites"), session=session or requests.Session())
        normalized_url = instance._normalize_url(url)
        instance._crawl_all(normalized_url, download_source=download_source)
        return instance

    def _normalize_url(self, url):
        parsed = urlparse(url)
        if not parsed.scheme:
            return "http://" + url
        return url

    def find(self, selector):
        if not self.soup:
            raise ValueError("No page loaded. Use `this()` or `all()` first.")
        return ScraptorResultSet(self.soup.select(selector))

    def _crawl_all(self, url, download_source):
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
        return os.path.sep.join([
            re.sub(r'[<>:"\\|?*#]', '_', part) for part in path.split('/')
        ])

    def _download_assets(self, soup, base_url, root_path):
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
                    if src.startswith("blob:"):
                        print(f"[Scraptor] Skipped blob URL: {src}")
                        continue
                    if src.startswith("data:"):
                        print(f"[Scraptor] Skipped data URI: {src[:40]}...")
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


    def _save_asset(self, asset_url, root_path):
        try:
            if asset_url.startswith("data:"):
                print(f"[Scraptor] Skipped data URI: {asset_url[:40]}...")
                return

            parsed = urlparse(asset_url)
            raw_path = parsed.path.lstrip("/")
            sanitized_path = self._sanitize_path(raw_path)

            local_path = os.path.join(root_path, sanitized_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            response = self.session.get(asset_url, timeout=10)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(response.content)
                print(f"[Scraptor] Downloaded asset: {local_path}")
        except Exception as e:
            print(f"[Scraptor] Failed to download asset {asset_url}: {e}")

    def _extract_links(self, soup, base_url):
        links = []
        base_domain = urlparse(base_url).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(base_url, href)
            if urlparse(absolute).netloc == base_domain:
                links.append(absolute)
        return links


class ScraptorResultSet:
    def __init__(self, elements):
        self.elements = elements

    def all(self):
        return self.elements

    def first(self):
        return self.elements[0] if self.elements else None
