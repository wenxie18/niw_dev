#!/usr/bin/env python3
"""
Debug script to examine line break characters in survey data
"""

import pandas as pd
import config
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def get_google_sheet_data(sheet_id, credentials_path):
    """Fetch data from Google Sheets."""
    try:
        # Load credentials
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Build service
        service = build('sheets', 'v4', credentials=creds)
        
        # Get the sheet data
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A:ZZ'  # Get all columns
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print('No data found.')
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
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
    
    # Find the row for zxiliang51@gmail.com
    email_col = "S2.5. Email Address"
    if email_col in df.columns:
        user_row = df[df[email_col] == "zxiliang51@gmail.com"]
        if not user_row.empty:
            row = user_row.iloc[0]
            
            # Check the job duties field
            job_duties_col = "S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"
            
            if job_duties_col in df.columns:
                job_duties_text = row.get(job_duties_col, 'NOT FOUND')
                
                print(f"Job Duties text for zxiliang51@gmail.com:")
                print(f"=" * 80)
                print(f"Raw text: {repr(job_duties_text)}")
                print(f"Text type: {type(job_duties_text)}")
                print(f"Text length: {len(str(job_duties_text))}")
                print()
                
                # Check for different types of line breaks
                if isinstance(job_duties_text, str):
                    print(f"Contains \\n: {'\\n' in job_duties_text}")
                    print(f"Contains \\r: {'\\r' in job_duties_text}")
                    print(f"Contains \\r\\n: {'\\r\\n' in job_duties_text}")
                    print(f"Contains \\t: {'\\t' in job_duties_text}")
                    print()
                    
                    # Show the actual characters
                    print("Character by character analysis:")
                    for i, char in enumerate(job_duties_text):
                        if char in ['\n', '\r', '\t']:
                            print(f"  Position {i}: {repr(char)}")
                    
                    print()
                    print("Lines when split by \\n:")
                    lines = job_duties_text.split('\n')
                    for i, line in enumerate(lines):
                        print(f"  Line {i+1}: {repr(line)}")
                        if line.strip():
                            print(f"    Length: {len(line)}")
                        else:
                            print(f"    (empty line)")
                
                print(f"=" * 80)
            else:
                print(f"Job duties column not found: {job_duties_col}")
        else:
            print(f"No data found for email: zxiliang51@gmail.com")
    else:
        print(f"Email column not found: {email_col}")

if __name__ == "__main__":
    main()
