from setuptools import setup, find_packages

setup(
    name="vigilante",
    version="0.1.3",
    packages=find_packages(),
    install_requires=[
        "requests[socks]",
        "beautifulsoup4",
        "stem",
        "lxml",
        "opencv-python",
        "numpy",
        "rstr",
        "torpy",
        "faker",
        "click",
        "pillow",
        "yt-dlp",
        "colorama",
        "aiohttp",
        "aiofiles",
        "python-dotenv",
        "pycountry",
        "dnspython",
        "tldextract",
        "python-whois",
        "fake-useragent",
        "tqdm",
        "python-dateutil",
        "urllib3"
    ],
    url="https://github.com/realyavuzbey/vigilante",
    author="Yavuz Bey",
    description="Dark Web Killer",
    python_requires=">=3.8"
)
