from setuptools import setup, find_packages

setup(
    name='vigilante',
    version='0.1.0',
    description='Dark Web Recon & Intelligence CLI by @realyavuzbey',
    author='Yavuz Bey',
    url='https://github.com/realyavuzbey/vigilante',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'requests[socks]',
        "aiohttp",
        "aiofiles",
        "faker",
        "scapy",
        "browser-cookie3",
        "playwright",
        "httpx[socks]",
        'beautifulsoup4',
        'undetected-chromedriver',
        'selenium-stealth',
        'networkx',
        'stem',
        'pysocks',
        'fake-useragent',
        'matplotlib',
        'pandas',
        'tqdm',
        'dnspython',
        'python-whois'
    ],
    entry_points={
        'console_scripts': [
            'vigilante=vigilante.cli:main'
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License'
    ]
)
