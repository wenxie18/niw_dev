from setuptools import setup, find_packages

setup(
    name="citation_map_local",
    version="4.6",
    packages=find_packages(),
    install_requires=[
        'backoff',
        'bs4',
        'folium',
        'geopy',
        'pandas',
        'pycountry',
        'requests',
        'scholarly',
        'tqdm'
    ],
) 