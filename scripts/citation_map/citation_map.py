# Copyright (c) 2024 Chen Liu
# All rights reserved.
import folium
import itertools
import pandas as pd
import os
import pickle
import pycountry
import re
import random
import time
import requests
import json

from geopy.geocoders import Nominatim
from multiprocessing import Pool
from scholarly import scholarly, ProxyGenerator
from tqdm import tqdm
from typing import Any, List, Tuple

from scripts.citation_map.scholarly_support import get_citing_author_ids_and_citing_papers, get_organization_name, NO_AUTHOR_FOUND_STR
from config import GOOGLE_MAPS_API_KEY


def find_all_citing_authors(scholar_id: str, num_processes: int = 16) -> List[Tuple[str]]:
    '''
    Step 1. Find all publications of the given Google Scholar ID.
    Step 2. Find all citing authors.
    '''
    # Find Google Scholar Profile using Scholar ID.
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    print('Author profile found, with %d publications.\n' % len(publications))

    # Fetch metadata for all publications.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            all_publications = list(tqdm(pool.imap(__fill_publication_metadata, publications),
                                         desc='Filling metadata for your %d publications' % len(publications),
                                         total=len(publications)))
    else:
        all_publications = []
        for pub in tqdm(publications,
                        desc='Filling metadata for your %d publications' % len(publications),
                        total=len(publications)):
            all_publications.append(__fill_publication_metadata(pub))

    # Convert all publications to Google Scholar publication IDs and paper titles.
    # This is fast and no parallel processing is needed.
    all_publication_info = []
    for pub in all_publications:
        if 'cites_id' in pub:
            for cites_id in pub['cites_id']:
                pub_title = pub['bib']['title']
                citation = pub['bib'].get('citation', '')  # Get citation info
                all_publication_info.append((cites_id, pub_title, citation))

    # Find all citing authors from all publications.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            all_citing_author_paper_info_nested = list(tqdm(pool.imap(__citing_authors_and_papers_from_publication, all_publication_info),
                                                            desc='Finding citing authors and papers on your %d publications' % len(all_publication_info),
                                                            total=len(all_publication_info)))
    else:
        all_citing_author_paper_info_nested = []
        for pub in tqdm(all_publication_info,
                        desc='Finding citing authors and papers on your %d publications' % len(all_publication_info),
                        total=len(all_publication_info)):
            all_citing_author_paper_info_nested.append(__citing_authors_and_papers_from_publication(pub))
    all_citing_author_paper_tuple_list = list(itertools.chain(*all_citing_author_paper_info_nested))
    return all_citing_author_paper_tuple_list

def find_all_citing_affiliations(all_citing_author_paper_tuple_list: List[Tuple[str]],
                                 num_processes: int = 16,
                                 affiliation_conservative: bool = False):
    '''
    Step 3. Find all citing affiliations.
    '''
    if affiliation_conservative:
        __affiliations_from_authors = __affiliations_from_authors_conservative
    else:
        __affiliations_from_authors = __affiliations_from_authors_aggressive

    # Find all citing insitutions from all citing authors.
    if num_processes > 1 and isinstance(num_processes, int):
        with Pool(processes=num_processes) as pool:
            author_paper_affiliation_tuple_list = list(tqdm(pool.imap(__affiliations_from_authors, all_citing_author_paper_tuple_list),
                                                            desc='Finding citing affiliations from %d citing authors' % len(all_citing_author_paper_tuple_list),
                                                            total=len(all_citing_author_paper_tuple_list)))
    else:
        author_paper_affiliation_tuple_list = []
        for author_and_paper in tqdm(all_citing_author_paper_tuple_list,
                                     desc='Finding citing affiliations from %d citing authors' % len(all_citing_author_paper_tuple_list),
                                     total=len(all_citing_author_paper_tuple_list)):
            author_paper_affiliation_tuple_list.append(__affiliations_from_authors(author_and_paper))

    # Filter empty items.
    author_paper_affiliation_tuple_list = [item for item in author_paper_affiliation_tuple_list if item]
    return author_paper_affiliation_tuple_list

