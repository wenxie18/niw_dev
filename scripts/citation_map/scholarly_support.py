# Copyright (c) 2024 Chen Liu
# All rights reserved.
import random
import requests
import time
from bs4 import BeautifulSoup
from typing import List

NO_AUTHOR_FOUND_STR = 'No_author_found'

# Create a session for persistent cookies
session = requests.Session()

# List of free proxies (you can add more)
PROXY_LIST = [
    None,  # Direct connection only for now
    # Add working proxies here if available
]

def rotate_proxy():
    """Rotate to a different proxy"""
    proxy = random.choice(PROXY_LIST)
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}
        print(f"Using proxy: {proxy}")
    else:
        session.proxies = {}
        print("Using direct connection")

def get_html_per_citation_page(soup) -> List[str]:
    '''
    Utility to query each page containing results for
    cited work.
    Parameters
    --------
    soup: Beautiful Soup object pointing to current page.
    '''
    citing_author_ids = []
    citing_papers = []

    for result in soup.find_all('div', class_='gs_ri'):
        title_tag = result.find('h3', class_='gs_rt')
        if title_tag:
            paper_parsed = False
            author_links = result.find_all('a', href=True)
            title_text = title_tag.get_text()
            title = title_text.replace('[HTML]', '').replace('[PDF]', '')
            
            # Get author name from the byline
            byline = result.find('div', class_='gs_a')
            author_name = byline.text.split('-')[0].strip() if byline else 'Unknown Author'
            
            for link in author_links:
                if 'user=' in link['href']:
                    author_id = link['href'].split('user=')[1].split('&')[0]
                    citing_author_ids.append(author_id)
                    citing_papers.append({'author': author_name, 'title': title})
                    paper_parsed = True
            if not paper_parsed:
                print("[WARNING!] Could not find author links for ", title)
                citing_author_ids.append(NO_AUTHOR_FOUND_STR)
                citing_papers.append({'author': author_name, 'title': title})
        else:
            continue
    return citing_author_ids, citing_papers


def get_citing_author_ids_and_citing_papers(cites_id: str) -> List[str]:
    '''
    Find the (Google Scholar IDs of authors, titles of papers) who cite a given paper on Google Scholar.

    Parameters
    --------
    cites_id: The citation ID from Google Scholar.
    '''
    citing_author_ids = []
    citing_papers = []

    # Rotate proxy for this request
    rotate_proxy()

    headers = requests.utils.default_headers()
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })

    # Simulate human behavior: longer initial delay
    time.sleep(random.uniform(3, 8))

    # Construct the URL for the citation page
    paper_url = f'https://scholar.google.com/scholar?cites={cites_id}&hl=en'

    # Try direct scraping first, then immediately fallback to SerpAPI if blocked
    try:
        # Search the url of all citing papers.
        response = session.get(paper_url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise Exception('Failed to fetch the Google Scholar page')

        # Get the HTML data.
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for common indicators of blocking
        if 'CAPTCHA' in soup.text or 'not a robot' in soup.text:
            print(f'[WARNING!] Blocked by CAPTCHA or robot check when searching {paper_url}.')
            print(f'[INFO] Switching to SerpAPI fallback immediately...')
            try:
                from scripts.serpapi_helper import get_citing_authors_serpapi_fallback
                fallback_results = get_citing_authors_serpapi_fallback(cites_id)
                if fallback_results:
                    print(f'[SUCCESS] SerpAPI fallback found {len(fallback_results)} citing authors')
                    for author_id, paper_info in fallback_results:
                        citing_author_ids.append(author_id)
                        citing_papers.append(paper_info)
                    return citing_author_ids, citing_papers
                else:
                    print(f'[WARNING] SerpAPI fallback also failed, returning empty results')
                    return [], []
            except ImportError:
                print(f'[WARNING] SerpAPI helper not available, returning empty results')
                return [], []

        if 'Access Denied' in soup.text or 'Forbidden' in soup.text:
            print(f'[WARNING!] Access denied or forbidden when searching {paper_url}.')
            print(f'[INFO] Switching to SerpAPI fallback immediately...')
            try:
                from scripts.serpapi_helper import get_citing_authors_serpapi_fallback
                fallback_results = get_citing_authors_serpapi_fallback(cites_id)
                if fallback_results:
                    print(f'[SUCCESS] SerpAPI fallback found {len(fallback_results)} citing authors')
                    for author_id, paper_info in fallback_results:
                        citing_author_ids.append(author_id)
                        citing_papers.append(paper_info)
                    return citing_author_ids, citing_papers
                else:
                    print(f'[WARNING] SerpAPI fallback also failed, returning empty results')
                    return [], []
            except ImportError:
                print(f'[WARNING] SerpAPI helper not available, returning empty results')
                return [], []

        # If we get here, the request was successful - continue with normal processing
        print(f'[SUCCESS] Direct scraping successful for {paper_url}')

    except Exception as e:
        print(f'[ERROR!] Direct scraping failed: {str(e)}')
        print(f'[INFO] Switching to SerpAPI fallback...')
        try:
            from scripts.serpapi_helper import get_citing_authors_serpapi_fallback
            fallback_results = get_citing_authors_serpapi_fallback(cites_id)
            if fallback_results:
                print(f'[SUCCESS] SerpAPI fallback found {len(fallback_results)} citing authors')
                for author_id, paper_info in fallback_results:
                    citing_author_ids.append(author_id)
                    citing_papers.append(paper_info)
                return citing_author_ids, citing_papers
            else:
                print(f'[WARNING] SerpAPI fallback also failed, returning empty results')
                return [], []
        except ImportError:
            print(f'[WARNING] SerpAPI helper not available, returning empty results')
            return [], []

    # If direct scraping was successful, process the results normally
    # Loop through the citation results and find citing authors and papers.
    current_page_number = 1
    author_ids, papers = get_html_per_citation_page(soup)
    citing_author_ids.extend(author_ids)
    citing_papers.extend(papers)

    # Find the page navigation.
    navigation_buttons = soup.find_all('a', class_='gs_nma')
    for navigation in navigation_buttons:
        page_number_str = navigation.text
        if page_number_str and page_number_str.isnumeric() and int(page_number_str) == current_page_number + 1:
            # Found the correct button for next page.
            current_page_number += 1
            next_url = 'https://scholar.google.com' + navigation['href']
            
            # Simulate human reading time
            time.sleep(random.uniform(5, 10))  # Longer delay between pages

            response = session.get(next_url, headers=headers, timeout=30)
            if response.status_code != 200:
                break
            soup = BeautifulSoup(response.text, 'html.parser')
            author_ids, papers = get_html_per_citation_page(soup)
            citing_author_ids.extend(author_ids)
            citing_papers.extend(papers)
        else:
            continue

    return citing_author_ids, citing_papers

def get_organization_name(organization_id: str) -> str:
    '''
    Get the official name of the organization defined by the unique Google Scholar organization ID.
    '''

    headers = requests.utils.default_headers()
    headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
    })

    url = f'https://scholar.google.com/citations?view_op=view_org&org={organization_id}&hl=en'

    time.sleep(random.uniform(1, 5))  # Random delay to reduce risk of being blocked.

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f'When getting organization name, failed to fetch {url}: {response.text}.')

    soup = BeautifulSoup(response.text, 'html.parser')
    tag = soup.find('h2', {'class': 'gsc_authors_header'})
    if not tag:
        raise Exception(f'When getting organization name, failed to parse {url}.')
    return tag.text.replace('Learn more', '').strip()