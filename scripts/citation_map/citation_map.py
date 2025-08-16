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
                            lat, lng, county, city, state, country = '', '', '', '', '', ''
                    
                    # If we got valid coordinates, break the retry loop
                    if lat and lng:
                        break
                except Exception as e:
                    print(f"Error geocoding {affiliation_name}: {str(e)}")
                    if attempt == max_attempts - 1:
                        lat, lng, county, city, state, country = '', '', '', '', '', ''
                    continue

            # Cache the results
            geocode_cache[affiliation_name] = {
                'lat': lat,
                'lng': lng,
                'county': county,
                'city': city,
                'state': state,
                'country': country
            }

            # Use the geocoded data for all entries with this affiliation
            corresponding_entries = affiliation_map[affiliation_name]
            for entry_idx in corresponding_entries:
                author_name, citing_paper_title, cited_paper_title, affiliation_name, author_id, *rest = author_paper_affiliation_tuple_list[entry_idx]
                citation = rest[0] if rest else ''
                coordinates_and_info.append((author_name, citing_paper_title, cited_paper_title, affiliation_name,
                                           lat, lng, county, city, state, country, author_id, citation))
            num_located_affiliations += 1

    # Save the updated cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(geocode_cache, f)
    except Exception as e:
        print(f"Error saving cache file: {str(e)}")

    print(f"\nSuccessfully located {num_located_affiliations} out of {num_total_affiliations} unique affiliations.")
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
    """
    Create an interactive map using Folium.
    """
    # Create a map centered at the mean of all coordinates
    valid_coords = [(float(lat), float(lng)) for _, _, _, _, lat, lng, _, _, _, _, _, _ in coordinates_and_info 
                    if lat and lng and lat != '' and lng != '']
    
    if not valid_coords:
        print("No valid coordinates found to create map.")
        return None
    
    mean_lat = sum(lat for lat, _ in valid_coords) / len(valid_coords)
    mean_lng = sum(lng for _, lng in valid_coords) / len(valid_coords)
    
    m = folium.Map(location=[mean_lat, mean_lng], zoom_start=2)
    
    # Add markers for each location
    for author_name, citing_paper_title, cited_paper_title, affiliation_name, lat, lng, county, city, state, country, author_id, citation in coordinates_and_info:
        if not lat or not lng or lat == '' or lng == '':
            continue
            
        # Create popup content
        popup_content = f"""
        <b>Author:</b> {author_name}<br>
        <b>Affiliation:</b> {affiliation_name}<br>
        <b>Citing Paper:</b> {citing_paper_title}<br>
        <b>Cited Paper:</b> {cited_paper_title}<br>
        <b>Location:</b> {city}, {state}, {country}<br>
        <b>Citation:</b> {citation}
        """
        
        # Choose marker color based on pin_colorful flag
        if pin_colorful:
            # Use a random color for each marker
            color = random.choice(['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray'])
        else:
            color = 'red'
            
        # Add marker to map
        folium.Marker(
            location=[float(lat), float(lng)],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)
    
    return m

def __fill_publication_metadata(pub):
    """
    Fill metadata for a single publication.
    """
    try:
        return scholarly.fill(pub)
    except Exception as e:
        print(f"Error filling publication metadata: {str(e)}")
        return pub

def __citing_authors_and_papers_from_publication(cites_id_and_cited_paper: Tuple[str, str]):
    """
    Get citing authors and papers for a single publication.
    """
    cites_id, cited_paper_title, citation = cites_id_and_cited_paper
    try:
        citing_author_ids, citing_papers = get_citing_author_ids_and_citing_papers(cites_id)
        # Zip the two lists together to create proper tuples
        result = []
        for author_id, paper_info in zip(citing_author_ids, citing_papers):
            if isinstance(paper_info, dict):
                citing_paper_title = paper_info.get('title', 'Unknown Title')
            else:
                citing_paper_title = str(paper_info)
            result.append((author_id, citing_paper_title, cited_paper_title, citation))
        return result
    except Exception as e:
        print(f"Error getting citing authors for paper {cited_paper_title}: {str(e)}")
        return []