def clean_affiliation_names(author_paper_affiliation_tuple_list: List[Tuple[str]]) -> List[Tuple[str]]:
    '''
    Optional Step. Clean up the names of affiliations from the authors' affiliation tab on their Google Scholar profiles.
    NOTE: This logic is very naive. Please send an issue or pull request if you have any idea how to improve it.
    Currently we will not consider any paid service or tools that pose extra burden on the users, such as GPT API.
    '''
    cleaned_author_paper_affiliation_tuple_list = []
    for author_name, citing_paper_title, cited_paper_title, affiliation_string, author_id, *rest in author_paper_affiliation_tuple_list:
        citation = rest[0] if rest else ''
        if author_name == NO_AUTHOR_FOUND_STR:
            cleaned_author_paper_affiliation_tuple_list.append((NO_AUTHOR_FOUND_STR, citing_paper_title, cited_paper_title, NO_AUTHOR_FOUND_STR, NO_AUTHOR_FOUND_STR, citation))
        else:
            # Use a regular expression to split the string by ';' or 'and'.
            substring_list = [part.strip() for part in re.split(r'[;]|\band\b', affiliation_string)]
            # Further split the substrings by ',' if the latter component is not a country.
            substring_list = __country_aware_comma_split(substring_list)

            for substring in substring_list:
                # Use a regular expression to remove anything before 'at', or '@'.
                cleaned_affiliation = re.sub(r'.*?\bat\b|.*?@', '', substring, flags=re.IGNORECASE).strip()
                # Use a regular expression to filter out strings that represent
                # a person's identity rather than affiliation.
                is_common_identity_string = re.search(
                    re.compile(
                        r'\b(director|manager|chair|engineer|programmer|scientist|professor|lecturer|phd|ph\.d|postdoc|doctor|student|department of)\b',
                        re.IGNORECASE),
                    cleaned_affiliation)
                if not is_common_identity_string:
                    cleaned_author_paper_affiliation_tuple_list.append(
                        (author_name, citing_paper_title, cited_paper_title, cleaned_affiliation, author_id, citation)
                    )
    return cleaned_author_paper_affiliation_tuple_list

