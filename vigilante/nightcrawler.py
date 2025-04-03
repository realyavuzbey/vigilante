import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import CONFIG, GLOBAL_TIMEOUT, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .utils import export_json_result

class Nightcrawler:
    def __init__(self, tor_session=None, parent=None):
        self.headers = CONFIG["HEADERS"]
        self.timeout = CONFIG["TIMEOUT"]
        self.session = tor_session or requests.Session()
        self.export = CONFIG.get("EXPORT", True)
        self.logger = None
        self.parent = parent
        self.proxy = parent.proxy if parent and hasattr(parent, "proxy") else CONFIG.get("TOR_PROXY")

    def crawl(self, query, search_type="all", export_json=True):
        encoded = quote(query)
        search_type = search_type.lower()

        result = {
            "query": query,
            "type": search_type,
            "status": "completed",
            "social_profiles": self._check_social_profiles(query),
            "search_engines": self._search_web(query, search_type),
            "darkweb": self._search_dark_web(encoded),
            "media_files": self._extract_all_media(query, search_type)
        }

        if export_json:
            os.makedirs("results", exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_json_result(result, class_name=f"Nightcrawler_{query}_{ts}")
            if self.logger:
                self.logger.add(f"[Nightcrawler] Exported Nightcrawler_{query}_{ts}.json")

        return result

    def _check_social_profiles(self, username):
        platforms = {
            "instagram": f"https://instagram.com/{username}",
            "twitter": f"https://twitter.com/{username}",
            "github": f"https://github.com/{username}",
            "youtube": f"https://www.youtube.com/@{username}",
            "reddit": f"https://www.reddit.com/user/{username}",
            "tiktok": f"https://www.tiktok.com/@{username}",
            "facebook": f"https://facebook.com/{username}"
        }

        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self._check_url, url): name
                for name, url in platforms.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                exists, _ = future.result()
                results[name] = exists
        return results

    def _check_url(self, url):
        try:
            res = self.session.get(url, headers=self.headers, timeout=self.timeout)
            return res.status_code == 200, url
        except:
            return False, url

    def _search_web(self, query, search_type):
        engines = {
            "duckduckgo": f"https://html.duckduckgo.com/html/?q={quote(query)}",
            "bing": f"https://www.bing.com/search?q={quote(query)}"
        }

        results = {}
        for name, url in engines.items():
            try:
                res = requests.get(url, headers=self.headers, timeout=self.timeout)
                soup = BeautifulSoup(res.text, "html.parser")
                items = []

                if search_type in ["text", "all"]:
                    for a in soup.find_all("a", href=True):
                        text = a.get_text(strip=True)
                        if query.lower() in text.lower():
                            items.append({"type": "text", "title": text, "link": a["href"]})

                if search_type in ["image", "all"]:
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if query.lower() in src.lower():
                            items.append({"type": "image", "src": src})

                if search_type in ["video", "all"]:
                    for tag in soup.find_all(["video", "source"]):
                        src = tag.get("src", "")
                        if query.lower() in src.lower():
                            items.append({"type": "video", "src": src})

                results[name] = items[:15]
            except Exception as e:
                results[name] = [{"error": str(e)}]

        return results

    def _search_dark_web(self, encoded):
        results = {}

        # AHmia
        try:
            ahmia_url = f"http://ahmia.fi/search/?q={encoded}"
            res = self.session.get(ahmia_url, headers=self.headers, timeout=self.timeout)
            soup = BeautifulSoup(res.text, "html.parser")
            items = []

            for li in soup.select("li.result"):
                title_tag = li.find("h4")
                desc_tag = li.find("p")
                a_tag = title_tag.find("a") if title_tag else None

                raw_href = a_tag["href"] if a_tag and a_tag.has_attr("href") else ""
                final_url = unquote(raw_href.split("redirect_url=")[-1]) if "redirect_url=" in raw_href else raw_href
                domain = urlparse(final_url).netloc or "No Domain"
                title = a_tag.get_text(strip=True) if a_tag else "No Title"
                desc = desc_tag.get_text(strip=True) if desc_tag else "No Description"

                items.append({
                    "title": title,
                    "url": final_url,
                    "description": desc,
                    "domain": domain
                })
            results["ahmia"] = items if items else [{"info": "no matches"}]
        except Exception as e:
            results["ahmia"] = [{"error": str(e)}]

        # Tordex (Requires working .onion proxy via Tor)
        try:
            tordex_url = f"http://tordexu73joywapk2txdr54jed4imqledpcvcuf75qsas2gwdgksvnyd.onion/search?onion=&query={encoded}"
            res = self.session.get(
                tordex_url,
                headers=self.headers,
                timeout=self.timeout,
                proxies={"http": self.proxy, "https": self.proxy}
            )
            soup = BeautifulSoup(res.text, "html.parser")
            items = []
            content_area = soup.find("div", class_="col-lg-8")
            if content_area:
                for block in content_area.select("div.result"):
                    title_tag = block.find("h5")
                    link_tag = block.find("h6 a") or block.find("h6")
                    desc_tag = block.find("p")

                    title_text = title_tag.get_text(strip=True) if title_tag else "No Title"
                    url_text = link_tag.get_text(strip=True) if link_tag else ""
                    desc_text = desc_tag.get_text(strip=True) if desc_tag else "No Description"
                    domain = urlparse(url_text).netloc or "Unknown"

                    items.append({
                        "title": title_text,
                        "url": url_text,
                        "description": desc_text,
                        "domain": domain
                    })
            results["tordex"] = items if items else [{"info": "no matches"}]
        except Exception as e:
            results["tordex"] = [{"error": str(e)}]

        return results

    def _extract_all_media(self, query, media_type):
        if media_type not in ["image", "video", "all"]:
            return []

        exts = IMAGE_EXTENSIONS if media_type == "image" else VIDEO_EXTENSIONS
        collected = set()

        def scan(url):
            try:
                html = self.session.get(url, headers=self.headers, timeout=10).text
                soup = BeautifulSoup(html, "html.parser")
                found = set()

                for tag in soup.find_all(src=True):
                    found.add(urljoin(url, tag["src"]))

                for tag in soup.find_all(href=True):
                    found.add(urljoin(url, tag["href"]))

                for tag in soup.find_all(style=True):
                    style = tag["style"]
                    matches = re.findall(r"url(.*?)", style)
                    for m in matches:
                        found.add(urljoin(url, m.strip(' "\'')))

                return [link for link in found if any(link.lower().endswith(ext) for ext in exts)]
            except:
                return []

        all_results = self._search_web(query, "text")
        urls = [i["link"] for engine in all_results.values() for i in engine if "link" in i]

        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(scan, u) for u in urls]
            for f in as_completed(futures):
                collected.update(f.result())

        return list(collected)
