import os
import requests
from scholarly import scholarly
import pandas as pd
import logging
from tqdm import tqdm
import time
from urllib.parse import urlparse, urljoin
import re
import json
from bs4 import BeautifulSoup
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib3
import config
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_PATH, 'pdf_download_comprehensive.log')),
        logging.StreamHandler()
    ]
)

def create_pdf_folder(email):
    """Create a folder for storing PDFs based on email."""
    pdf_folder = os.path.join(config.OUTPUT_BASE_FOLDER, email, 'pdfs')
    
    # Create folders if they don't exist
    os.makedirs(pdf_folder, exist_ok=True)
    return pdf_folder

def download_pdf(pdf_url, output_path, headers=None):
    """Download PDF with improved error handling and retries."""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(pdf_url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True, None
            elif response.status_code == 403:
                # Try with different headers
                headers['User-Agent'] = random.choice([
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                ])
                time.sleep(2)  # Wait before retry
                continue
            else:
                return False, f"HTTP Error: {response.status_code}"
        except Exception as e:
            if attempt == max_retries - 1:
                return False, str(e)
            time.sleep(2)  # Wait before retry
    return False, "Max retries exceeded"

def get_doi_from_crossref(title):
    """Search for DOI using CrossRef API."""
    try:
        url = f"https://api.crossref.org/works?query.title={requests.utils.quote(title)}&rows=1"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['message']['items']:
                return data['message']['items'][0]['DOI']
    except Exception as e:
        logging.warning(f"Error getting DOI from CrossRef: {str(e)}")
    return None

def get_pdf_from_doi(doi):
    """Get PDF URL from DOI using Unpaywall API."""
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=your-email@example.com"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('best_oa_location'):
                return data['best_oa_location']['url_for_pdf']
    except Exception as e:
        logging.warning(f"Error getting PDF from DOI: {str(e)}")
    return None

def search_researchgate(title):
    """Search for PDF on ResearchGate."""
    try:
        search_url = f"https://www.researchgate.net/search/publication?q={requests.utils.quote(title)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for PDF download links
            pdf_links = soup.find_all('a', href=re.compile(r'.*\.pdf$'))
            if pdf_links:
                return pdf_links[0]['href']
    except Exception as e:
        logging.warning(f"Error searching ResearchGate: {str(e)}")
    return None

def search_academia(title):
    """Search for PDF on Academia.edu."""
    try:
        search_url = f"https://www.academia.edu/search?q={requests.utils.quote(title)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for PDF download links
            pdf_links = soup.find_all('a', href=re.compile(r'.*\.pdf$'))
            if pdf_links:
                return pdf_links[0]['href']
    except Exception as e:
        logging.warning(f"Error searching Academia.edu: {str(e)}")
    return None

def get_pdf_urls(pub):
    """Get PDF URLs from multiple sources."""
    pdf_urls = []
    title = pub['bib']['title']
    
    # 1. Try Google Scholar's eprint_url
    if pub.get('eprint_url'):
        pdf_urls.append(pub['eprint_url'])
    
    # 2. Try publication URL
    if pub.get('pub_url'):
        try:
            response = requests.get(pub['pub_url'], timeout=10, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for PDF links
                pdf_links = soup.find_all('a', href=re.compile(r'.*\.pdf$'))
                for link in pdf_links:
                    pdf_url = link['href']
                    if not urlparse(pdf_url).netloc:  # If relative URL
                        pdf_url = urljoin(pub['pub_url'], pdf_url)
                    pdf_urls.append(pdf_url)
        except Exception as e:
            logging.warning(f"Error getting PDF from publication URL: {str(e)}")
    
    # 3. Try DOI-based search
    doi = get_doi_from_crossref(title)
    if doi:
        pdf_url = get_pdf_from_doi(doi)
        if pdf_url:
            pdf_urls.append(pdf_url)
    
    # 4. Try ResearchGate
    pdf_url = search_researchgate(title)
    if pdf_url:
        pdf_urls.append(pdf_url)
    
    # 5. Try Academia.edu
    pdf_url = search_academia(title)
    if pdf_url:
        pdf_urls.append(pdf_url)
    
    return pdf_urls

def get_publication_pdfs(scholar_id, email):
    """Get all publications and download their PDFs for a given scholar ID."""
    try:
        # Create PDF folder
        pdf_folder = create_pdf_folder(email)
        logging.info("Created PDF folder at: %s" % pdf_folder)
        
        # Create or load download status CSV
        status_file = os.path.join(config.OUTPUT_BASE_FOLDER, email, 'publication_download_status_comprehensive.csv')
        if os.path.exists(status_file):
            status_df = pd.read_csv(status_file)
            logging.info("Loaded existing status file: %s" % status_file)
        else:
            status_df = pd.DataFrame(columns=['paper_title', 'download_status', 'error_message', 'pdf_path', 'source'])
            logging.info("Created new status file: %s" % status_file)
        
        # Get author's publications
        author = scholarly.search_author_id(scholar_id)
        author = scholarly.fill(author, sections=['publications'])
        publications = author['publications']
        
        logging.info("Found %d publications" % len(publications))
        
        # Process each publication
        for pub in tqdm(publications, desc="Processing publications"):
            try:
                # Skip if already processed
                if pub['bib']['title'] in status_df['paper_title'].values:
                    continue
                    
                # Get publication details
                pub = scholarly.fill(pub)
                title = pub['bib']['title']
                
                # Clean title for filename
                safe_title = re.sub(r'[^\w\s-]', '', title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-_')
                pdf_path = os.path.join(pdf_folder, safe_title + ".pdf")
                
                # Try to get PDF URLs from multiple sources
                pdf_urls = get_pdf_urls(pub)
                
                # Try each PDF URL until successful
                success = False
                error_msg = None
                source = None
                
                for pdf_url in pdf_urls:
                    logging.info(f"Trying to download PDF from: {pdf_url}")
                    success, error = download_pdf(pdf_url, pdf_path)
                    if success:
                        source = pdf_url
                        break
                
                if success:
                    status = "Downloaded"
                    error_msg = None
                else:
                    status = "Failed"
                    error_msg = "No valid PDF found from any source"
                
                # Add to status DataFrame
                new_row = pd.DataFrame({
                    'paper_title': [title],
                    'download_status': [status],
                    'error_message': [error_msg],
                    'pdf_path': [pdf_path if status == "Downloaded" else None],
                    'source': [source]
                })
                status_df = pd.concat([status_df, new_row], ignore_index=True)
                
                # Save status after each download
                status_df.to_csv(status_file, index=False)
                
            except Exception as e:
                logging.error("Error processing publication: %s" % str(e))
                continue
                
        # Print summary
        total = len(status_df)
        downloaded = (status_df['download_status'] == 'Downloaded').sum()
        failed = (status_df['download_status'] == 'Failed').sum()
        
        logging.info("\nDownload Summary:")
        logging.info("Total publications: %d" % total)
        logging.info("Successfully downloaded: %d" % downloaded)
        logging.info("Failed downloads: %d" % failed)
        logging.info("Status saved to: %s" % status_file)
        
    except Exception as e:
        logging.error("Error getting publications: %s" % str(e))

if __name__ == '__main__':
    # Test with your Google Scholar ID
    scholar_id = 'KreqRjAAAAAJ'
    email = 'vaneshieh@gmail.com'
    
    logging.info("Starting comprehensive PDF download for scholar ID: %s" % scholar_id)
    get_publication_pdfs(scholar_id, email)
    logging.info("PDF download process completed") 