def affiliation_text_to_geocode(author_paper_affiliation_tuple_list: List[Tuple[str]], max_attempts: int = 3) -> List[Tuple[str]]:
    '''
    Step 4: Convert affiliations in plain text to Geocode.
    First tries Nominatim, falls back to Google Maps API if it times out.
    Uses caching to store and retrieve previously geocoded affiliations.
    '''
    coordinates_and_info = []
    import requests
    import time
    import json
    import os
    from config import GOOGLE_MAPS_API_KEY
    from geopy.geocoders import Nominatim

    # Initialize geocoders
    nominatim = Nominatim(user_agent='citation_mapper')
    
    # Load cache if it exists
    cache_file = 'geocode_cache.json'
    geocode_cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                geocode_cache = json.load(f)
        except Exception as e:
            print(f"Error loading cache file: {str(e)}")
    
    # Find unique affiliations and record their corresponding entries.
    affiliation_map = {}
    for entry_idx, (_, _, _, affiliation_name, _, *_) in enumerate(author_paper_affiliation_tuple_list):
        if affiliation_name not in affiliation_map.keys():
            affiliation_map[affiliation_name] = [entry_idx]
        else:
            affiliation_map[affiliation_name].append(entry_idx)

    num_total_affiliations = len(affiliation_map)
    num_located_affiliations = 0
    
    for affiliation_name in tqdm(affiliation_map,
                                 desc='Finding geographic coordinates from %d unique citing affiliations in %d entries' % (
                                     len(affiliation_map), len(author_paper_affiliation_tuple_list)),
                                 total=len(affiliation_map),
                                 position=0,
                                 leave=True):
        if affiliation_name == NO_AUTHOR_FOUND_STR:
            corresponding_entries = affiliation_map[affiliation_name]
            for entry_idx in corresponding_entries:
                author_name, citing_paper_title, cited_paper_title, affiliation_name, author_id, *rest = author_paper_affiliation_tuple_list[entry_idx]
                citation = rest[0] if rest else ''
                coordinates_and_info.append((author_name, citing_paper_title, cited_paper_title, affiliation_name,
                                           '', '', '', '', '', '', author_id, citation))
        else:
            # Check cache first - only based on affiliation name
            if affiliation_name in geocode_cache:
                cached_data = geocode_cache[affiliation_name]
                # Use cached data for all entries with this affiliation
                corresponding_entries = affiliation_map[affiliation_name]
                for entry_idx in corresponding_entries:
                    author_name, citing_paper_title, cited_paper_title, affiliation_name, author_id, *rest = author_paper_affiliation_tuple_list[entry_idx]
                    citation = rest[0] if rest else ''
                    coordinates_and_info.append((author_name, citing_paper_title, cited_paper_title, affiliation_name,
                                               cached_data['lat'], cached_data['lng'], cached_data['county'],
                                               cached_data['city'], cached_data['state'], cached_data['country'], author_id, citation))
                num_located_affiliations += 1
                continue

            # If not in cache, try to geocode
            for attempt in range(max_attempts):
                try:
                    # Add a longer delay between requests to respect rate limits
                    if attempt > 0:
                        time.sleep(2)  # 2 second delay between retries
                    else:
                        time.sleep(1)  # 1 second delay between different affiliations

                    # Try Nominatim first
                    if attempt == 0:
                        geo_location = nominatim.geocode(affiliation_name, timeout=30)  # Increased timeout to 30 seconds
                        if geo_location:
                            # Get the full location metadata
                            time.sleep(1)  # Additional delay before reverse geocoding
                            location_metadata = nominatim.reverse(str(geo_location.latitude) + ',' + str(geo_location.longitude), 
                                                                language='en', timeout=30)  # Increased timeout to 30 seconds
                            address = location_metadata.raw['address']
                            lat, lng = geo_location.latitude, geo_location.longitude
                            county = address.get('county')
                            city = address.get('city')
                            state = address.get('state')
                            country = address.get('country')
                    else:
                        # Fall back to Google Maps API
                        time.sleep(0.1)  # Respect rate limits
                        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={affiliation_name}&key={GOOGLE_MAPS_API_KEY}'
                        response = requests.get(url)
                        data = response.json()
                        
                        if data['status'] == 'OK':
                            result = data['results'][0]
                            location = result['geometry']['location']
                            lat, lng = location['lat'], location['lng']
                            
                            # Get address components
                            address_components = result.get('address_components', [])
                            county, city, state, country = None, None, None, None
                            
                            for component in address_components:
                                types = component['types']
                                if 'administrative_area_level_2' in types:
                                    county = component['long_name']
                                elif 'locality' in types:
                                    city = component['long_name']
                                elif 'administrative_area_level_1' in types:
                                    state = component['long_name']
                                elif 'country' in types:
                                    country = component['long_name']
                        else:
                            continue

                    # Cache the successful geocoding result - only store the location data
                    geocode_cache[affiliation_name] = {
                        'lat': lat,
                        'lng': lng,
                        'county': county,
                        'city': city,
                        'state': state,
                        'country': country
                    }

                    # Use the same geocoded data for all entries with this affiliation
                    corresponding_entries = affiliation_map[affiliation_name]
                    for entry_idx in corresponding_entries:
                        author_name, citing_paper_title, cited_paper_title, affiliation_name, author_id, *rest = author_paper_affiliation_tuple_list[entry_idx]
                        citation = rest[0] if rest else ''
                        coordinates_and_info.append((author_name, citing_paper_title, cited_paper_title, affiliation_name,
                                                   lat, lng, county, city, state, country, author_id, citation))
                    # This location is successfully recorded.
                    num_located_affiliations += 1
                    break
                    
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed for {affiliation_name}: {str(e)}")
                    if attempt == max_attempts - 1:
                        print(f"All attempts failed for {affiliation_name}, skipping...")
                    continue

    # Save the updated cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(geocode_cache, f)
    except Exception as e:
        print(f"Error saving cache file: {str(e)}")
                    
    print('\nConverted %d/%d affiliations to Geocodes.' % (num_located_affiliations, num_total_affiliations))
    coordinates_and_info = [item for item in coordinates_and_info if item is not None]  # Filter out empty entries.
    return coordinates_and_info

