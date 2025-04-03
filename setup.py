from setuptools import setup, find_packages

setup(
    name="vigilante",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests[socks]",
        "beautifulsoup4",
        "stem",
        "lxml"
    ],
    author="Yavuz Bey",
    description="Dark web crawler & intelligence toolkit",
    python_requires=">=3.8"
)