def __affiliations_from_authors_conservative(citing_author_paper_info: str):
    """
    Get affiliations from authors using conservative approach.
    """
    author_id, citing_paper_title, cited_paper_title, citation = citing_author_paper_info
    try:
        author = scholarly.search_author_id(author_id)
        author = scholarly.fill(author, sections=['affiliation'])
        affiliation = author.get('affiliation', NO_AUTHOR_FOUND_STR)
        author_name = author.get('name', NO_AUTHOR_FOUND_STR)
        return (author_name, citing_paper_title, cited_paper_title, affiliation, author_id, citation)
    except Exception as e:
        print(f"Error getting affiliation for author {author_id}: {str(e)}")
        return (NO_AUTHOR_FOUND_STR, citing_paper_title, cited_paper_title, NO_AUTHOR_FOUND_STR, author_id, citation)

def __affiliations_from_authors_aggressive(citing_author_paper_info: str):
    """
    Get affiliations from authors using aggressive approach.
    """
    author_id, citing_paper_title, cited_paper_title, citation = citing_author_paper_info
    try:
        author = scholarly.search_author_id(author_id)
        author = scholarly.fill(author, sections=['affiliation'])
        affiliation = author.get('affiliation', NO_AUTHOR_FOUND_STR)
        author_name = author.get('name', NO_AUTHOR_FOUND_STR)
        return (author_name, citing_paper_title, cited_paper_title, affiliation, author_id, citation)
    except Exception as e:
        print(f"Error getting affiliation for author {author_id}: {str(e)}")
        return (NO_AUTHOR_FOUND_STR, citing_paper_title, cited_paper_title, NO_AUTHOR_FOUND_STR, author_id, citation)

def __country_aware_comma_split(string_list: List[str]) -> List[str]:
    """
    Split strings by comma, but be aware of country names.
    """
    result = []
    for string in string_list:
        if not string:
            continue
        parts = string.split(',')
        current_part = parts[0]
        for part in parts[1:]:
            if __iscountry(part.strip()):
                result.append(current_part.strip())
                current_part = part
            else:
                current_part += ',' + part
        result.append(current_part.strip())
    return result

def __iscountry(string: str) -> bool:
    """
    Check if a string is a country name.
    """
    try:
        return pycountry.countries.get(name=string) is not None
    except:
        return False

def __print_author_and_affiliation(author_paper_affiliation_tuple_list: List[Tuple[str]]) -> None:
    """
    Print author and affiliation information.
    """
    for item in author_paper_affiliation_tuple_list:
        # Handle both 6-value and 12-value tuples
        if len(item) == 6:
            author_name, citing_paper_title, cited_paper_title, affiliation_name, author_id, citation = item
        elif len(item) == 12:
            author_name, citing_paper_title, cited_paper_title, affiliation_name, lat, lng, county, city, state, country, author_id, citation = item
        else:
            print(f"Unexpected tuple length: {len(item)}")
            continue
            
        print(f"Author: {author_name}")
        print(f"Affiliation: {affiliation_name}")
        print(f"Citing Paper: {citing_paper_title}")
        print(f"Cited Paper: {cited_paper_title}")
        print(f"Citation: {citation}")
        print("-" * 80)

def save_cache(data: Any, fpath: str) -> None:
    """
    Save data to cache file.
    """
    with open(fpath, 'wb') as f:
        pickle.dump(data, f)

def load_cache(fpath: str) -> Any:
    """
    Load data from cache file.
    """
    with open(fpath, 'rb') as f:
        return pickle.load(f)