def export_dict_to_csv(coordinates_and_info: List[Tuple[str]], csv_output_path: str) -> None:
    '''
    Step 5.1: Export csv file recording citation information.
    '''
    citation_df = pd.DataFrame(coordinates_and_info,
                               columns=['citing author name', 'citing paper title', 'cited paper title',
                                        'affiliation', 'latitude', 'longitude',
                                        'county', 'city', 'state', 'country',
                                        'author_id', 'citation'])  # Added citation column

    # Add Google Scholar profile links
    citation_df['google_scholar_link'] = citation_df['author_id'].apply(
        lambda x: f'https://scholar.google.com/citations?user={x}&hl=en' if x != NO_AUTHOR_FOUND_STR and x != '' else ''
    )

    citation_df.to_csv(csv_output_path)
    return

def read_csv_to_dict(csv_path: str) -> None:
    '''
    Step 5.1: Read csv file recording citation information.
    Only relevant if `read_from_csv` is True.
    '''

    citation_df = pd.read_csv(csv_path, index_col=0)
    coordinates_and_info = list(citation_df.itertuples(index=False, name=None))
    return coordinates_and_info

def create_map(coordinates_and_info: List[Tuple[str]], pin_colorful: bool = True):
    '''
    Step 5.2: Create the Citation World Map.

    For authors under the same affiliations, they will be displayed in the same pin.
    '''
    citation_map = folium.Map(location=[20, 0], zoom_start=2)

    # Find unique affiliations and record their corresponding entries.
    affiliation_map = {}
    for entry_idx, (_, _, _, affiliation_name, _, *_) in enumerate(coordinates_and_info):
        if affiliation_name == NO_AUTHOR_FOUND_STR:
            continue
        elif affiliation_name not in affiliation_map.keys():
            affiliation_map[affiliation_name] = [entry_idx]
        else:
            affiliation_map[affiliation_name].append(entry_idx)

    if pin_colorful:
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                  'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
                  'darkpurple', 'pink', 'lightblue', 'lightgreen',
                  'gray', 'black', 'lightgray']
        for affiliation_name in affiliation_map:
            color = random.choice(colors)
            corresponding_entries = affiliation_map[affiliation_name]
            author_name_list = []
            for entry_idx in corresponding_entries:
                author_name, _, _, _, lat, lon, _, _, _, _, author_id, *rest = coordinates_and_info[entry_idx]
                if author_id != NO_AUTHOR_FOUND_STR:
                    author_link = f'<a href="https://scholar.google.com/citations?user={author_id}&hl=en" target="_blank">{author_name}</a>'
                    author_name_list.append(author_link)
                else:
                    author_name_list.append(author_name)
            folium.Marker([lat, lon], popup='%s (%s)' % (affiliation_name, ' & '.join(author_name_list)),
                          icon=folium.Icon(color=color)).add_to(citation_map)
    else:
        for affiliation_name in affiliation_map:
            corresponding_entries = affiliation_map[affiliation_name]
            author_name_list = []
            for entry_idx in corresponding_entries:
                author_name, _, _, _, lat, lon, _, _, _, _, author_id, *rest = coordinates_and_info[entry_idx]
                if author_id != NO_AUTHOR_FOUND_STR:
                    author_link = f'<a href="https://scholar.google.com/citations?user={author_id}&hl=en" target="_blank">{author_name}</a>'
                    author_name_list.append(author_link)
                else:
                    author_name_list.append(author_name)
            folium.Marker([lat, lon], popup='%s (%s)' % (affiliation_name, ' & '.join(author_name_list))).add_to(citation_map)
    return citation_map


