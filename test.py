from Vigilante import Vigilante, Nightcrawler

print(Nightcrawler(Vigilante().tor_session).crawl("tordex", search_type="all"))
