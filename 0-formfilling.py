import argparse
import pandas as pd
import fitz  # PyMuPDF
import json
import os
import math
import config # Import configuration from config.py
import logging
from datetime import datetime
import re
from textwrap3 import wrap
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Path to the Chinese font file
default_font_name = "helv"  # Built-in Helvetica font in PyMuPDF
chinese_font_name = "china-s"

def get_google_sheet_data(sheet_id, credentials_path):
    """
    Fetch data from a Google Sheet using the Google Sheets API.
    
    Args:
        sheet_id (str): The ID of the Google Sheet to read from
        credentials_path (str): Path to the service account credentials JSON file
        
    Returns:
        pandas.DataFrame: The data from the Google Sheet, or None if there was an error
    """
    try:
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logging.error("Credentials file not found at %s", credentials_path)
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
            logging.error("No data found in the Google Sheet")
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
        
        # Convert all columns to string to maintain consistency with Excel reading
        df = df.astype(str)
        
        return df
        
    except Exception as e:
        logging.error("Error reading from Google Sheet: %s", str(e))
        return None

def contains_chinese(text):
    """Check if the text contains any Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def fill_static_pdf(static_pdf_path, output_pdf_path, mapping, data):
    """Fills a static PDF form with data from a dictionary."""
    try:
        logging.info(f"Opening PDF: {static_pdf_path}")
        doc = fitz.open(static_pdf_path)
        field_mapping, checkbox_mapping = mapping

        # Log some basic info
        logging.info(f"Number of pages in PDF: {len(doc)}")
        logging.info(f"Number of fields to fill: {len(field_mapping)}")
        if checkbox_mapping:
            logging.info(f"Number of checkboxes to fill: {len(checkbox_mapping)}")

        for field_name in field_mapping.keys():
            try:
                key = field_mapping[field_name]['key']
                page_index = field_mapping[field_name]['page_index']
                x0, y0 = field_mapping[field_name]['position']
                fill = field_mapping[field_name]['fill']
                value = data.get(key, '')  # Use .get() to handle missing keys gracefully
                # Handle NaN values properly
                if isinstance(value, float) and math.isnan(value):
                    value = None  # Replace NaN None

                # Adjust font size if the text contains Chinese characters
                font_size = config.FONT_SIZE_LARGE if contains_chinese(str(value)) else config.FONT_SIZE
                font_name = chinese_font_name if contains_chinese(str(value)) else default_font_name

                if value is not None and fill:
                    if page_index >= len(doc):
                        logging.error(f"Invalid page index {page_index} for field {field_name}. PDF has {len(doc)} pages.")
                        continue
                    page = doc[page_index]
                    page.insert_text((x0, y0), str(value), fontsize=font_size, fontname=font_name)
            except Exception as e:
                logging.error(f"Error filling field {field_name}: {str(e)}")
        
        if checkbox_mapping:
            for field_name in checkbox_mapping.keys():
                try:
                    key = checkbox_mapping[field_name]['key']
                    page_index = checkbox_mapping[field_name]['page_index']
                    fill = checkbox_mapping[field_name]['fill']
                    value = data.get(key, '')  # Use .get() to handle missing keys gracefully
                    #print(key, value)
                    # Handle NaN values properly
                    if isinstance(value, float) and math.isnan(value):
                        value = None  # Replace NaN with None
                    else:
                        #checkbox location
                        #check if page index change
                        if len(checkbox_mapping[field_name]['subkey'][value])==3:
                            page_index, x0, y0 = checkbox_mapping[field_name]['subkey'][value]
                        else:
                            x0, y0 = checkbox_mapping[field_name]['subkey'][value]
                        rect = x0, y0, x0+20, y0+20

                    if value is not None and fill:
                        if page_index >= len(doc):
                            logging.error(f"Invalid page index {page_index} for checkbox {field_name}. PDF has {len(doc)} pages.")
                            continue
                        page = doc[page_index]
                        page.insert_image(rect, filename="checkmark.png")  # Use filename or another image source 
                except Exception as e:
                    logging.error(f"Error filling checkbox {field_name}: {str(e)}")

        logging.info(f"Saving filled PDF to: {output_pdf_path}")
        doc.save(output_pdf_path)
        doc.close()
        logging.info(f"Filled form saved as {output_pdf_path}")
        print(f"Filled form saved as {output_pdf_path}")
    except Exception as e:
        logging.error(f"Failed to fill static PDF: {str(e)}")
        if 'doc' in locals():
            doc.close()

def create_output_folder(base_folder, email_address):
    """Creates a unique folder for each email address under the base folder."""
    email_folder = os.path.join(base_folder, email_address)

    if not os.path.exists(email_folder):
        os.makedirs(email_folder)
        logging.info(f"Created folder: {email_folder}")
    else:
        logging.info(f"Folder already exists: {email_folder}")

    return email_folder

def generate_output_file_path(folder, form_name, timestamp=None):
    """Generates a unique output file path."""
    if timestamp:
        #return os.path.join(folder, f"filled_{form_name}_{timestamp}.pdf")
        return os.path.join(folder, f"filled_{form_name}.pdf")
    else:
        return os.path.join(folder, f"filled_{form_name}.pdf")

def custom_spacing_uscis(number_str, spaces=[2, 3, 2, 2, 3, 3, 2, 2, 2, 2, 2]):  
    """  
    11space, 12 digits
    Add custom spaces between digits based on the specified space list.  
    """  
    digits = list(number_str)  
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing  

    return spaced_str 

def custom_spacing_i94(number_str, spaces=[2, 3, 2, 2, 3, 3, 2, 2, 2, 2]):  
    """  
    10space, 11 digits
    Add custom spaces between digits based on the specified space list.  
    """  
    digits = list(number_str)  
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing  

    return spaced_str 

def custom_spacing_ssn(number_str, spaces=[2, 3, 2, 2, 2, 3, 2, 2]):  
    """  
    8space, 9 digits
    Add custom spaces between digits based on the specified space list.  
    """  
    digits = list(number_str)  
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing  

    return spaced_str 

def custom_spacing_Anumber(number_str, spaces=[2, 3, 2, 2, 2, 3, 2, 2]):  
    """  
    8space, 9 digits
    Add custom spaces between digits based on the specified space list.  
    """  
    digits = list(number_str)  
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing  

    return spaced_str 

def custom_spacing_SOCcode(number_str, spaces=[3, 6, 3, 2, 2]):  
    """  
    5space, 6 digits
    Add custom spaces between digits based on the specified space list.  
    """  
    #19-2222, remove -, get digits
    number_str = ''.join(re.findall(r'\d+', number_str)) 
    digits = list(number_str)  
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            # Use the spacing if available, otherwise use 1 space as default
            space_count = spaces[i] if i < len(spaces) else 1
            spaced_str += ' ' * space_count

    return spaced_str 

def process_df(df):
    # uscis account
    df["S9.2. USCIS Online Account Number (if any)"] = df["S9.2. USCIS Online Account Number (if any)"] \
        .fillna('') \
        .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
    df["S9.2. USCIS Online Account Number (if any)"] = df["S9.2. USCIS Online Account Number (if any)"] \
        .apply(lambda x: custom_spacing_uscis(x) if x.isdigit() else x)  
    
    # ssn
    df["S9.1. U.S. Social Security Number (SSN) (if any)"] = df["S9.1. U.S. Social Security Number (SSN) (if any)"] \
        .fillna('') \
        .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
    df["S9.1. U.S. Social Security Number (SSN) (if any)"] = df["S9.1. U.S. Social Security Number (SSN) (if any)"] \
        .apply(lambda x: custom_spacing_ssn(x) if x.isdigit() else x) 
    
    # a number
    df["S4.2. Alien Registration Number (A#)"] = df["S4.2. Alien Registration Number (A#)"] \
        .fillna('') \
        .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
    df["S4.2. Alien Registration Number (A#)"] = df["S4.2. Alien Registration Number (A#)"] \
        .apply(lambda x: custom_spacing_Anumber(x) if x.isdigit() else x) 
    
    # i94
    df["S7.3. Admission I-94 Record Number"] = df["S7.3. Admission I-94 Record Number"] \
        .fillna('') \
        .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
    df["S7.3. Admission I-94 Record Number"] = df["S7.3. Admission I-94 Record Number"] \
        .apply(lambda x: custom_spacing_i94(x) if x.isdigit() else x) 
    
    #soc
    df["S6.9. Job SOC Code"] = df["S6.9. Job SOC Code"] \
        .fillna('') \
        .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
    df["S6.9. Job SOC Code"] = df["S6.9. Job SOC Code"].apply(lambda x: custom_spacing_SOCcode(x)) 
    

    #date of birth
    df['S2.4. Date of Birth (mm/dd/yyyy)'] = pd.to_datetime(df['S2.4. Date of Birth (mm/dd/yyyy)'], errors='coerce') \
    .dt.strftime('%m/%d/%Y')
    #date of last arrival
    df['S7.1. Date of Last Arrival (mm/dd/yyyy)'] = pd.to_datetime(df['S7.1. Date of Last Arrival (mm/dd/yyyy)'], errors='coerce') \
    .dt.strftime('%m/%d/%Y')
    # passport 
    df['S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)'] = pd.to_datetime(df['S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)'], errors='coerce') \
    .dt.strftime('%m/%d/%Y')
    
    #start
    df["S6.14. Job Start Date"] = pd.to_datetime(df["S6.14. Job Start Date"], errors='coerce') \
    .dt.strftime('%m/%Y')

    # job description
    df["S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"] = \
        df["S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"].apply(lambda x: '\n'.join(wrap(x, 30)))

    return df


def process_form(form_name, df, email_filter=None):
    """Processes a single form for all rows in the DataFrame."""
    try:
        form_config = config.FORMS_CONFIG.get(form_name)
        if not form_config:
            logging.error(f"Form configuration for '{form_name}' not found.")
            return

        static_pdf_path = os.path.join(config.FOLDER_PATH, form_config["STATIC_PDF_PATH"])
        mapping_file_path = os.path.join(config.FOLDER_PATH, form_config["MAPPING_FILE_PATH"])
        output_folder_base = os.path.join(config.FOLDER_PATH, "filled")

        # Log paths for debugging
        logging.info(f"Processing form {form_name}")
        logging.info(f"Static PDF path: {static_pdf_path}")
        logging.info(f"Mapping file path: {mapping_file_path}")

        # Check if files exist
        if not os.path.exists(static_pdf_path):
            logging.error(f"Static PDF file not found: {static_pdf_path}")
            return
        if not os.path.exists(mapping_file_path):
            logging.error(f"Mapping file not found: {mapping_file_path}")
            return

        # Ensure the base output folder exists
        os.makedirs(output_folder_base, exist_ok=True)

        # Load the field mapping for the selected form
        try:
            with open(mapping_file_path, 'r', encoding='utf-8') as json_file:
                field_mapping = json.load(json_file)
        except Exception as e:
            logging.error(f"Error loading mapping file for form {form_name}: {str(e)}")
            return

        checkbox_mapping = None
        if form_name in ['140','9089']:
            mapping_checkbox_file_path = os.path.join(config.FOLDER_PATH, form_config["MAPPING_CHECKMARK_FILE_PATH"])
            if not os.path.exists(mapping_checkbox_file_path):
                logging.error(f"Checkbox mapping file not found: {mapping_checkbox_file_path}")
                return
            try:
                with open(mapping_checkbox_file_path, 'r', encoding='utf-8') as json_file:
                    checkbox_mapping = json.load(json_file)
            except Exception as e:
                logging.error(f"Error loading checkbox mapping file for form {form_name}: {str(e)}")
                return

        # Filter DataFrame by email if specified
        if email_filter:
            df = df[df["S2.5. Email Address"] == email_filter]
            if df.empty:
                logging.warning(f"No records found for email: {email_filter}")
                return

        # Process each row of the DataFrame
        for index, row in df.iterrows():
            try:
                email_address = row["S2.5. Email Address"]
                timestamp_str = datetime.now().strftime("%Y%m%d")

                # Create a unique subfolder for each email address under the filled folder
                email_folder = create_output_folder(output_folder_base, email_address)

                # Check if forms already exist in the folder and append timestamp if necessary
                existing_files = os.listdir(email_folder)
                if existing_files:
                    output_pdf_path = generate_output_file_path(email_folder, form_name, timestamp_str)
                else:
                    output_pdf_path = generate_output_file_path(email_folder, form_name)

                # Fill the PDF form with data from the current row
                data = row.to_dict()  # Convert row to dictionary
                fill_static_pdf(static_pdf_path, output_pdf_path, (field_mapping, checkbox_mapping), data)
            except Exception as e:
                logging.error(f"Error processing row {index} for form {form_name}: {str(e)}")

    except Exception as e:
        logging.error(f"Error in process_form for {form_name}: {str(e)}")

def main(fill_option=None, email_filter=None):
    """Main function to load data and fill PDF forms."""

    # Use argparse only when running in non-interactive mode (e.g., terminal)
    if fill_option is None:
        parser = argparse.ArgumentParser(description="Fill PDF forms based on Google Sheets data.")

        parser.add_argument("--fill", type=str,
                            default=config.DEFAULT_FILL,
                            help="Specify which forms to fill (e.g., 'all', '1145', '9089', '140'). Default is set in config.py.")
                            
        parser.add_argument("--email", type=str,
                            default=config.DEFAULT_EMAIL,
                            help="Specify email address to filter forms (e.g., 'vaneshieh@gmail.com'). If not specified, uses DEFAULT_EMAIL from config.py.")

        args = parser.parse_args()

        fill_option = args.fill  # Get --fill argument or default value
        email_filter = args.email  # Get --email argument if specified

    
    # Load data from Google Sheets
    df = get_google_sheet_data(config.GOOGLE_SHEET_ID, config.GOOGLE_CREDENTIALS_PATH)
    
    if df is None:
        logging.error("Failed to load data from Google Sheets. Exiting.")
        return
        
    df = process_df(df)

    if df is None:
        logging.error("Exiting due to data loading failure.")
        return

    # Determine which forms to process based on the --fill argument or default value in config.py
    if fill_option == "all":
        for form_name in config.FORMS_CONFIG.keys():
            process_form(form_name, df, email_filter)
    elif fill_option in config.FORMS_CONFIG.keys():
        process_form(fill_option, df, email_filter)
    else:
        logging.error(f"Invalid value for --fill: {fill_option}. Must be one of 'all', '1145', '9089', or '140'.")

if __name__ == "__main__":
    try:
        # Check if running in an interactive environment (like Colab or Jupyter Notebook)
        from IPython import get_ipython
        main(fill_option=config.DEFAULT_FILL, email_filter=config.DEFAULT_EMAIL)
    except ImportError:
        main()  # Run normally with argparse when executed from terminal
