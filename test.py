from vigilante import Vigilante

v = Vigilante(security="0", export_json=True)
result = v.nightcrawler.crawl("tordex", search_type="all")

print(result)
