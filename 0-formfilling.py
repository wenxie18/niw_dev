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
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import sys
from pathlib import Path

# Path to the Chinese font file
default_font_name = "helv"  # Built-in Helvetica font in PyMuPDF
chinese_font_name = "china-s"

# Ensure log directory exists
os.makedirs(config.LOG_PATH, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_PATH, 'formfilling.log')),
        logging.StreamHandler()
    ]
)

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

def insert_text_with_width(page, text, x0, y0, field_width, font_size=10, font_name="helv", pdf_path=None):
    """
    Insert text that spans the full width of a form field while preserving paragraph structure.
    
    Args:
        page: PDF page object
        text: Text to insert
        x0, y0: Starting position
        field_width: Width of the field to span
        font_size: Font size
        font_name: Font name
        pdf_path: PDF path for form-specific adjustments
    """
    # Form-specific line height adjustments
    if pdf_path and "140" in pdf_path:
        # 140 form has specific line spacing - use larger line height
        line_height = font_size * 1.8  # Adjusted line height for 140 form
        font_size = 10
    else:
        # Default line height for other forms, 9089
        line_height = font_size * 1.2  # Standard line height
        font_size = 10
    
    # Estimate characters per line based on field width
    # Approximate: 1 character ≈ 6-8 points at font_size 10
    # For wider fields, we can be more aggressive with character count
    chars_per_line = int(field_width / 6.5)  # More aggressive estimate for wider fields
    
    # Split text into paragraphs first (preserve blank lines and single newlines)
    # Handle different types of line breaks that might be in survey data
    paragraphs = []
    if '\n\n' in text:
        # Double newlines indicate paragraph breaks
        paragraphs = text.split('\n\n')
    elif '\n' in text:
        # Single newlines might indicate line breaks within paragraphs
        # Split by single newlines but treat as separate lines rather than paragraphs
        lines = text.split('\n')
        paragraphs = [lines]  # Treat all lines as one paragraph
    else:
        # No line breaks, treat as single paragraph
        paragraphs = [text]
    
    current_x = x0
    current_y = y0
    
    for paragraph in paragraphs:
        if isinstance(paragraph, list):
            # This is a list of lines (from single newline split)
            for line in paragraph:
                if line.strip():  # Skip empty lines
                    # Process this line word by word
                    words = line.strip().split()
                    current_line = ""
                    
                    for word in words:
                        test_line = current_line + " " + word if current_line else word
                        
                        if len(test_line) <= chars_per_line and current_line:
                            current_line = test_line
                        else:
                            if current_line:
                                page.insert_text((current_x, current_y), current_line, fontsize=font_size, fontname=font_name)
                                current_y += line_height
                            current_line = word
                    
                    # Insert the last line of this line
                    if current_line:
                        page.insert_text((current_x, current_y), current_line, fontsize=font_size, fontname=font_name)
                        current_y += line_height
        else:
            # This is a regular paragraph (from double newline split)
            if not paragraph.strip():  # Skip empty paragraphs
                current_y += line_height  # Add extra space for paragraph breaks
                continue
                
            # Split paragraph into words
            words = paragraph.strip().split()
            current_line = ""
            
            for word in words:
                # Test if adding this word would exceed the estimated line length
                test_line = current_line + " " + word if current_line else word
                
                if len(test_line) <= chars_per_line and current_line:
                    # Word fits on current line
                    current_line = test_line
                else:
                    # Word doesn't fit, insert current line and start new line
                    if current_line:
                        page.insert_text((current_x, current_y), current_line, fontsize=font_size, fontname=font_name)
                        current_y += line_height
                    
                    # Start new line with current word
                    current_line = word
            
            # Insert the last line of the paragraph
            if current_line:
                page.insert_text((current_x, current_y), current_line, fontsize=font_size, fontname=font_name)
                current_y += line_height
        
        # Add extra space between paragraphs (except after the last one)
        if paragraph != paragraphs[-1]:  # Not the last paragraph
            current_y += line_height * 0.5  # Half line height for paragraph spacing

