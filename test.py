from vigilante import Nightcrawler

crawler = Nightcrawler(export_json=True)

search_term = "your_keywords_goes_here"

results = crawler.crawl(search_term)

for engine, engine_results in results.items():
    print(f"\n[{engine}] {len(engine_results)} result(s) found:\n")
    for entry in engine_results:
        print(f"- Title: {entry['title']}")
        print(f"  URL: {entry['url']}")
        print(f"  Description: {entry['description']}")
        print(f"  Domain: {entry['domain']}")
        print("")