### **Vigilante OSINT Suite**

**Vigilante** is a high-security, Tor-powered OSINT suite designed to **crawl**, **analyze**, and **monitor** dark web intelligence.  
From passive recon to active content extraction, Vigilante is your entry point into the underground.
<br>

> ### **Nightcrawler**
- A **Tor-native dark web intelligence harvester** designed for keyword-based OSINT queries across hidden service search engines.
- Supports engines like **Ahmia**, **Tordex**, and **Tor66**, automatically routing all traffic over Tor for full anonymity.
- Extracts and normalizes structured data from search results: `title`, `url`, `description`, and `domain`.
- Modular HTML parsers handle DOM inconsistencies across search engines—resilient to layout changes or obfuscation.
- Provides **custom session injection** for fine-grained Tor control or external proxy chaining.
- Results can be exported to `JSON`, `CSV`, `Markdown`, or `TXT`—perfect for intel pipelines or dashboards.
- **Zero-click architecture**: once initialized, executes entire search lifecycle autonomously.
- Ideal for:
  - Threat intel teams monitoring deep web chatter.
  - Journalists tracking underground marketplaces.
  - Analysts pivoting from keywords to onion intelligence.
- Built for speed, stealth, and structure.

> ### **Scraptor**
- High-fidelity, OSINT-focused **web mirroring & forensic extraction engine** for clearnet and dark web.
- Reconstructs full web pages including **HTML, CSS, JS, fonts, videos, images, and forms**.
- `Scraptor.this(url)` → Downloads a single web page with all related static assets.
- `Scraptor.all(url)` → Recursively crawls the domain and mirrors its entire internal structure.
- Preserves original **directory hierarchy** under `downloads/websites/{domain}` for offline browsing.
- Supports advanced modes:
  - `mode="text"` to strip away all non-content elements for clean NLP-ready content.
  - `mode="video"` or `mode="image"` to extract and download only visual assets.
- Comes with a built-in `extract_page()` profiler:
  - Extracts meta tags, form actions, headers, cookies, scripts, favicons, and structural info.
  - Generates **structured JSON reports** for digital forensics, compliance, or analysis pipelines.
- Ideal for:
  - Dark web intelligence collection
  - Static site fingerprinting
  - Content mirroring for censorship circumvention
  - Red teaming reconnaissance
- Fully compatible with Tor or custom session for anonymous web scraping at scale.

> ### **Typhonn**
- Performs deep and surface-level vulnerability assessments on any given web target.
- Automatically checks for common security misconfigurations: missing HSTS, CSP, and X-Frame headers.
- Scans for insecure cookies, visible server info, outdated tech stacks, and metadata leaks.
- Detects exposed directories like `/.git`, `/admin`, `/config`, `.env`, and backup files.
- In `detail=True` mode, it also performs:
  - SSL certificate fingerprinting and expiration checks
  - Hidden honeypot detection using behavior-based heuristics
  - Chained redirect loop analysis
- Generates a full threat report with risk scoring and severity level (LOW, MEDIUM, HIGH, CRITICAL).
- Designed for red/blue teams to integrate easily into OSINT and recon pipelines.

> [!NOTE]
> Ensure Tor is running locally. Default SOCKS proxy is usually at `127.0.0.1:9150` or `9050`.
> You can install Tor via [Tor Browser](https://www.torproject.org/download/) or run `tor` as a background service.

### **Usage & Installation**

```bash
pip install vigilante
```
```python
from vigilante import Vigilante

v = Vigilante()
print(v.whois())
```

### **Legal Disclaimer**

This project is intended for **educational and research purposes only**.  
The author(s) of Vigilante do **not condone**, support, or take any responsibility for any misuse, illegal activity, or unethical behavior involving this software.

By using this tool, you agree to take full responsibility for your actions.  
Ensure all activities comply with local laws and regulations in your jurisdiction.

**Use at your own risk. The Vigilante project and its contributors accept no liability.**
