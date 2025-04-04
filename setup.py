from setuptools import setup, find_packages

setup(
    name="vigilante",
    version="0.2.5",
    packages=find_packages(),
    install_requires=[
        "requests[socks]",
        "beautifulsoup4",
        "stem",
        "lxml",
        "numpy",
        "plyer",
        "rstr",
        "torpy",
        "faker",
        "click",
        "pymediainfo",
        "exifread",
        "pillow",
        "python-docx",
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
        "urllib3",
        "2captcha-python"
    ],
    url="https://github.com/realyavuzbey/vigilante",
    author="Yavuz Bey",
    description="Dark Web Killer",
    python_requires=">=3.8"
)
