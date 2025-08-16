#how to import the citation map from scripts folder
#generate_citation_map

# Import the citation map directly from scripts folder
from scripts.citation_map.citation_map import generate_citation_map
from scripts.citation_map.citation_map import save_author_ids_for_debugging
from scripts.scrape_email import scrape_email_from_google_scholar_profile
import pandas as pd
import logging
import config
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import warnings
from tqdm import tqdm
import time

# Suppress oauth2client warning
warnings.filterwarnings('ignore', message='file_cache is only supported with oauth2client<4.0.0')

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('email_rank.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_google_sheet_data(sheet_id, credentials_path):
    """
    Fetch data from a Google Sheet using the Google Sheets API.
    """
    try:
        if not os.path.exists(credentials_path):
            logging.error("Credentials file not found at %s", credentials_path)
            return None
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        title = sheets[0].get("properties", {}).get("title", "Sheet1")
        
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range=f'{title}!A:ZZ'
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logging.error("No data found in the Google Sheet")
            return None
            
        headers = values[0]
        data = values[1:]
        
        max_cols = max(len(headers), max(len(row) for row in data))
        headers = headers + [''] * (max_cols - len(headers))
        padded_data = []
        for row in data:
            padded_row = row + [''] * (max_cols - len(row))
            padded_data.append(padded_row)
            
        df = pd.DataFrame(padded_data, columns=headers)
        df = df.astype(str)
        
        return df
        
    except Exception as e:
        logging.error("Error reading from Google Sheet: %s", str(e))
        return None

def add_emails_to_csv(csv_path):
    """
    Read the CSV file, scrape emails from Google Scholar profiles, and add them to the CSV.
    Uses a cache to avoid scraping the same profile multiple times.
    """
    logging.info(f"Starting email scraping process for CSV: {csv_path}")
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    logging.info(f"Found {len(df)} total entries in CSV")
    
    # Add a new column for emails
    df['email'] = ''
    
    # Create a cache for emails based on Google Scholar links
    email_cache = {}
    
    # Count valid entries
    valid_entries = df[~df['google_scholar_link'].isna() & (df['author_id'] != 'No_author_found')]
    logging.info(f"Found {len(valid_entries)} valid entries with Google Scholar links")
    
    # Process each row
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Scraping emails"):
        author_id = row['author_id']
        google_scholar_link = row['google_scholar_link']
        author_name = row['citing author name']
        
        # Skip if no valid author ID or link
        if pd.isna(author_id) or author_id == 'No_author_found' or pd.isna(google_scholar_link):
            continue
            
        # Check if we've already scraped this profile
        if google_scholar_link in email_cache:
            df.at[idx, 'email'] = email_cache[google_scholar_link]
            logging.debug(f"Using cached email for {author_name} ({google_scholar_link})")
            continue
            
        try:
            logging.info(f"Scraping email for {author_name} ({google_scholar_link})")
            
            # Add delay to avoid rate limiting
            time.sleep(2)
            
            # Scrape emails using the existing function
            emails = scrape_email_from_google_scholar_profile(google_scholar_link)
            
            # Cache and add the first email found (if any)
            if emails:
                email_cache[google_scholar_link] = emails[0]  # Store first email in cache
                df.at[idx, 'email'] = emails[0]  # Store first email in DataFrame
                logging.info(f"Found email for {author_name}: {emails[0]}")
            else:
                logging.warning(f"No email found for {author_name}")
                
        except Exception as e:
            logging.error(f"Error processing author {author_name} ({author_id}): {str(e)}")
            continue
    
    # Save the updated CSV
    output_path = csv_path.replace('.csv', '_with_emails.csv')
    df.to_csv(output_path, index=False)
    logging.info(f"Updated CSV saved to: {output_path}")
    logging.info(f"Total unique profiles scraped: {len(email_cache)}")
    
    # Print summary
    emails_found = df['email'].notna().sum()
    logging.info(f"Total emails found: {emails_found} out of {len(valid_entries)} valid entries")
    
    return df

def find_rank(affiliation, rank_df):
    """
    Find the rank of a university in the ranking dataframe.
    """
    if pd.isna(affiliation) or affiliation == 'No_author_found':
        return None
    
    # Try exact match first
    exact_match = rank_df[rank_df['Institution Name'].str.lower() == affiliation.lower()]
    if not exact_match.empty:
        return exact_match['RANK'].iloc[0]
    
    # Try partial match
    for _, row in rank_df.iterrows():
        if row['Institution Name'].lower() in affiliation.lower() or affiliation.lower() in row['Institution Name'].lower():
            return row['RANK']
    
    return None

def extract_first_number(rank):
    """
    Extract the first number from a rank value for sorting purposes.
    """
    if pd.isna(rank):
        return float('inf')
    if isinstance(rank, (int, float)):
        return float(rank)
    try:
        return float(str(rank).split('-')[0])
    except:
        return float('inf')

if __name__ == '__main__':
    # # Get data from Google Sheet
    # scholar_df = get_google_sheet_data(config.GOOGLE_SCHOLAR_SHEET_ID, config.GOOGLE_CREDENTIALS_PATH)
    # if scholar_df is None:
    #     logging.error("Failed to load data from Google Scholar Sheet. Exiting.")
    #     exit(1)
        
    # # Find the row matching the email from config
    # email_row = scholar_df[scholar_df["What's your email address used in your application with us at TurboNIW?"] == config.DEFAULT_EMAIL]
    # if email_row.empty:
    #     logging.error(f"No matching email found in the sheet: {config.DEFAULT_EMAIL}")
    #     exit(1)
        
    # # Get the Google Scholar profile link
    # scholar_link = email_row["2.1. What is your Google Scholar profile link?"].iloc[0]
    # if not scholar_link:
    #     logging.error("No Google Scholar profile link found for the email")
    #     exit(1)
        
    # # Extract the scholar ID from the link
    # try:
    #     scholar_id = scholar_link.split('user=')[1].split('&')[0]
    # except:
    #     logging.error("Could not extract scholar ID from the link")
    #     exit(1)

    scholar_id = 'KreqRjAAAAAJ&hl'
    # # Generate citation map and CSV
    csv_path = f'filled/{config.DEFAULT_EMAIL}/citation_info.csv'
    # generate_citation_map(scholar_id, output_path=f'filled/{config.DEFAULT_EMAIL}/citation_map.html', 
    #                       csv_output_path=csv_path)
    
    # Scrape emails and update CSV
    logging.info("Starting email scraping process...")
    citation_df = add_emails_to_csv(csv_path)
    #email_df.to_csv()

    # Read the data files
    rank_df = pd.read_excel('university_rank.xlsx')
    #citation_df = pd.read_csv(csv_path)

    # Add rank column to the dataframe
    citation_df['rank'] = citation_df['affiliation'].apply(lambda x: find_rank(x, rank_df))

    # Sort by rank, handling both numeric and range ranks
    citation_df['sort_rank'] = citation_df['rank'].apply(extract_first_number)
    citation_df = citation_df.sort_values(by='sort_rank', ascending=True)
    citation_df = citation_df.drop('sort_rank', axis=1)
    
    # Save the updated dataframe
    output_path = f'filled/{config.DEFAULT_EMAIL}/citation_info_with_ranks.csv'
    citation_df.to_csv(output_path, index=False)
    logging.info(f"Updated CSV with ranks saved to: {output_path}")
    logging.info(f"Total entries with ranks found: {citation_df['rank'].notna().sum()} out of {len(citation_df)} entries")
    
    