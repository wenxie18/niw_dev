import pandas as pd
import config
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

def get_google_sheet_data_detailed(sheet_id, credentials_path):
    """Fetch data from a Google Sheet with detailed debugging."""
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
        
        print(f"Sheet title: {title}")
        
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
            
        print(f"Total rows in sheet: {len(values)}")
        print(f"First row (headers): {values[0]}")
        
        # Get headers and data separately
        headers = values[0]
        data = values[1:]
        
        # Find the maximum number of columns
        max_cols = max(len(headers), max(len(row) for row in data) if data else 0)
        
        print(f"Maximum columns: {max_cols}")
        print(f"Headers length: {len(headers)}")
        
        # Pad headers and data rows to match max_cols
        headers = headers + [''] * (max_cols - len(headers))
        padded_data = []
        for i, row in enumerate(data):
            padded_row = row + [''] * (max_cols - len(row))
            padded_data.append(padded_row)
            if i < 3:  # Show first 3 rows for debugging
                print(f"Row {i+1}: {padded_row}")
        
        # Convert to DataFrame
        df = pd.DataFrame(padded_data, columns=headers)
        
        return df
        
    except Exception as e:
        print(f"Error reading from Google Sheet: {str(e)}")
        return None

def main():
    # Load data from Google Sheets
    print("Fetching data from Google Sheet...")
    df = get_google_sheet_data_detailed(config.GOOGLE_SHEET_ID, config.GOOGLE_SHEETS_CREDENTIALS_PATH)
    
    if df is None:
        print("Failed to load data from Google Sheets.")
        return
    
    print(f"\nDataFrame shape: {df.shape}")
    print(f"DataFrame columns: {len(df.columns)}")
    
    # Find the row for vaneshieh@gmail.com
    email_col = "S2.5. Email Address"
    if email_col in df.columns:
        print(f"\nEmail column found: {email_col}")
        user_row = df[df[email_col] == "vaneshieh@gmail.com"]
        if not user_row.empty:
            row = user_row.iloc[0]
            print(f"Found data for vaneshieh@gmail.com")
            
            # Check the two specific questions
            question1 = "S6.25. Are you a nonprofit organized as tax exempt or a governmental research organization?"
            question2 = "S6.26. Do you currently employ a total of 25 or fewer full-time equivalent employees in the United States, including all affiliates or subsidiaries of this company/organization?"
            
            print(f"\nDetailed analysis:")
            print(f"=" * 80)
            
            # Check if columns exist
            print(f"Question 1 column exists: {question1 in df.columns}")
            print(f"Question 2 column exists: {question2 in df.columns}")
            
            if question1 in df.columns:
                print(f"\nQuestion 1: {question1}")
                print(f"Raw answer: '{row.get(question1, 'NOT FOUND')}'")
                print(f"Answer type: {type(row.get(question1, 'NOT FOUND'))}")
                print(f"Answer length: {len(str(row.get(question1, 'NOT FOUND')))}")
                print(f"Answer repr: {repr(row.get(question1, 'NOT FOUND'))}")
                
                # Check all rows for this column
                print(f"\nAll values in this column:")
                for i, val in enumerate(df[question1]):
                    print(f"  Row {i+1}: '{val}' (type: {type(val)})")
            
            if question2 in df.columns:
                print(f"\nQuestion 2: {question2}")
                print(f"Raw answer: '{row.get(question2, 'NOT FOUND')}'")
                print(f"Answer type: {type(row.get(question2, 'NOT FOUND'))}")
                print(f"Answer length: {len(str(row.get(question2, 'NOT FOUND')))}")
                print(f"Answer repr: {repr(row.get(question2, 'NOT FOUND'))}")
                
                # Check all rows for this column
                print(f"\nAll values in this column:")
                for i, val in enumerate(df[question2]):
                    print(f"  Row {i+1}: '{val}' (type: {type(val)})")
            
            print(f"=" * 80)
            
            # Show all columns that might be related
            print(f"\nAll columns containing 'nonprofit' or '25 or fewer':")
            for col in df.columns:
                if 'nonprofit' in col.lower() or '25 or fewer' in col.lower():
                    print(f"Column: {col}")
                    print(f"Value: '{row.get(col, 'NOT FOUND')}'")
                    print()
                    
        else:
            print(f"No data found for email: vaneshieh@gmail.com")
            print("Available emails:")
            if email_col in df.columns:
                for email in df[email_col].unique():
                    if email and email != '':
                        print(f"  {email}")
    else:
        print(f"Email column '{email_col}' not found in the data")
        print("Available columns containing 'email':")
        for col in df.columns:
            if 'email' in col.lower():
                print(f"  {col}")

if __name__ == "__main__":
    main() 