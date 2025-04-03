### Vigilante OSINT Suite

**Vigilante** is a high-security, Tor-powered OSINT suite designed to **crawl**, **analyze**, and **monitor** dark web intelligence.  
From passive recon to active content extraction, Vigilante is your entry point into the underground.

> [!NOTE]
> Ensure Tor is running locally. Default SOCKS proxy is usually at `127.0.0.1:9150` or `9050`.
> You can install Tor via [Tor Browser](https://www.torproject.org/download/) or run `tor` as a background service.

### Some tools this we have:

### Nightcrawler
- Supports multiple search engines including Ahmia and Tordex for deep web queries.
- Returns structured results with title, description, URL, and domain extracted from dark web listings.
- Automatically performs searches over the Tor network without manual interaction.
- Uses robust, custom HTML parsers to handle changes in search engine DOM structures.
- Allows exporting results to timestamped JSON files for later analysis or integration.

### Usage & Installation

```bash
pip install vigilante
```
```python
from vigilante import Vigilante

v = Vigilante()
print(v.whois())
```
