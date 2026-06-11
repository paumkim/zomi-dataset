"""
Run full Zomi crawl across all websites.
"""
import time, sys
sys.path.insert(0, '.')
from crawl.crawler import crawl_site

sites = ['zomidaily', 'zomiworship', 'zomilyrics', 'zomilaisiangtho', 'zomielibrary', 'zomidictionary']

for site in sites:
    sep = "=" * 60
    print(f'\n{sep}')
    print(f'Crawling: {site}')
    print(f'{sep}')
    try:
        crawl_site(site)
    except Exception as e:
        print(f'Error crawling {site}: {e}')
    time.sleep(2)

print('\nAll HTML sites crawled')