def contains_chinese(text):
    """Check if the text contains any Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def fill_static_pdf(static_pdf_path, output_pdf_path, mapping, data, form_errors=None):
    """Fills a static PDF form with data from a dictionary."""
    # Initialize error tracking if not provided
    if form_errors is None:
        form_errors = {
            "failed_fields": [],
            "total_fields": 0,
            "successful_fields": 0,
            "failed_fields_count": 0
        }
    
    try:
        #logging.info(f"Opening PDF: {static_pdf_path}")
        doc = fitz.open(static_pdf_path)
        field_mapping, checkbox_mapping = mapping

        # Track field filling statistics
        total_fields = sum(1 for field_info in field_mapping.values() if field_info.get('fill', False))
        successful_fields = 0
        failed_fields = []

        # Log some basic info
        logging.info(f"Number of pages in PDF: {len(doc)}")
        logging.info(f"Number of fields to fill: {total_fields}")
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
                    value = None  # Replace NaN with None

                # Only process fields that should be filled
                if fill and value is not None and str(value).strip():
                    # Adjust font size if the text contains Chinese characters
                    if contains_chinese(str(value)):
                        font_size = 8
                        font_name = "helv"
                    else:
                        font_size = 10
                        font_name = "helv"

                    if page_index >= len(doc):
                        error_info = {
                            "field_name": field_name,
                            "key": key,
                            "value": str(value),
                            "reason": f"Invalid page index {page_index} for field. PDF has {len(doc)} pages.",
                            "page_index": page_index,
                            "position": [x0, y0],
                            "timestamp": datetime.now().isoformat()
                        }
                        failed_fields.append(error_info)
                        logging.error(f"Invalid page index {page_index} for field {field_name}. PDF has {len(doc)} pages.")
                        continue
                    
                    page = doc[page_index]
                    
                    # Check if this is a wide text field that should span the full width
                    if "Job Duties" in key or "job duties" in key.lower():
                        # Set different field widths for different forms
                        # 9089 form fields can use more width (650 points)
                        # 140 form fields are more constrained (300 points)
                        if "9089" in static_pdf_path:
                            field_width = 660  # 9089 form - use more width
                        else:
                            field_width = 330  # 140 form - more constrained
                        
                        insert_text_with_width(page, str(value), x0, y0, field_width, font_size, font_name, static_pdf_path)
                    else:
                        # Regular text insertion for normal fields
                        page.insert_text((x0, y0), str(value), fontsize=font_size, fontname=font_name)
                 
                    # Print debug info for first page (page 0)
                    #if page_index == 0:
                    #    print(f"PAGE 0: {field_name} | Key: {key} | Value: '{value}' | Pos: ({x0:.1f}, {y0:.1f})")
                    
                    successful_fields += 1
                    
                elif fill and (value is None or not str(value).strip()):
                    # Field should be filled but has no value
                    error_info = {
                        "field_name": field_name,
                        "key": key,
                        "value": str(value) if value is not None else "None",
                        "reason": "Field marked for filling but has no value or empty value",
                        "page_index": page_index,
                        "position": [x0, y0],
                        "timestamp": datetime.now().isoformat()
                    }
                    failed_fields.append(error_info)
                    logging.warning(f"Field {field_name} (key: {key}) marked for filling but has no value")
                    
            except Exception as e:
                error_info = {
                    "field_name": field_name,
                    "key": key if 'key' in locals() else "Unknown",
                    "value": str(value) if 'value' in locals() else "Unknown",
                    "reason": f"Exception during field filling: {str(e)}",
                    "page_index": page_index if 'page_index' in locals() else "Unknown",
                    "position": [x0, y0] if 'x0' in locals() and 'y0' in locals() else "Unknown",
                    "timestamp": datetime.now().isoformat()
                }
                failed_fields.append(error_info)
                logging.error(f"Error filling field {field_name}: {str(e)}")

        # Process checkboxes
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
                            error_info = {
                                "field_name": field_name,
                                "key": key,
                                "value": str(value) if value is not None else "None",
                                "reason": f"Invalid page index {page_index} for checkbox. PDF has {len(doc)} pages.",
                                "page_index": page_index,
                                "position": "Unknown",
                                "timestamp": datetime.now().isoformat()
                            }
                            failed_fields.append(error_info)
                            logging.error(f"Invalid page index {page_index} for checkbox {field_name}. PDF has {len(doc)} pages.")
                            continue
                        page = doc[page_index]
                        page.insert_image(rect, filename=config.CHECKMARK_PATH)  # Use full path from config 
                except Exception as e:
                    # Get page info for better debugging
                    page_info = f"page {page_index}" if 'page_index' in locals() else "unknown page"
                    error_info = {
                        "field_name": field_name,
                        "key": key if 'key' in locals() else "Unknown",
                        "value": str(value) if 'value' in locals() else "Unknown",
                        "reason": f"Exception during checkbox filling: {str(e)}",
                        "page_index": page_index if 'page_index' in locals() else "Unknown",
                        "position": "Unknown",
                        "timestamp": datetime.now().isoformat()
                    }
                    failed_fields.append(error_info)
                    logging.error(f"Error filling checkbox {field_name} on {page_info}: {str(e)}, key: {key}, value: {value}")

        #logging.info(f"Saving filled PDF to: {output_pdf_path}")
        doc.save(output_pdf_path)
        doc.close()
        logging.info(f"Filled form saved as {output_pdf_path}")
        #print(f"Filled form saved as {output_pdf_path}")
        
        # Return error tracking information
        return {
            "total_fields": total_fields,
            "successful_fields": successful_fields,
            "failed_fields_count": len(failed_fields),
            "failed_fields": failed_fields
        }
        
    except Exception as e:
        logging.error(f"Failed to fill static PDF: {str(e)}")
        if 'doc' in locals():
            doc.close()
        
        # Return error information even if PDF filling failed
        return {
            "total_fields": total_fields if 'total_fields' in locals() else 0,
            "successful_fields": successful_fields if 'successful_fields' in locals() else 0,
            "failed_fields_count": len(failed_fields) if 'failed_fields' in locals() else 0,
            "failed_fields": failed_fields if 'failed_fields' in locals() else [],
            "pdf_filling_error": str(e)
        }

def create_output_folder(base_folder, email_address):
    """Creates a unique folder for each email address under the base folder."""
    email_folder = os.path.join(base_folder, email_address)

    if not os.path.exists(email_folder):
        os.makedirs(email_folder)
        logging.info(f"Created folder: {email_folder}")
    #else:
    #    logging.info(f"Folder already exists: {email_folder}")

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

def custom_spacing_i94(number_str, spaces=[3, 4, 3, 3, 3, 3, 4, 3, 3, 3]):  
    """  
    Handle alphanumeric I-94 numbers, treat all characters as individual positions
    I-94 numbers have exactly 11 characters with 10 spaces between them
    Letters like A, 4, A, 3 are treated as individual characters for spacing
    """  
    #print(f"I94 DEBUG: Input number_str: '{number_str}' (type: {type(number_str)})")
    
    # Treat the entire string as individual characters (digits + letters)
    all_chars = list(number_str)
    #print(f"I94 DEBUG: All characters: {all_chars} (length: {len(all_chars)})")
    #print(f"I94 DEBUG: Spaces list: {spaces} (length: {len(spaces)})")
    
    spaced_str = ''  

    for i, char in enumerate(all_chars):  
        #print(f"I94 DEBUG: Processing character {i}: '{char}'")
        spaced_str += char  
        if i < len(all_chars) - 1:  # Avoid adding space at the end  
            # Use spaces[i] if available, otherwise use default spacing of 2
            space_count = spaces[i] # if i < len(spaces) else 2
            #print(f"I94 DEBUG: Adding {space_count} spaces after character {i}")
            spaced_str += ' ' * space_count

    #print(f"I94 DEBUG: Final result: '{spaced_str}'")
    return spaced_str 

def custom_spacing_ssn(number_str, spaces=[3, 4, 3, 3, 3, 3, 3, 3]):  
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

def custom_spacing_Anumber(number_str, spaces=[2, 4, 3, 3, 3, 4, 3, 4]):  
    """  
    8space, 9 digits
    Normalize input (remove dashes), then add custom spaces between digits.
    Must be exactly 9 digits after normalization.
    """  
    #print(f"ANUMBER DEBUG: Input number_str: '{number_str}' (type: {type(number_str)})")
    
    # Handle missing/NaN values
    if number_str is None or pd.isna(number_str) or str(number_str).strip() == '':
        raise ValueError(f"A-Number is missing or empty. Input: '{number_str}'")
    
    # Convert to string and handle edge cases
    number_str = str(number_str).strip()
    if number_str == '' or number_str == 'nan' or number_str == 'None':
        raise ValueError(f"A-Number is empty or invalid. Input: '{number_str}'")
    
    # Normalize: remove dashes and extract only digits
    digits_only = ''.join(re.findall(r'\d+', number_str))
    #print(f"ANUMBER DEBUG: After normalization: '{digits_only}' (length: {len(digits_only)})")
    
    # Validate: must be exactly 9 digits
    if len(digits_only) != 9:
        raise ValueError(f"A-Number must be exactly 9 digits after normalization. Got: '{digits_only}' (length: {len(digits_only)}) from input '{number_str}'. Expected format: 9 digits (e.g., 123456789 or 123-456-789)")
    
    # Apply spacing to the 9 digits using the 8 predefined spaces
    digits = list(digits_only)
    #print(f"ANUMBER DEBUG: Digits list: {digits} (length: {len(digits)})")
    #print(f"ANUMBER DEBUG: Spaces list: {spaces} (length: {len(spaces)})")
    
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        #print(f"ANUMBER DEBUG: Processing digit {i}: '{digit}'")
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing (always safe since we have exactly 9 digits)
            #print(f"ANUMBER DEBUG: Adding {spaces[i]} spaces after digit {i}")

    #print(f"ANUMBER DEBUG: Final result: '{spaced_str}'")
    return spaced_str 

def custom_spacing_SOCcode(number_str, spaces=[3, 8, 4, 3, 3]):  
    """  
    SOC codes must be exactly 6 digits for 140 form
    Normalize input to 6 digits and add custom spaces between digits.
    Raises ValueError if normalization fails.
    """  
    # Handle missing/NaN values
    if number_str is None or pd.isna(number_str) or str(number_str).strip() == '':
        raise ValueError(f"SOC code is missing or empty. Input: '{number_str}'")
    
    # Convert to string and handle edge cases
    number_str = str(number_str).strip()
    if number_str == '' or number_str == 'nan' or number_str == 'None':
        raise ValueError(f"SOC code is empty or invalid. Input: '{number_str}'")
    
    #19-2222, remove -, get digits
    #print(f"DEBUG: Input number_str: '{number_str}' (type: {type(number_str)})")
    number_str = ''.join(re.findall(r'\d+', number_str)) 
    #print(f"DEBUG: After regex: '{number_str}' (length: {len(number_str)})")
    
    # Validate that we have digits
    if not number_str:
        raise ValueError(f"Invalid SOC code: '{number_str}' - no digits found after removing non-digits")
    
    # Normalize to exactly 6 digits for 140 form
    if len(number_str) > 6:
        # Take first 6 digits (most significant)
        number_str = number_str[:6]
        #print(f"DEBUG: Normalized to 6 digits: '{number_str}'")
    elif len(number_str) < 6:
        # Pad with zeros if less than 6 digits
        number_str = number_str.zfill(6)
        #print(f"DEBUG: Padded to 6 digits: '{number_str}'")
    
    # Final validation - ensure we have exactly 6 digits
    if len(number_str) != 6:
        raise ValueError(f"Failed to normalize SOC code to 6 digits: '{number_str}' (length: {len(number_str)})")
    
    digits = list(number_str)  
    #print(f"DEBUG: Final digits list: {digits} (length: {len(digits)})")
    #print(f"DEBUG: Spaces list: {spaces} (length: {len(spaces)})")
    
    spaced_str = ''  

    for i, digit in enumerate(digits):  
        #print(f"DEBUG: Processing digit {i}: '{digit}'")
        spaced_str += digit  
        if i < len(digits) - 1:  # Avoid adding space at the end  
            spaced_str += ' ' * spaces[i]  # Use the predefined spacing  
    #print(f"DEBUG: Final result: '{spaced_str}'")
    return spaced_str 

def process_df(df):
    """Process DataFrame with error handling for each field transformation."""
    processing_errors = []
    
    try:
        # uscis account
        df["S9.2. USCIS Online Account Number (if any)"] = df["S9.2. USCIS Online Account Number (if any)"] \
            .fillna('') \
            .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
        df["S9.2. USCIS Online Account Number (if any)"] = df["S9.2. USCIS Online Account Number (if any)"] \
            .apply(lambda x: custom_spacing_uscis(x))  
    except Exception as e:
        error_msg = f"Error processing USCIS Online Account Number: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S9.2. USCIS Online Account Number (if any)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S9.2. USCIS Online Account Number (if any)"] = ''
    
    try:
        # ssn
        df["S9.1. U.S. Social Security Number (SSN) (if any)"] = df["S9.1. U.S. Social Security Number (SSN) (if any)"] \
            .fillna('') \
            .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
        df["S9.1. U.S. Social Security Number (SSN) (if any)"] = df["S9.1. U.S. Social Security Number (SSN) (if any)"] \
            .apply(lambda x: custom_spacing_ssn(x)) 
    except Exception as e:
        error_msg = f"Error processing SSN: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S9.1. U.S. Social Security Number (SSN) (if any)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S9.1. U.S. Social Security Number (SSN) (if any)"] = ''
    
    try:
        # a number
        df["S4.2. Alien Registration Number (A#)"] = df["S4.2. Alien Registration Number (A#)"] \
            .fillna('') \
            .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
        df["S4.2. Alien Registration Number (A#)"] = df["S4.2. Alien Registration Number (A#)"] \
            .apply(lambda x: custom_spacing_Anumber(x)) 
    except Exception as e:
        error_msg = f"Error processing A-Number: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S4.2. Alien Registration Number (A#)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S4.2. Alien Registration Number (A#)"] = ''
    
    try:
        # i94
        df["S7.3. Admission I-94 Record Number"] = df["S7.3. Admission I-94 Record Number"] \
            .fillna('') \
            .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
        df["S7.3. Admission I-94 Record Number"] = df["S7.3. Admission I-94 Record Number"] \
            .apply(lambda x: custom_spacing_i94(x))  # Process all I-94 numbers (alphanumeric),  i94 number could have letters such as A, 4, A, 3
    except Exception as e:
        error_msg = f"Error processing I-94 Number: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S7.3. Admission I-94 Record Number",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S7.3. Admission I-94 Record Number"] = ''
    
    try:
        #soc
        df["S6.9. Job SOC Code"] = df["S6.9. Job SOC Code"] \
            .fillna('') \
            .apply(lambda x: str(int(x)) if isinstance(x, (float, int)) and not pd.isna(x) else str(x))  # Remove .0 if it's a float
        df["S6.9. Job SOC Code"] = df["S6.9. Job SOC Code"].apply(lambda x: custom_spacing_SOCcode(x)) 
    except Exception as e:
        error_msg = f"Error processing SOC Code: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S6.9. Job SOC Code",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S6.9. Job SOC Code"] = ''

    try:
        #date of birth
        df['S2.4. Date of Birth (mm/dd/yyyy)'] = pd.to_datetime(df['S2.4. Date of Birth (mm/dd/yyyy)'], errors='coerce') \
        .dt.strftime('%m/%d/%Y')
    except Exception as e:
        error_msg = f"Error processing Date of Birth: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S2.4. Date of Birth (mm/dd/yyyy)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df['S2.4. Date of Birth (mm/dd/yyyy)'] = ''
    
    try:
        #date of last arrival
        df['S7.1. Date of Last Arrival (mm/dd/yyyy)'] = pd.to_datetime(df['S7.1. Date of Last Arrival (mm/dd/yyyy)'], errors='coerce') \
        .dt.strftime('%m/%d/%Y')
    except Exception as e:
        error_msg = f"Error processing Date of Last Arrival: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S7.1. Date of Last Arrival (mm/dd/yyyy)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df['S7.1. Date of Last Arrival (mm/dd/yyyy)'] = ''
    
    try:
        # passport 
        df['S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)'] = pd.to_datetime(df['S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)'], errors='coerce') \
        .dt.strftime('%m/%d/%Y')
    except Exception as e:
        error_msg = f"Error processing Passport Expiration Date: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df['S7.6. Expiration Date for Passport or Travel Document (mm/dd/yyyy)'] = ''
    
    try:
        #start
        df["S6.14. Job Start Date"] = pd.to_datetime(df["S6.14. Job Start Date"], errors='coerce') \
        .dt.strftime('%m/%Y')
    except Exception as e:
        error_msg = f"Error processing Job Start Date: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S6.14. Job Start Date",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S6.14. Job Start Date"] = ''

    try:
        # job description - preserve original paragraph structure, don't use textwrap
        # df["S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"] = \
        #     df["S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"].apply(lambda x: '\n'.join(wrap(x, 80)))  # Increased from 30 to 80 characters
        pass  # Keep original text structure
    except Exception as e:
        error_msg = f"Error processing Job Duties: {str(e)}"
        logging.error(error_msg)
        processing_errors.append({
            "field": "S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        # Set to empty string to continue processing
        df["S6.24. Job Duties: Specify details of the job (work tasks performed, use of tools/equipment, supervision, etc.) (up to 3,500 characters)"] = ''

    # Log summary of processing errors
    if processing_errors:
        logging.warning(f"DataFrame processing completed with {len(processing_errors)} errors. Check logs for details.")
    
    return df, processing_errors


def process_form(form_name, df, email_filter=None):
    """Processes a single form for all rows in the DataFrame."""
    # Initialize error tracking for this form
    form_errors = {
        "form_name": form_name,
        "timestamp": datetime.now().isoformat(),
        "failed_fields": [],
        "total_fields": 0,
        "successful_fields": 0,
        "failed_fields_count": 0
    }
    
    try:
        form_config = config.FORMS_CONFIG.get(form_name)
        if not form_config:
            logging.error(f"Form configuration for '{form_name}' not found.")
            return

        static_pdf_path = form_config["STATIC_PDF_PATH"]
        mapping_file_path = form_config["MAPPING_FILE_PATH"]
        output_folder_base = config.OUTPUT_BASE_FOLDER

        # Log paths for debugging
        logging.info(f"Processing form {form_name}")
        #logging.info(f"Static PDF path: {static_pdf_path}")
        #logging.info(f"Mapping file path: {mapping_file_path}")

        # Check if files exist
        if not os.path.exists(static_pdf_path):
            logging.error(f"Static PDF file not found: {static_pdf_path}")
            return
        if not os.path.exists(mapping_file_path):
            logging.error(f"Mapping file path: {mapping_file_path}")
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
            mapping_checkbox_file_path = form_config["MAPPING_CHECKMARK_FILE_PATH"]
            if not os.path.exists(mapping_checkbox_file_path):
                logging.error(f"Checkbox mapping file not found: {mapping_checkbox_file_path}")
                return
            try:
                with open(mapping_checkbox_file_path, 'r', encoding='utf-8') as json_file:
                    checkbox_mapping = json.load(json_file)
            except Exception as e:
                logging.error(f"Error loading checkbox mapping file for form {form_name}: {str(e)}")
                return

        # Email filtering is now handled in main() function before calling process_form
        # The DataFrame passed here is already filtered for the specific user
        
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
                fill_result = fill_static_pdf(static_pdf_path, output_pdf_path, (field_mapping, checkbox_mapping), data, form_errors)
                
                # Update form_errors with the result
                if fill_result:
                    form_errors.update(fill_result)
                
            except Exception as e:
                logging.error(f"Error processing row {index} for form {form_name}: {str(e)}")

    except Exception as e:
        logging.error(f"Error in process_form for {form_name}: {str(e)}")
    
    # Save error report to JSON file
    try:
        # Save error report under the user's email folder instead of base folder
        if 'email_folder' in locals():
            error_report_path = os.path.join(email_folder, f"{form_name}_error_report.json")
        else:
            # Fallback to base folder if email_folder not available
            error_report_path = os.path.join(output_folder_base, f"{form_name}_error_report.json")
        
        with open(error_report_path, 'w', encoding='utf-8') as f:
            json.dump(form_errors, f, indent=2, ensure_ascii=False)
        logging.info(f"Error report saved to: {error_report_path}")
    except Exception as e:
        logging.error(f"Failed to save error report: {str(e)}")
    
    return form_errors

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
    df = get_google_sheet_data(config.GOOGLE_SHEET_ID, config.GOOGLE_SHEETS_CREDENTIALS_PATH)
    
    if df is None:
        logging.error("Failed to load data from Google Sheets. Exiting.")
        return
    
    # Apply email filtering BEFORE processing DataFrame
    if email_filter:
        user_rows = df[df["S2.5. Email Address"] == email_filter]
        if user_rows.empty:
            logging.error(f"No records found for email: {email_filter}")
            return
        
        # If multiple rows exist for the same email, get the most recent one based on timestamp
        if len(user_rows) > 1:
            logging.info(f"Found {len(user_rows)} responses for {email_filter}, using the most recent one")
            # Convert timestamp to datetime for proper sorting
            user_rows = user_rows.copy()
            user_rows['Timestamp'] = pd.to_datetime(user_rows['Timestamp'], errors='coerce')
            # Sort by timestamp descending (most recent first) and take the first row
            user_rows = user_rows.sort_values('Timestamp', ascending=False)
            df = user_rows.iloc[[0]]  # Keep as DataFrame with single row
        else:
            df = user_rows
        
        logging.info(f"Processing forms for user: {email_filter}")
        logging.info(f"User data row count: {len(df)}")
    
    # Now process the filtered DataFrame (single user only)
    df, processing_errors = process_df(df)

    if df is None:
        logging.error("Exiting due to data loading failure.")
        return

    # Track overall statistics
    overall_stats = {
        "user_email": email_filter,  # Track which user this summary is for
        "total_forms_processed": 0,
        "total_fields_attempted": 0,
        "total_fields_successful": 0,
        "total_fields_failed": 0,
        "data_processing_errors": processing_errors,  # Include DataFrame processing errors
        "form_results": []
    }

    # Log DataFrame processing errors if any
    if processing_errors:
        logging.warning(f"DataFrame processing completed with {len(processing_errors)} errors:")
        for error in processing_errors:
            logging.warning(f"  - {error['field']}: {error['error']}")
        print(f"\n⚠️  {len(processing_errors)} data processing errors occurred during DataFrame preparation.")
        print("These fields will be set to empty strings in the forms.")

    # Determine which forms to process based on the --fill argument or default value in config.py
    if fill_option == "all":
        for form_name in config.FORMS_CONFIG.keys():
            form_result = process_form(form_name, df, email_filter)
            if form_result:
                overall_stats["form_results"].append(form_result)
                overall_stats["total_forms_processed"] += 1
                overall_stats["total_fields_attempted"] += form_result.get("total_fields", 0)
                overall_stats["total_fields_successful"] += form_result.get("successful_fields", 0)
                overall_stats["total_fields_failed"] += form_result.get("failed_fields_count", 0)
    elif fill_option in config.FORMS_CONFIG.keys():
        form_result = process_form(fill_option, df, email_filter)
        if form_result:
            overall_stats["form_results"].append(form_result)
            overall_stats["total_forms_processed"] += 1
            overall_stats["total_fields_attempted"] += form_result.get("total_fields", 0)
            overall_stats["total_fields_successful"] += form_result.get("successful_fields", 0)
            overall_stats["total_fields_failed"] += form_result.get("failed_fields_count", 0)
    else:
        logging.error(f"Invalid value for --fill: {fill_option}. Must be one of 'all', '1145', '9089', or '140'.")
        return

    # Display summary statistics
    print("\n" + "="*60)
    if email_filter:
        print(f"FORM FILLING SUMMARY FOR USER: {email_filter}")
    else:
        print("FORM FILLING SUMMARY")
    print("="*60)
    print(f"Total forms processed: {overall_stats['total_forms_processed']}")
    print(f"Total fields attempted: {overall_stats['total_fields_attempted']}")
    print(f"Total fields successful: {overall_stats['total_fields_successful']}")
    print(f"Total fields failed: {overall_stats['total_fields_failed']}")
    
    if overall_stats['total_fields_attempted'] > 0:
        success_rate = (overall_stats['total_fields_successful'] / overall_stats['total_fields_attempted']) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    print("\nForm-by-form breakdown:")
    for form_result in overall_stats["form_results"]:
        form_name = form_result.get("form_name", "Unknown")
        total = form_result.get("total_fields", 0)
        successful = form_result.get("successful_fields", 0)
        failed = form_result.get("failed_fields_count", 0)
        
        if total > 0:
            form_success_rate = (successful / total) * 100
            print(f"  {form_name}: {successful}/{total} fields filled ({form_success_rate:.1f}% success)")
        else:
            print(f"  {form_name}: No fields to fill")
    
    if overall_stats['total_fields_failed'] > 0:
        print(f"\n⚠️  {overall_stats['total_fields_failed']} fields failed to fill.")
        print("Check the individual error report JSON files for details.")
    
    # Display data processing errors if any
    if processing_errors:
        print(f"\n⚠️  {len(processing_errors)} data processing errors occurred:")
        for error in processing_errors:
            print(f"  - {error['field']}: {error['error']}")
        print("These fields were set to empty strings and will appear blank in the forms.")
    
    print("="*60)
    
    # Save overall summary to JSON
    try:
        if email_filter:
            # Save summary under the user's email folder
            email_folder_path = os.path.join(config.OUTPUT_BASE_FOLDER, email_filter)
            summary_filename = f"form_filling_summary.json"
            summary_path = os.path.join(email_folder_path, summary_filename)
        else:
            # Fallback to base folder if no email filter
            summary_filename = f"form_filling_summary.json"
            summary_path = os.path.join(config.OUTPUT_BASE_FOLDER, summary_filename)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(overall_stats, f, indent=2, ensure_ascii=False)
        print(f"Overall summary saved to: {summary_path}")
    except Exception as e:
        logging.error(f"Failed to save summary: {str(e)}")

if __name__ == "__main__":
    try:
        # Check if running in an interactive environment (like Colab or Jupyter Notebook)
        from IPython import get_ipython
        ipython = get_ipython()
        if ipython is not None:
            # Running in interactive environment
            main(fill_option=config.DEFAULT_FILL, email_filter=config.DEFAULT_EMAIL)
        else:
            # Running from terminal
            main()
    except ImportError:
        # No IPython available, running from terminal
        main()
