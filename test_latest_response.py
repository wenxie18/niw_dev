import pandas as pd
import config
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

def get_google_sheet_data(sheet_id, credentials_path):
    """Fetch data from a Google Sheet using the Google Sheets API."""
    try:
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            print(f"Credentials file not found at {credentials_path}")
            return None
            
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Build the service
        service = build('sheets', 'v4', credentials=credentials)
        
        # First, get the sheet metadata to determine the range
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        title = sheets[0].get("properties", {}).get("title", "Sheet1")
        
        # Get the sheet data with the full range
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range=f'{title}!A:ZZ'  # Read all columns up to ZZ
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("No data found in the Google Sheet")
            return None
            
        # Get headers and data separately
        headers = values[0]
        data = values[1:]
        
        # Find the maximum number of columns
        max_cols = max(len(headers), max(len(row) for row in data) if data else 0)
        
        # Pad headers and data rows to match max_cols
        headers = headers + [''] * (max_cols - len(headers))
        padded_data = []
        for row in data:
            padded_row = row + [''] * (max_cols - len(row))
            padded_data.append(padded_row)
            
        # Convert to DataFrame
        df = pd.DataFrame(padded_data, columns=headers)
        
        return df
        
    except Exception as e:
        print(f"Error reading from Google Sheet: {str(e)}")
        return None

def main():
    # Load data from Google Sheets
    df = get_google_sheet_data(config.GOOGLE_SHEET_ID, config.GOOGLE_SHEETS_CREDENTIALS_PATH)
    
    if df is None:
        print("Failed to load data from Google Sheets.")
        return
    
    # Find all rows for vaneshieh@gmail.com
    email_col = "S2.5. Email Address"
    user_rows = df[df[email_col] == "vaneshieh@gmail.com"]
    
    print(f"Found {len(user_rows)} responses for vaneshieh@gmail.com:")
    print("=" * 80)
    
    for i, (idx, row) in enumerate(user_rows.iterrows()):
        print(f"Response {i+1}:")
        print(f"  Timestamp: {row.get('Timestamp', 'N/A')}")
        print(f"  S6.25 (Nonprofit): '{row.get('S6.25. Are you a nonprofit organized as tax exempt or a governmental research organization?', 'N/A')}'")
        print(f"  S6.26 (25 or fewer): '{row.get('S6.26. Do you currently employ a total of 25 or fewer full-time equivalent employees in the United States, including all affiliates or subsidiaries of this company/organization?', 'N/A')}'")
        print()
    
    # Test the sorting logic
    if len(user_rows) > 1:
        print("Testing sorting logic:")
        user_rows_copy = user_rows.copy()
        user_rows_copy['Timestamp'] = pd.to_datetime(user_rows_copy['Timestamp'], errors='coerce')
        user_rows_sorted = user_rows_copy.sort_values('Timestamp', ascending=False)
        
        print(f"Most recent response (after sorting):")
        latest_row = user_rows_sorted.iloc[0]
        print(f"  Timestamp: {latest_row.get('Timestamp', 'N/A')}")
        print(f"  S6.25 (Nonprofit): '{latest_row.get('S6.25. Are you a nonprofit organized as tax exempt or a governmental research organization?', 'N/A')}'")
        print(f"  S6.26 (25 or fewer): '{latest_row.get('S6.26. Do you currently employ a total of 25 or fewer full-time equivalent employees in the United States, including all affiliates or subsidiaries of this company/organization?', 'N/A')}'")

if __name__ == "__main__":
    main() 