def __fill_publication_metadata(pub):
    time.sleep(random.uniform(1, 5))  # Random delay to reduce risk of being blocked.
    return scholarly.fill(pub)

def __citing_authors_and_papers_from_publication(cites_id_and_cited_paper: Tuple[str, str]):
    '''
    Find all citing authors and papers from a publication.
    '''
    cites_id, cited_paper_title, citation = cites_id_and_cited_paper
    citing_author_ids, citing_papers = get_citing_author_ids_and_citing_papers(cites_id)
    citing_author_paper_info = []
    for author_id, paper in zip(citing_author_ids, citing_papers):
        citing_author_paper_info.append((NO_AUTHOR_FOUND_STR if author_id == NO_AUTHOR_FOUND_STR else paper['author'], 
                                       paper['title'], 
                                       cited_paper_title,
                                       NO_AUTHOR_FOUND_STR if author_id == NO_AUTHOR_FOUND_STR else author_id,
                                       citation))  # Add citation info
    return citing_author_paper_info

def __affiliations_from_authors_conservative(citing_author_paper_info: str):
    '''
    Conservative: only use Google Scholar verified organization.
    This will have higher precision and lower recall.
    '''
    author_name, citing_paper_title, cited_paper_title, citing_author_id, citation = citing_author_paper_info
    if citing_author_id == NO_AUTHOR_FOUND_STR:
        return (NO_AUTHOR_FOUND_STR, citing_paper_title, cited_paper_title, NO_AUTHOR_FOUND_STR, NO_AUTHOR_FOUND_STR, citation)

    time.sleep(random.uniform(1, 5))  # Random delay to reduce risk of being blocked.
    citing_author = scholarly.search_author_id(citing_author_id)

    if 'organization' in citing_author:
        try:
            author_organization = get_organization_name(citing_author['organization'])
            return (citing_author['name'], citing_paper_title, cited_paper_title, author_organization, citing_author_id, citation)
        except Exception as e:
            print('[Warning!]', e)
            return None
    return None

def __affiliations_from_authors_aggressive(citing_author_paper_info: str):
    '''
    Aggressive: use the self-reported affiliation string from the Google Scholar affiliation panel.
    This will have lower precision and higher recall.
    '''
    author_name, citing_paper_title, cited_paper_title, citing_author_id, citation = citing_author_paper_info
    if citing_author_id == NO_AUTHOR_FOUND_STR:
        return (NO_AUTHOR_FOUND_STR, citing_paper_title, cited_paper_title, NO_AUTHOR_FOUND_STR, NO_AUTHOR_FOUND_STR, citation)

    time.sleep(random.uniform(1, 5))  # Random delay to reduce risk of being blocked.
    citing_author = scholarly.search_author_id(citing_author_id)
    if 'affiliation' in citing_author:
        return (citing_author['name'], citing_paper_title, cited_paper_title, citing_author['affiliation'], citing_author_id, citation)
    return None

def __country_aware_comma_split(string_list: List[str]) -> List[str]:
    comma_split_list = []

    for part in string_list:
        # Split the strings by comma.
        # NOTE: The non-English comma is entered intentionally.
        sub_parts = [sub_part.strip() for sub_part in re.split(r'[,，]', part)]
        sub_parts_iter = iter(sub_parts)

        # Merge the split strings if the latter component is a country name.
        for sub_part in sub_parts_iter:
            if __iscountry(sub_part):
                continue  # Skip country names if they appear as the first sub_part.
            next_part = next(sub_parts_iter, None)
            if __iscountry(next_part):
                comma_split_list.append(f"{sub_part}, {next_part}")
            else:
                comma_split_list.append(sub_part)
                if next_part:
                    comma_split_list.append(next_part)
    return comma_split_list

def __iscountry(string: str) -> bool:
    try:
        pycountry.countries.lookup(string)
        return True
    except LookupError:
        return False

