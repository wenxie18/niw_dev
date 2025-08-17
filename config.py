# config.py
# always use this python /opt/homebrew/Caskroom/miniforge/base/bin/python
import os

# General Configuration
# Use relative paths for portability
FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))  # Current script directory
DATA_PATH = os.path.join(FOLDER_PATH, 'data')

# Data-related paths
OUTPUT_BASE_FOLDER = os.path.join(DATA_PATH, 'filled')  # Base folder for all filled forms
CACHE_PATH = os.path.join(DATA_PATH, 'cache')
LOG_PATH = os.path.join(DATA_PATH, 'log')
CREDENTIALS_PATH = os.path.join(DATA_PATH, 'credentials')
FORMS_PATH = os.path.join(DATA_PATH, 'forms')
CHECKMARK_PATH = os.path.join(DATA_PATH, 'checkmark.png')

# Font settings
FONT_SIZE = 12
FONT_SIZE_LARGE = 12 # for chinese charater

# Google Sheets API Configuration
#stage 1 google sheet id
GOOGLE_SHEET_ID = '1yVoA6I4qkhzl_j-AP4wpvLhZX9mg9wSquGvYvnjCVqQ'#'1MLlEwKiCd06FXLN1uk0v22JRXIugU2YXrgzzjmnoJI0'
#stage 2 google sheet id
# GOOGLE_SCHOLAR_SHEET_ID = '1MhIzhJjdYXWfGDFtzcH4gyanzn6TyTeeBolop0-P9EY' #'1YXQ_kMOL-l7dERVB867suz7CE5YCAT1vZCEeoKgbqqU'
GOOGLE_SHEETS_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, "turboniw-8093004799d6.json")  # For Google Sheets API
GOOGLE_FORM_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, "credentials-google-form-api.json")  # For Google Form API

# Geocoding API Configuration
# To get a valid API key:
# 1. Go to Google Cloud Console (https://console.cloud.google.com/)
# 2. Create a project or select existing one
# 3. Enable the "Geocoding API"
# 4. Create credentials (API key) under "APIs & Services" > "Credentials"
# 5. Replace the key below with your new API key
GOOGLE_MAPS_API_KEY = 'AIzaSyDx4DZ734PQXD-_aoIUhPqrPsXioE_ZrlM'  # This key works as shown in the test

# SerpAPI Configuration
# To get a valid API key:
# 1. Go to https://serpapi.com/dashboard
# 2. Sign up and get your API key
# 3. Replace the key below with your API key
SERPAPI_KEY = '297e9f2f752895b4330978487115b604ce242fa820fd1a4c06b7f6228a6705ad'  # Replace with your actual SerpAPI key
SERPAPI_ENABLED = False  # Set to False to disable SerpAPI fallback

# Form Configuration
FORMS_CONFIG = {
    "1145": {
        "STATIC_PDF_PATH": os.path.join(FORMS_PATH, "g-1145-static.pdf"),
        "MAPPING_FILE_PATH": os.path.join(FORMS_PATH, "mapping/mapping1145_final.json")
    },
    "9089": {
        "STATIC_PDF_PATH": os.path.join(FORMS_PATH, "ETA-9089-Appendix-A-static.pdf"),
        "MAPPING_FILE_PATH": os.path.join(FORMS_PATH, "mapping/mapping9089_final.json"),
        "MAPPING_CHECKMARK_FILE_PATH": os.path.join(FORMS_PATH, "mapping/mapping9089_checkbox.json")
    },
    "140": {
        "STATIC_PDF_PATH": os.path.join(FORMS_PATH, "i-140-static.pdf"),
        "MAPPING_FILE_PATH": os.path.join(FORMS_PATH, "mapping/mapping140_final.json"),
        "MAPPING_CHECKMARK_FILE_PATH": os.path.join(FORMS_PATH, "mapping/mapping140_checkbox.json")
    }
}

# Default parameters (can be overridden via command-line arguments)
DEFAULT_FILL = 'all'  # Options: 'all', '1145', '9089', '140'
DEFAULT_EMAIL = 'zxiliang51@gmail.com' #'ziyuan1501040205@gmail.com'  #'ziyuan1501040205@gmail.com' Default email to process, set to None to process all emails
#'jacquelineliu1997@gmail.com'#