def setup_proxy_system(max_retries=3):
    """
    Set up proxy system for scholarly.
    """
    pg = ProxyGenerator()
    success = False
    for attempt in range(max_retries):
        try:
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                print("Successfully set up proxy system.")
                break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to set up proxy: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print("Failed to set up proxy system after all attempts.")
    return success

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
    """
    Generate citation map for a given scholar ID.
    """
    if use_proxy:
        setup_proxy_system()
    
    if parse_csv:
        coordinates_and_info = read_csv_to_dict(csv_output_path)
    else:
        # Step 1: Find all citing authors
        all_citing_author_paper_tuple_list = find_all_citing_authors(scholar_id, num_processes)
        
        # Step 2: Find all citing affiliations
        author_paper_affiliation_tuple_list = find_all_citing_affiliations(
            all_citing_author_paper_tuple_list,
            num_processes,
            affiliation_conservative
        )
        
        # Optional Step: Clean up affiliation names
        cleaned_author_paper_affiliation_tuple_list = clean_affiliation_names(author_paper_affiliation_tuple_list)
        
        # Step 3: Convert affiliations to geocodes
        coordinates_and_info = affiliation_text_to_geocode(cleaned_author_paper_affiliation_tuple_list)
        
        # Export to CSV
        export_dict_to_csv(coordinates_and_info, csv_output_path)
    
    # Create and save the map
    m = create_map(coordinates_and_info, pin_colorful)
    if m:
        m.save(output_path)
        print(f"Map saved to {output_path}")
    
    if print_citing_affiliations:
        __print_author_and_affiliation(coordinates_and_info)
    
    return coordinates_and_info

def save_author_ids_for_debugging(scholar_id: str, output_path: str = 'author_ids_debug.csv'):
    """
    Save author IDs for debugging purposes.
    """
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    
    author_ids = []
    for pub in publications:
        try:
            pub = scholarly.fill(pub)
            if 'cites_id' in pub:
                for cites_id in pub['cites_id']:
                    citing_author_ids, citing_papers = get_citing_author_ids_and_citing_papers(cites_id)
                    author_ids.extend(citing_author_ids)
        except Exception as e:
            print(f"Error processing publication: {str(e)}")
    
    # Save to CSV
    df = pd.DataFrame({'author_id': author_ids})
    df.to_csv(output_path, index=False)
    print(f"Saved {len(author_ids)} author IDs to {output_path}")

def save_citation_info_for_debugging(scholar_id: str, output_path: str = 'citation_info_debug.csv'):
    """
    Save citation information for debugging purposes.
    """
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=['publications'])
    publications = author['publications']
    
    citation_info = []
    for pub in publications:
        try:
            pub = scholarly.fill(pub)
            if 'cites_id' in pub:
                for cites_id in pub['cites_id']:
                    citing_author_ids, citing_papers = get_citing_author_ids_and_citing_papers(cites_id)
                    for author_id, paper_info in zip(citing_author_ids, citing_papers):
                        if isinstance(paper_info, dict):
                            citing_paper_title = paper_info.get('title', 'Unknown Title')
                        else:
                            citing_paper_title = str(paper_info)
                        citation_info.append({
                            'author_id': author_id,
                            'citing_paper_title': citing_paper_title,
                            'cited_paper_title': pub['bib']['title']
                        })
        except Exception as e:
            print(f"Error processing publication: {str(e)}")
    
    # Save to CSV
    df = pd.DataFrame(citation_info)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(citation_info)} citation records to {output_path}")

if __name__ == '__main__':
    # Replace this with your Google Scholar ID.
    scholar_id = 'KreqRjAAAAAJ'
    
    # # Save author IDs for debugging
    # save_author_ids_for_debugging(scholar_id, 'author_ids_debug.csv')
    
    # Save citation information for debugging
    save_citation_info_for_debugging(scholar_id, 'citation_info_debug.csv')
    
    # Original citation map generation (commented out for now)
    generate_citation_map(scholar_id, output_path='citation_map.html',
                        csv_output_path='citation_info.csv',
                        parse_csv=False,
                        cache_folder='cache', affiliation_conservative=True, num_processes=16,
                        use_proxy=False, pin_colorful=True, print_citing_affiliations=True)