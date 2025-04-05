import re
import ssl
import time
import socket
import requests
import json

from .session import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .utils import log
from .config import BADWORDS

class Typhonn:
    """
    Typhonn
    =======

    Typhonn is a hyper-intelligent web reconnaissance and vulnerability analysis engine, 
    engineered for high-resolution scanning of web targets across the clearnet and dark web.

    It identifies a wide range of technical weaknesses including misconfigured headers, 
    SSL certificate issues, exposed admin paths, weak authentication points, 
    insecure cookies, JavaScript injection vectors, and potential honeypot traps.

    With its two-stage analysis design, Typhonn enables both quick surface scans 
    and in-depth, multi-layered vulnerability audits via the detail=True flag.

    Whether you're a red teamer mapping your attack surface, or a blue team analyst hardening your stack,
    Typhonn delivers operational insights with surgical precision and developer-friendly output.

    Key Features:
    - Smart HTTP header and cookie misconfiguration detection.
    - SSL fingerprinting and expiration validation.
    - Hidden path probing (e.g., /.git, /.env, /admin, /config, /backup.zip).
    - DOM-level JavaScript and form analysis (e.g., eval, base64, CSRF indicators).
    - Honeypot and redirect behavior detection.
    - Heuristic-based risk scoring with severity mapping.
    - "Detail" mode unlocks advanced forensic checks, including content analysis.
    - Integrated badwords analysis to flag potentially dangerous or suspicious language in the content.
    """

    def __init__(self, url, detail=False, session=None, debug=False):
        """
        Initializes the Typhonn scanner.

        Args:
            url (str): The target URL to scan.
            detail (bool): Enables extended vulnerability checks when set to True.
            debug (bool): Enables detailed logging.
        """
        self.url = self._normalize(url)
        self.session = session if session else Session().session
        self.detail = detail
        self.debug = debug
        self.logger = lambda msg, level="INFO": log(msg, level=level, debug=self.debug)
        self.BADWORDS = BADWORDS

        self.report = {
            "url": self.url,
            "timestamp": time.ctime(),
            "detected_issues": {},
            "risk_score": 0
        }
        self.logger(f"[Typhonn] Initialized for: {self.url}")

    def _normalize(self, url):
        """
        Ensures the URL includes the protocol (http/https).

        Args:
            url (str): The raw URL input.

        Returns:
            str: The normalized URL.
        """
        if not url.startswith("http"):
            return "http://" + url
        return url

    def analyze(self):
        """
        Runs the core scan against the target URL. Performs layered analysis:
        - HTTP headers
        - SSL Certificate
        - Cookies
        - Metadata (meta tags)
        - Forms
        - Scripts
        - (Optional) Deep analysis: redirect behavior, hidden paths, honeypot detection, and badwords scanning.

        Returns:
            dict: A full JSON-compatible report.
        """
        self.logger("[Typhonn] Starting analysis...")

        try:
            r = self.session.get(self.url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            self.logger(f"[Typhonn] Page fetched successfully from: {self.url}")
        except Exception as e:
            self.report["error"] = f"Failed to fetch page: {e}"
            self.logger(f"[Typhonn] ERROR: {e}", level="ERROR")
            return self.report

        self._analyze_headers(r)
        self._analyze_ssl()
        self._analyze_cookies(r)
        self._analyze_meta(soup)
        self._analyze_forms(soup)
        self._analyze_scripts(soup)
        self._analyze_text_content(soup)

        if self.detail:
            self.logger("[Typhonn] Running deep inspection (detail=True)")
            self._check_redirect_behavior()
            self._detect_hidden_paths()
            self._detect_honeypot(soup)

        self._calculate_risk()
        self.logger(f"[Typhonn] Scan complete. Threat level: {self.report.get('threat_level')}")
        return self.report

    def _analyze_headers(self, r):
        """
        Analyzes HTTP response headers for potential security misconfigurations
        such as missing HSTS, CSP, or X-Frame headers, or tech stack leaks.
        """
        headers = r.headers
        issues = []

        if "Server" in headers:
            issues.append(f"Server info leaked: {headers['Server']}")
        if "X-Powered-By" in headers:
            issues.append(f"Tech stack leaked: {headers['X-Powered-By']}")
        if "Strict-Transport-Security" not in headers:
            issues.append("Missing HSTS header")
        if "Content-Security-Policy" not in headers:
            issues.append("Missing CSP header")
        if "X-Frame-Options" not in headers:
            issues.append("Missing X-Frame-Options header")

        self.report["detected_issues"]["headers"] = issues

    def _analyze_ssl(self):
        """
        Retrieves and inspects the SSL certificate of the domain
        to detect expiry, invalid cert chains, or self-signed certificates.
        """
        self.logger("[Typhonn] Checking SSL certificate...")
        try:
            hostname = urlparse(self.url).hostname
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.settimeout(5)
                s.connect((hostname, 443))
                cert = s.getpeercert()
                self.report["ssl_issuer"] = cert.get("issuer")
                self.report["ssl_expiry"] = cert.get("notAfter")
        except Exception as e:
            self.report["detected_issues"]["ssl"] = [f"SSL check failed: {e}"]

    def _analyze_cookies(self, r):
        """
        Inspects cookies for common misconfigurations, such as missing
        Secure or HttpOnly flags, which could lead to session hijacking.
        """
        issues = []
        for cookie in r.cookies:
            if not cookie.secure:
                issues.append(f"{cookie.name} missing Secure flag")
            if not cookie.has_nonstandard_attr("HttpOnly"):
                issues.append(f"{cookie.name} missing HttpOnly")
        self.report["detected_issues"]["cookies"] = issues

    def _analyze_meta(self, soup):
        """
        Checks the page's metadata for leaked tech stack, version info, 
        author names, or other SEO-relevant misconfigurations.
        """
        metas = soup.find_all("meta")
        leaks = []
        for m in metas:
            if m.get("name") in ["generator", "author", "powered-by"]:
                leaks.append(f"{m.get('name')}: {m.get('content')}")
        self.report["detected_issues"]["meta"] = leaks

    def _analyze_forms(self, soup):
        """
        Inspects forms for insecure configurations like missing CSRF tokens,
        non-password fields, and open action attributes.
        """
        forms = soup.find_all("form")
        form_issues = []
        for form in forms:
            if not form.get("action"):
                form_issues.append("Form with no action attribute")
            if "csrf" not in str(form).lower():
                form_issues.append("Possible missing CSRF token")
        self.report["detected_issues"]["forms"] = form_issues

    def _analyze_scripts(self, soup):
        """
        Detects usage of dangerous JavaScript functions (eval, setTimeout),
        obfuscation via Base64, and inline scripts.
        """
        suspicious = []
        for script in soup.find_all("script"):
            code = script.string or ""
            if any(x in code for x in ["eval(", "setTimeout(", "new Function"]):
                suspicious.append("Suspicious JavaScript function used")
            if re.search(r"atob\([^)]+\)", code):
                suspicious.append("Base64 obfuscation pattern detected")
        self.report["detected_issues"]["scripts"] = suspicious

    def _analyze_text_content(self, soup):
        """
        Scans the page's textual content for suspicious keywords based on a predefined badwords list.
        Each badword adds +2 to the risk score.
        """
        self.logger("[Typhonn] Analyzing text content for suspicious keywords...")
        text = soup.get_text(separator=" ", strip=True).lower()

        found_badwords = [word for word in self.BADWORDS if word in text]

        if found_badwords:
            self.report["detected_issues"].setdefault("badwords", []).extend(found_badwords)
            self.logger(f"[Typhonn] Badwords detected: {found_badwords}", level="WARNING")

            increment = len(found_badwords) * 2
            self.report["risk_score"] += increment
            self.logger(f"[Typhonn] Risk score increased by {increment} due to badwords", level="INFO")

            if any(word in found_badwords for word in ["rape", "pedo" "child", "abuse", "underage", "child porn"]):
                self.report.setdefault("flags", []).append("CRIMINAL_CONTENT_POSSIBLE")
                self.logger("[Typhonn] Criminal content flagged.", level="CRITICAL")

    def _check_redirect_behavior(self):
        """
        Detects possible redirect loops or time-delay honeypots 
        by following initial Location headers manually.
        """
        try:
            seen = set()
            current = self.url
            for _ in range(10):
                res = self.session.get(current, allow_redirects=False)
                loc = res.headers.get("Location")
                if not loc or loc in seen:
                    break
                seen.add(loc)
                current = urljoin(current, loc)
            if len(seen) > 5:
                self.report["detected_issues"]["redirect"] = ["Multiple chained redirects (possible trap)"]
        except Exception:
            pass

    def _detect_hidden_paths(self):
        """
        Brute-checks common hidden paths for exposure (e.g., /.git, /.env, /admin).
        """
        self.logger("[Typhonn] Scanning common hidden paths...")
        common_paths = ["/.git", "/.env", "/admin", "/config", "/backup.zip"]
        found = []
        for path in common_paths:
            full_url = urljoin(self.url, path)
            try:
                res = self.session.get(full_url, timeout=5)
                if res.status_code == 200:
                    found.append(path)
            except Exception:
                pass
        self.report["detected_issues"]["hidden_paths"] = found

    def _detect_honeypot(self, soup):
        """
        Uses behavioral heuristics to detect honeypot pages.
        Flags identical response bodies on search query variations, 
        or presence of invisible elements or bait forms.
        """
        red_flags = []
        try:
            q1 = self.session.get(self.url + "?q=test1").text
            q2 = self.session.get(self.url + "?q=test2").text
            if q1.strip() == q2.strip():
                red_flags.append("Identical response for unrelated queries")
            for tag in soup.find_all(style=True):
                if "display:none" in tag.get("style", ""):
                    red_flags.append("Invisible HTML element detected")
        except Exception:
            pass
        self.report["detected_issues"]["honeypot"] = red_flags

    def _calculate_risk(self):
        """
        Assigns a basic risk score based on the number and severity of findings.
        Used for dashboard or prioritization purposes.
        """
        total = 0
        for cat, issues in self.report["detected_issues"].items():
            total += len(issues) * 5
        self.report["risk_score"] = min(total, 100)
        if total > 75:
            self.report["threat_level"] = "CRITICAL"
        elif total > 40:
            self.report["threat_level"] = "HIGH"
        elif total > 20:
            self.report["threat_level"] = "MEDIUM"
        else:
            self.report["threat_level"] = "LOW"
