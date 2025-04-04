import os
import re
import time
import json
import socket
import hashlib
import requests

from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .utils import basedir, log, default_export_path
from .config import DEFAULT_EXTENSION, AUTO_EXTENSIONS
from .session import Session

class Scraptor:
    """
    Scraptor is a site-mirroring utility for extracting and downloading 
    full web pages including their assets like images, CSS, JS, video, and audio files.

    It can crawl a single page or the entire domain, preserving folder structures 
    for accurate offline browsing.
    """

    def __init__(self, downloads=None, session=None, export_path=None, debug=False, logger=None):
        """
        Initializes the Scraptor instance.
        
        Args:
            downloads (str): Root directory where downloaded websites will be stored.
                If None, defaults to default_export_path() (typically Desktop on Windows/Linux or Downloads on mobile).
            session (requests.Session, optional): Custom or Tor-enabled session.
            export_path (str, optional): Directory where exported JSON profiles will be saved.
                If None, defaults to default_export_path().
            debug (bool, optional): Enable debug logging.
            logger (callable, optional): Custom logger. If not provided, uses global log().
        """
        self.visited = set()
        self.session = session or Session().session
        # Use the default_export_path from utils if not provided.
        self.downloads = downloads if downloads else default_export_path()
        self.export_path = export_path if export_path else default_export_path()
        os.makedirs(self.downloads, exist_ok=True)
        os.makedirs(self.export_path, exist_ok=True)

        self.soup = None
        self.last_url = None
        self.debug = debug
        self.logger = logger or (lambda msg, level="INFO": log(msg, level=level, debug=self.debug))

    @classmethod
    def this(cls, url, download_source=False, downloads=None, session=None):
        """
        Download only the given page and its assets.

        Args:
            url (str): The URL to scrape.
            download_source (bool): Whether to download assets (CSS, images, etc.).
        """
        instance = cls(downloads=downloads, session=session)
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
        instance = cls(downloads=downloads, session=session or requests.Session())
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
    
    @classmethod
    def extract(cls, url, output_path="Scraptor.json", session=None):
        instance = cls(downloads=None, session=session)
        return instance.extract_page(url, output_path)
    
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
    
    @classmethod
    def get(cls, url, mode="video", session=None):
        """
        Downloads specific content type from a page: video, image or text.

        Args:
            url (str): Target URL.
            mode (str): 'video', 'image', or 'text'.
            session (requests.Session): Optional session override.

        Returns:
            list or dict: List of file paths (for media) or dict of text/html file paths (for text).
        """
        assert mode in ("video", "image", "text"), "Mode must be 'video', 'image', or 'text'"

        instance = cls(downloads=None, session=session)
        url = instance._normalize_url(url)

        try:
            response = instance.session.get(url, timeout=15)
            if response.status_code != 200:
                instance.logger(f"[Scraptor] HTTP {response.status_code}: {url}", level="WARNING")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            parsed = urlparse(url)
            hostname = parsed.hostname.replace(".", "_")
            target_dir = os.path.join(instance.downloads, hostname, mode + "s")
            os.makedirs(target_dir, exist_ok=True)

            if mode == "text":
                for tag in soup(["form", "input", "iframe", "textarea", "script", "style"]):
                    tag.decompose()

                text = soup.get_text(separator=" ", strip=True)

                text_file = os.path.join(target_dir, "page.txt")
                html_file = os.path.join(target_dir, "page.html")

                with open(text_file, "w", encoding="utf-8") as f:
                    f.write(text)

                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(str(soup))

                instance.logger(f"[Scraptor] Text content saved to {text_file}", level="INFO")
                instance.logger(f"[Scraptor] Clean HTML saved to {html_file}", level="INFO")
                return {"text": text_file, "html": html_file}

            media_tags = {
                "video": ["video", "source"],
                "image": ["img"]
            }

            media_attrs = {
                "video": ["src", "poster"],
                "image": ["src"]
            }

            saved = []

            for tag in media_tags[mode]:
                for el in soup.find_all(tag):
                    for attr in media_attrs[mode]:
                        src = el.get(attr)
                        if not src:
                            continue
                        if src.startswith("data:") or src.startswith("blob:"):
                            instance.logger(f"[Scraptor] Skipped inline asset: {src[:40]}...", level="INFO")
                            continue

                        media_url = urljoin(url, src)
                        filename = os.path.basename(urlparse(media_url).path)
                        local_path = os.path.join(target_dir, filename)

                        try:
                            media_resp = instance.session.get(media_url, timeout=10)
                            if media_resp.status_code == 200:
                                with open(local_path, "wb") as f:
                                    f.write(media_resp.content)
                                instance.logger(f"[Scraptor] Saved {mode}: {local_path}", level="INFO")
                                saved.append(local_path)
                        except Exception as e:
                            instance.logger(f"[Scraptor] Failed to get {mode} {media_url}: {e}", level="ERROR")

            return saved

        except Exception as e:
            instance.logger(f"[Scraptor] ERROR: get({mode}) failed - {e}", level="ERROR")
            return [] if mode != "text" else None

    def _resolve_output_path(self, output_path, default_filename="Scraptor.json", fallback_folder="results"):
        """
        Handles logic for default output path resolution.
        """
        if not output_path or output_path.strip() == "":
            output_path = os.path.join(os.getcwd(), default_filename)

        if os.path.isdir(output_path) or output_path.endswith(("/", "\\")):
            output_path = os.path.join(output_path, default_filename)

        return output_path

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
                    self.logger(f"[Scraptor] Skipped {current} (status {response.status_code})", level="WARNING")
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
                self.logger(f"[Scraptor] ERROR crawling {current}: {e}", level="ERROR")

    def _scrape_page(self, url, download_source):
        """
        Downloads a single page and optionally its assets.
        """
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                self.logger(f"[Scraptor] HTTP {response.status_code}: {url}", level="WARNING")
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
            self.logger(f"[Scraptor] ERROR scraping {url}: {e}", level="ERROR")

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

        self.logger(f"[Scraptor] Saved page: {local_path}", level="INFO")
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
                        self.logger(f"[Scraptor] Skipped inline asset: {src[:40]}...", level="INFO")
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
                            self.logger(f"[Scraptor] Downloaded asset: {local_path}", level="INFO")
                            downloaded.add(asset_url)

                            relative_path = os.path.relpath(local_path, start=os.path.dirname(self._save_page_path)).replace("\\", "/")
                            el[attr] = relative_path
                    except Exception as e:
                        self.logger(f"[Scraptor] Failed to download asset {asset_url}: {e}", level="ERROR")

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
    
    @classmethod
    def inspect(cls, url, session=None):
        instance = cls(downloads=None, session=session)
        url = instance._normalize_url(url)

        try:
            r = instance.session.get(url, timeout=10)
            return {
                "url": url,
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "content_type": r.headers.get("Content-Type"),
                "size_kb": round(len(r.content) / 1024, 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def extract_page(self, url, output_path=""):
        """
        Extracts all available metadata, headers, and forensic info from a single HTML page
        and saves it in a JSON file.

        Args:
            url (str): The target URL to analyze.
            output_path (str): Where to save the resulting data.

        Returns:
            str: Path to the saved JSON file.
        """
        output_path = self._resolve_output_path(output_path)

        def check_allowed_methods(url, session):
            try:
                r = session.options(url, timeout=10)
                return r.headers.get("Allow")
            except:
                return None

        def analyze_cookies(headers):
            results = []
            cookies = headers.get("Set-Cookie", "")
            if "PHPSESSID" in cookies:
                results.append("PHP session detected")
            if "laravel_session" in cookies:
                results.append("Laravel backend")
            if "JSESSIONID" in cookies:
                results.append("Java backend (Tomcat or Spring)")
            if "Secure" not in cookies:
                results.append("Cookie NOT marked Secure")
            if "HttpOnly" not in cookies:
                results.append("Cookie NOT marked HttpOnly")
            return results

        def basic_header_analysis(headers):
            flags = []
            if "X-Powered-By" in headers:
                flags.append(f"Reveals tech stack: {headers['X-Powered-By']}")
            if "Server" in headers and "Apache" in headers["Server"]:
                flags.append("Apache detected")
            if "Strict-Transport-Security" not in headers:
                flags.append("Missing HSTS (vulnerable to downgrade attack)")
            return flags

        url = self._normalize_url(url)

        try:
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                self.logger(f"[Scraptor] HTTP {response.status_code}: {url}", level="WARNING")
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            favicon_hash = None
            try:
                fav_url = urljoin(url, "/favicon.ico")
                fav_resp = self.session.get(fav_url, timeout=10)
                if fav_resp.status_code == 200:
                    favicon_hash = hashlib.md5(fav_resp.content).hexdigest()
            except:
                pass

            founding_year = None
            copyright_tags = soup.find_all(string=re.compile(r"©|copyright|\d{4}"))
            years = re.findall(r"\b(19|20)\d{2}\b", " ".join(copyright_tags))
            if years:
                founding_year = min(set(years))

            headers = dict(response.headers)
            analysis = {
                "favicon_hash": favicon_hash,
                "founded_guess": founding_year,
                "allowed_methods": check_allowed_methods(url, self.session),
                "cookie_analysis": analyze_cookies(headers),
                "header_flags": basic_header_analysis(headers)
            }

            data = {
                "url": url,
                "title": soup.title.string if soup.title else None,
                "headers": headers,
                "meta": [
                    {tag.get("name") or tag.get("property"): tag.get("content")}
                    for tag in soup.find_all("meta") if tag.get("content")
                ],
                "links": [a.get("href") for a in soup.find_all("a", href=True)],
                "images": [img.get("src") for img in soup.find_all("img", src=True)],
                "scripts": [s.get("src") for s in soup.find_all("script", src=True)],
                "stylesheets": [l.get("href") for l in soup.find_all("link", rel="stylesheet")],
                "forms": [f.get("action") for f in soup.find_all("form") if f.get("action")],
                "text_snippet": soup.get_text(separator=" ", strip=True)[:1000],
                "analysis": analysis
            }

            dir_path = os.path.dirname(output_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.logger(f"[Scraptor] Full profile exported to {output_path}", level="INFO")
            return output_path

        except Exception as e:
            self.logger(f"[Scraptor] ERROR: Recon failed due to {e}", level="ERROR")
            return None

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