def __print_author_and_affiliation(author_paper_affiliation_tuple_list: List[Tuple[str]]) -> None:
    __author_affiliation_tuple_list = []
    for author_name, _, _, affiliation_name, author_id, *_ in sorted(author_paper_affiliation_tuple_list):
        if author_name == NO_AUTHOR_FOUND_STR:
            continue
        __author_affiliation_tuple_list.append((author_name, affiliation_name))

    # Take unique tuples.
    __author_affiliation_tuple_list = list(set(__author_affiliation_tuple_list))
    for author_name, affiliation_name in sorted(__author_affiliation_tuple_list):
        print('Author: %s. Affiliation: %s.' % (author_name, affiliation_name))
    print('')
    return


def save_cache(data: Any, fpath: str) -> None:
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "wb") as fd:
        pickle.dump(data, fd)

def load_cache(fpath: str) -> Any:
    with open(fpath, "rb") as fd:
        return pickle.load(fd)

def setup_proxy_system(max_retries=3):
    '''
    Set up proxy system with retries and validation for scholarly 1.7.11.
    '''
    from scholarly import ProxyGenerator, scholarly
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Attempt {attempt+1}: Initializing ProxyGenerator and FreeProxies (no 'proxies' kwarg)")
            pg = ProxyGenerator()
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                print(f'Proxy setup successful on attempt {attempt + 1}')
                return pg
            else:
                print(f'Proxy setup failed on attempt {attempt + 1}, retrying...')
                time.sleep(2)
        except TypeError as e:
            print(f"[ERROR] TypeError during proxy setup: {e}")
            print("This usually means an incompatible scholarly version or a bad call. Skipping proxy setup.")
            break
        except Exception as e:
            print(f'Error setting up proxy on attempt {attempt + 1}: {str(e)}')
            time.sleep(2)
    print('Failed to set up proxy after all attempts')
    return None

