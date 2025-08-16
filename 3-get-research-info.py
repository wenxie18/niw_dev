import os
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Survey-specific Google Sheet ID
SURVEY_SHEET_ID = '1MhIzhJjdYXWfGDFtzcH4gyanzn6TyTeeBolop0-P9EY'

def get_credentials():
    """Gets valid credentials using service account."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            config.GOOGLE_SHEETS_CREDENTIALS_PATH,
            scopes=SCOPES
        )
        return credentials
    except Exception as e:
        print(f"Error getting credentials: {str(e)}")
        return None

def create_or_load_template():
    """Create a template JSON with null values from the basic petition letter if it doesn't exist."""
    template_path = os.path.join(config.DATA_PATH, 'survey_template.json')
    
    if os.path.exists(template_path):
        # Load existing template
        with open(template_path, 'r') as f:
            return json.load(f)
    else:
        # Create new template
        with open(os.path.join(config.DATA_PATH, 'data_collections_basic_basic_petition_letter.json'), 'r') as f:
            template = json.load(f)
        
        # Set all values to null
        for key in template:
            template[key] = None
        
        # Save template for future use
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=2)
        
        return template

def load_question_mapping():
    """Load the survey questions mapping."""
    with open(os.path.join(config.DATA_PATH, 'survey_questions_mapping_v1.json'), 'r') as f:
        return json.load(f)

def get_survey_data(service, spreadsheet_id):
    """Get survey data from Google Sheets."""
    try:
        # Get the first sheet
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range='A1:ZZ'  # Adjust range as needed
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print('No data found.')
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    
    except Exception as e:
        print(f"Error getting survey data: {str(e)}")
        return None

def find_user_row(df, email):
    """Find the row corresponding to the user's email."""
    if 'What is your email (the same one you shared with us before)?' in df.columns:
        email_col = 'What is your email (the same one you shared with us before)?'
        user_row = df[df[email_col] == email]
        if not user_row.empty:
            return user_row.iloc[0]
    return None

def map_answers_to_template(user_row, question_mapping, template):
    """Map survey answers to the template using the question mapping."""
    # Create a copy of the template to avoid modifying the original
    filled_template = template.copy()
    
    # Flatten the questions mapping
    flat_mapping = {}
    for section in question_mapping['sections'].values():
        for key, question in section['questions'].items():
            flat_mapping[question] = key
    
    # Map answers - only for keys that exist in the template
    mapped_count = 0
    skipped_count = 0
    
    for question, answer in user_row.items():
        if question in flat_mapping:
            key = flat_mapping[question]
            # Only map if the key exists in the template
            if key in filled_template:
                filled_template[key] = answer
                mapped_count += 1
            else:
                print(f"Warning: Key '{key}' from question mapping not found in template, skipping...")
                skipped_count += 1
    
    print(f"Mapped {mapped_count} answers to template")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} answers (keys not in template)")
    
    return filled_template

def validate_question_mapping(question_mapping, template):
    """Validate that all keys in the question mapping exist in the template."""
    template_keys = set(template.keys())
    mapping_keys = set()
    
    # Collect all keys from the question mapping
    for section in question_mapping['sections'].values():
        for key in section['questions'].keys():
            mapping_keys.add(key)
    
    # Find keys that are in mapping but not in template
    missing_keys = mapping_keys - template_keys
    extra_keys = template_keys - mapping_keys
    
    if missing_keys:
        print(f"Warning: {len(missing_keys)} keys in question mapping are not in template:")
        for key in sorted(missing_keys):
            print(f"  - {key}")
    
    if extra_keys:
        print(f"Info: {len(extra_keys)} keys in template are not in question mapping:")
        for key in sorted(extra_keys):
            print(f"  - {key}")
    
    return len(missing_keys) == 0

def main():
    # Get credentials and build service
    creds = get_credentials()
    if creds is None:
        print("Failed to get credentials")
        return
        
    service = build('sheets', 'v4', credentials=creds)
    
    # Load question mapping
    question_mapping = load_question_mapping()
    
    # Create or load template
    template = create_or_load_template()
    
    # Validate question mapping against template
    print("Validating question mapping against template...")
    validate_question_mapping(question_mapping, template)
    print()
    
    # Get survey data using the survey-specific sheet ID
    df = get_survey_data(service, SURVEY_SHEET_ID)
    
    if df is not None:
        # Find user's row
        user_row = find_user_row(df, config.DEFAULT_EMAIL)
        
        if user_row is not None:
            # Map answers to template
            filled_template = map_answers_to_template(user_row, question_mapping, template)
            
            # Save the filled template
            output_path = os.path.join(config.OUTPUT_BASE_FOLDER, config.DEFAULT_EMAIL, 'survey_answers.json')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(filled_template, f, indent=2)
            
            print(f"Survey answers saved to: {output_path}")
        else:
            print(f"No data found for email: {config.DEFAULT_EMAIL}")
    else:
        print("Failed to get survey data")

if __name__ == '__main__':
    main() 