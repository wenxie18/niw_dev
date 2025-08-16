import os
import requests
from scholarly import scholarly
import pandas as pd
import logging
from tqdm import tqdm
import time
from urllib.parse import urlparse
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_download.log'),
        logging.StreamHandler()
    ]
)

def create_pdf_folder(email):
    """Create a folder for storing PDFs based on email."""
    base_folder = 'filled'
    email_folder = os.path.join(base_folder, email)
    pdf_folder = os.path.join(email_folder, 'pdfs')
    
    # Create folders if they don't exist
    os.makedirs(pdf_folder, exist_ok=True)
    return pdf_folder

def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 150:
        filename = filename[:150]
    return filename

def download_pdf(pdf_url, output_path):
    try:
        response = requests.get(pdf_url, timeout=10)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True, None
        else:
            return False, "HTTP Error: " + str(response.status_code)
    except Exception as e:
        return False, str(e)

def get_publication_pdfs(scholar_id, email):
    """Get all publications and download their PDFs for a given scholar ID."""
    try:
        # Create PDF folder
        pdf_folder = create_pdf_folder(email)
        logging.info("Created PDF folder at: %s" % pdf_folder)
        
        # Create or load download status CSV
        status_file = os.path.join('filled', email, 'publication_download_status.csv')
        if os.path.exists(status_file):
            status_df = pd.read_csv(status_file)
            logging.info("Loaded existing status file: %s" % status_file)
        else:
            status_df = pd.DataFrame(columns=['paper_title', 'download_status', 'error_message', 'pdf_path'])
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
                
                # Try to get PDF URL
                pdf_url = None
                if pub.get('eprint_url'):
                    pdf_url = pub['eprint_url']
                elif pub.get('pub_url'):
                    try:
                        response = requests.get(pub['pub_url'], timeout=10)
                        if response.status_code == 200:
                            pdf_links = re.findall(r'href=[\'"]?([^\'" >]+\.pdf)', response.text)
                            if pdf_links:
                                pdf_url = pdf_links[0]
                    except:
                        pass
                
                # Download PDF if URL found
                if pdf_url:
                    success, error = download_pdf(pdf_url, pdf_path)
                    if success:
                        status = "Downloaded"
                        error_msg = None
                    else:
                        status = "Failed"
                        error_msg = error
                else:
                    status = "No PDF URL found"
                    error_msg = None
                
                # Add to status DataFrame
                new_row = pd.DataFrame({
                    'paper_title': [title],
                    'download_status': [status],
                    'error_message': [error_msg],
                    'pdf_path': [pdf_path if status == "Downloaded" else None]
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
        no_url = (status_df['download_status'] == 'No PDF URL found').sum()
        
        logging.info("\nDownload Summary:")
        logging.info("Total publications: %d" % total)
        logging.info("Successfully downloaded: %d" % downloaded)
        logging.info("Failed downloads: %d" % failed)
        logging.info("No PDF URL found: %d" % no_url)
        logging.info("Status saved to: %s" % status_file)
        
    except Exception as e:
        logging.error("Error getting publications: %s" % str(e))

if __name__ == '__main__':
    # Test with your Google Scholar ID
    scholar_id = 'KreqRjAAAAAJ'
    email = 'vaneshieh@gmail.com'
    
    logging.info("Starting PDF download for scholar ID: %s" % scholar_id)
    get_publication_pdfs(scholar_id, email)
    logging.info("PDF download process completed") 