def generate_citation_map(scholar_id: str,
                          output_path: str = 'citation_map.html',
                          csv_output_path: str = 'citation_info.csv',
                          parse_csv: bool = False,
                          cache_folder: str = 'cache',
                          affiliation_conservative: bool = False,
                          num_processes: int = 16,
                          use_proxy: bool = False,
                          pin_colorful: bool = True,
                          print_citing_affiliations: bool = True):
    '''
    Google Scholar Citation World Map.

    Parameters
    ----
    scholar_id: str
        Your Google Scholar ID.
    output_path: str
        (default is 'citation_map.html')
        The path to the output HTML file.
    csv_output_path: str
        (default is 'citation_info.csv')
        The path to the output csv file.
    parse_csv: bool
        (default is False)
        If True, will directly jump to Step 5.2, using the information loaded from the csv.
    cache_folder: str
        (default is 'cache')
        The folder to save intermediate results, after finding (author, paper) but before finding the affiliations.
        This is because the user might want to try the aggressive vs. conservative approach.
        Set to None if you do not want caching.
    affiliation_conservative: bool
        (default is False)
        If true, we will use a more conservative approach to identify affiliations.
        If false, we will use a more aggressive approach to identify affiliations.
    num_processes: int
        (default is 16)
        Number of processes for parallel processing.
    use_proxy: bool
        (default is False)
        If true, we will use a scholarly proxy.
        It is necessary for some environments to avoid blocks, but it usually makes things slower.
    pin_colorful: bool
        (default is True)
        If true, the location pins will have a variety of colors.
        Otherwise, it will only have one color.
    print_citing_affiliations: bool
        (default is True)
        If true, print the list of citing affiliations (affiliations of citing authors).
    '''

    if not parse_csv:
        if use_proxy:
            proxy_generator = setup_proxy_system()
            if proxy_generator:
                print('Successfully configured proxy system')
            else:
                print('Warning: Proceeding without proxy as setup failed')
                use_proxy = False

        if cache_folder is not None:
            cache_path = os.path.join(cache_folder, scholar_id, 'all_citing_author_paper_tuple_list.pkl')
        else:
            cache_path = None

        if cache_path is None or not os.path.exists(cache_path):
            print('No cache found for this author. Finding citing authors from scratch.\n')

            # NOTE: Step 1. Find all publications of the given Google Scholar ID.
            #       Step 2. Find all citing authors.
            all_citing_author_paper_tuple_list = find_all_citing_authors(scholar_id=scholar_id,
                                                                        num_processes=num_processes)
            print('A total of %d citing authors recorded.\n' % len(all_citing_author_paper_tuple_list))
            if cache_path is not None and len(all_citing_author_paper_tuple_list) > 0:
                save_cache(all_citing_author_paper_tuple_list, cache_path)
            print('Saved to cache: %s.\n' % cache_path)

        else:
            print('Cache found. Loading author paper information from cache.\n')
            all_citing_author_paper_tuple_list = load_cache(cache_path)
            print('Loaded from cache: %s.\n' % cache_path)
            print('A total of %d citing authors loaded.\n' % len(all_citing_author_paper_tuple_list))

        if cache_folder is not None:
            cache_path = os.path.join(cache_folder, scholar_id, 'author_paper_affiliation_tuple_list.pkl')
        else:
            cache_path = None

        if cache_path is None or not os.path.exists(cache_path):
            print('No cache found for this author. Finding citing affiliations from scratch.\n')

            # NOTE: Step 2. Find all citing affiliations.
            print('Identifying affiliations using the %s approach.' % ('conservative' if affiliation_conservative else 'aggressive'))
            author_paper_affiliation_tuple_list = find_all_citing_affiliations(all_citing_author_paper_tuple_list,
                                                                             num_processes=num_processes,
                                                                             affiliation_conservative=affiliation_conservative)
            print('\nA total of %d citing affiliations recorded.\n' % len(author_paper_affiliation_tuple_list))
            # Take unique tuples.
            author_paper_affiliation_tuple_list = list(set(author_paper_affiliation_tuple_list))

            # NOTE: Step 3. Clean the affiliation strings (optional, only used if taking the aggressive approach).
            if print_citing_affiliations:
                if affiliation_conservative:
                    print('Taking the conservative approach. Will not need to clean the affiliation names.')
                    print('List of all citing authors and affiliations:\n')
                else:
                    print('Taking the aggressive approach. Cleaning the affiliation names.')
                    print('List of all citing authors and affiliations before cleaning:\n')
                __print_author_and_affiliation(author_paper_affiliation_tuple_list)
            if not affiliation_conservative:
                cleaned_author_paper_affiliation_tuple_list = clean_affiliation_names(author_paper_affiliation_tuple_list)
                if print_citing_affiliations:
                    print('List of all citing authors and affiliations after cleaning:\n')
                    __print_author_and_affiliation(cleaned_author_paper_affiliation_tuple_list)
                # Use the merged set to maximize coverage.
                author_paper_affiliation_tuple_list += cleaned_author_paper_affiliation_tuple_list
                # Take unique tuples.
                author_paper_affiliation_tuple_list = list(set(author_paper_affiliation_tuple_list))

            if cache_path is not None and len(author_paper_affiliation_tuple_list) > 0:
                save_cache(author_paper_affiliation_tuple_list, cache_path)
            print('Saved to cache: %s.\n' % cache_path)

        else:
            print('Cache found. Loading author paper and affiliation information from cache.\n')
            author_paper_affiliation_tuple_list = load_cache(cache_path)
            print('List of all citing authors and affiliations loaded:\n')
            __print_author_and_affiliation(author_paper_affiliation_tuple_list)

        # NOTE: Step 4. Convert affiliations in plain text to Geocode.
        coordinates_and_info = affiliation_text_to_geocode(author_paper_affiliation_tuple_list)
        # Take unique tuples.
        coordinates_and_info = list(set(coordinates_and_info))

        # NOTE: Step 5.1. Export csv file recording citation information.
        export_dict_to_csv(coordinates_and_info, csv_output_path)
        print('\nCitation information exported to %s.' % csv_output_path)

    else:
        print('\nDirectly parsing the csv. Skipping all previous steps.')
        assert os.path.isfile(csv_output_path), '`csv_output_path` is not a file.'
        coordinates_and_info = read_csv_to_dict(csv_output_path)
        print('\nCitation information loaded from %s.' % csv_output_path)

    # NOTE: Step 5.2. Create the citation world map.
    citation_map = create_map(coordinates_and_info, pin_colorful=pin_colorful)
    citation_map.save(output_path)
    print('\nHTML map created and saved at %s.\n' % output_path)
    return

