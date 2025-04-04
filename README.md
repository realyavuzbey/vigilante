### **Vigilante OSINT Suite**

**Vigilante** is a high-security, Tor-powered OSINT suite designed to **crawl**, **analyze**, and **monitor** dark web intelligence.  
From passive recon to active content extraction, Vigilante is your entry point into the underground.
<br>

> ### **Nightcrawler**
- Supports multiple search engines including Ahmia and Tordex for deep web queries.
- Returns structured results with title, description, URL, and domain extracted from dark web listings.
- Automatically performs searches over the Tor network without manual interaction.
- Uses robust, custom HTML parsers to handle changes in search engine DOM structures.
- Allows exporting results to timestamped JSON files for later analysis or integration.

> ### **Scraptor**
- Downloads any webpage with all static assets (HTML, CSS, JS, fonts, images).
- `Scraptor.this(url)` downloads a single page.
- `Scraptor.all(url)` recursively crawls the site and downloads all internal pages.
- Saves content under `downloads/websites/{domain}` while preserving folder structure.

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
