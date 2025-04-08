from setuptools import setup, find_packages

setup(
    name='vigilante',
    version="0.1.1",
    description='Dark Web Recon & Intelligence CLI by @realyavuzbey',
    author='Yavuz Bey',
    url='https://github.com/realyavuzbey/vigilante',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'aiohttp',
        'aiofiles',
        'faker',
        'scapy',
        'browser-cookie3',
        'playwright',
        'httpx[socks]',
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
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Security',
        'Intended Audience :: Developers',
        'Environment :: Console'
    ],
    python_requires='>=3.8',
    keywords='osint tor darkweb crawler recon cli vigilante',
    platforms=['any']
)