def save_author_ids_for_debugging(scholar_id: str, output_path: str = 'author_ids_debug.csv'):
    '''
    Save author IDs and links for debugging purposes.
    This function only collects and saves the essential information about citing authors
    without running the full citation map generation process.
    '''
    print('Finding citing authors for Google Scholar ID:', scholar_id)
    
    # Step 1: Get all publications
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    print(f'Found {len(publications)} publications')

    # Step 2: Get citing authors for each publication
    all_citing_authors = []
    for pub in tqdm(publications, desc='Processing publications'):
        if 'cites_id' in pub:
            for cites_id in pub['cites_id']:
                citing_author_ids, citing_papers = get_citing_author_ids_and_citing_papers(cites_id)
                for author_id, paper in zip(citing_author_ids, citing_papers):
                    if author_id != NO_AUTHOR_FOUND_STR:
                        all_citing_authors.append({
                            'author_name': paper['author'],
                            'author_id': author_id,
                            'paper_title': paper['title'],
                            'cited_paper': pub['bib']['title'],
                            'google_scholar_link': f'https://scholar.google.com/citations?user={author_id}&hl=en'
                        })

    # Save to CSV
    df = pd.DataFrame(all_citing_authors)
    df.to_csv(output_path, index=False)
    print(f'\nSaved {len(all_citing_authors)} citing authors to {output_path}')
    return df

def save_citation_info_for_debugging(scholar_id: str, output_path: str = 'citation_info_debug.csv'):
    '''
    Save citation information for debugging purposes.
    This function collects and saves the citation information about publications
    without running the full citation map generation process.
    '''
    print('Finding citation information for Google Scholar ID:', scholar_id)
    
    # Step 1: Get all publications
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    print(f'Found {len(publications)} publications')

    # Step 2: Collect citation information for each publication
    all_citations = []
    for pub in tqdm(publications, desc='Processing publications'):
        if 'bib' in pub:
            citation_info = {
                'title': pub['bib'].get('title', ''),
                'citation': pub['bib'].get('citation', ''),
                'pub_year': pub['bib'].get('pub_year', ''),
                'journal': pub['bib'].get('journal', ''),
                'volume': pub['bib'].get('volume', ''),
                'number': pub['bib'].get('number', ''),
                'pages': pub['bib'].get('pages', ''),
                'publisher': pub['bib'].get('publisher', ''),
                'num_citations': pub.get('num_citations', 0),
                'cites_per_year': str(pub.get('cites_per_year', {}))
            }
            all_citations.append(citation_info)

    # Save to CSV
    df = pd.DataFrame(all_citations)
    df.to_csv(output_path, index=False)
    print(f'\nSaved citation information for {len(all_citations)} publications to {output_path}')
    return df

if __name__ == '__main__':
    # Replace this with your Google Scholar ID.
    scholar_id = 'KreqRjAAAAAJ'
    
    # # Save author IDs for debugging
    # save_author_ids_for_debugging(scholar_id, 'author_ids_debug.csv')
    
    # Save citation information for debugging
    save_citation_info_for_debugging(scholar_id, 'citation_info_debug.csv')
    
    # Original citation map generation (commented out for now)
    # generate_citation_map(scholar_id, output_path='citation_map.html',
    #                     csv_output_path='citation_info.csv',
    #                     parse_csv=False,
    #                     cache_folder='cache', affiliation_conservative=True, num_processes=16,
    #                     use_proxy=False, pin_colorful=True, print_citing_affiliations=True)