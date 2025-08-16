import pandas as pd
import config
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
        max_cols = max(len(headers), max(len(row) for row in data))
        
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
    
    # Find the row for vaneshieh@gmail.com
    email_col = "S2.5. Email Address"
    if email_col in df.columns:
        user_row = df[df[email_col] == "vaneshieh@gmail.com"]
        if not user_row.empty:
            row = user_row.iloc[0]
            
            # Check the two specific questions
            question1 = "S6.25. Are you a nonprofit organized as tax exempt or a governmental research organization?"
            question2 = "S6.26. Do you currently employ a total of 25 or fewer full-time equivalent employees in the United States, including all affiliates or subsidiaries of this company/organization?"
            
            print(f"Survey answers for vaneshieh@gmail.com:")
            print(f"=" * 80)
            print(f"Question 1: {question1}")
            print(f"Answer: '{row.get(question1, 'NOT FOUND')}'")
            print(f"Answer type: {type(row.get(question1, 'NOT FOUND'))}")
            print(f"Answer length: {len(str(row.get(question1, 'NOT FOUND')))}")
            print()
            print(f"Question 2: {question2}")
            print(f"Answer: '{row.get(question2, 'NOT FOUND')}'")
            print(f"Answer type: {type(row.get(question2, 'NOT FOUND'))}")
            print(f"Answer length: {len(str(row.get(question2, 'NOT FOUND')))}")
            print(f"=" * 80)
            
            # Also show all columns that contain "nonprofit" or "25 or fewer"
            print("\nAll columns containing 'nonprofit' or '25 or fewer':")
            for col in df.columns:
                if 'nonprofit' in col.lower() or '25 or fewer' in col.lower():
                    print(f"Column: {col}")
                    print(f"Value: '{row.get(col, 'NOT FOUND')}'")
                    print()
        else:
            print(f"No data found for email: vaneshieh@gmail.com")
    else:
        print(f"Email column '{email_col}' not found in the data")
        print("Available columns:")
        for col in df.columns:
            if 'email' in col.lower():
                print(f"  {col}")

if __name__ == "__main__":
    import os
    main() 