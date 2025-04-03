from setuptools import setup, find_packages

setup(
    name="vigilante",
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        "requests[socks]",
        "beautifulsoup4",
        "stem",
        "lxml",
        "opencv-python",
        "rstr",
        "numpy",
        "torpy",
        "faker",
        "click",
        "pillow",
        "yt-dlp",
        "colorama",
        "aiohttp",
        "pycountry",
        "dnspython",
        "tldextract",
        "python-whois",
        "fake-useragent"
    ],
    url="https://github.com/realyavuzbey/vigilante",
    author="Yavuz Bey",
    description="Dark Web Killer",
    python_requires=">=3.8"
)
