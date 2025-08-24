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
SCHOOLRANK_PATH = os.path.join(DATA_PATH, 'schoolrank/2025_QS_university_rank.xlsx')

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

# Survey Configuration
SURVEY_QUESTIONS_MAPPING_PATH = os.path.join(DATA_PATH, "survey_questions_mapping_v2.json")

# Rankings Configuration
RANKINGS_CSV_COLUMNS = ['rank', 'university_name', 'country']  # Default CSV columns
RANKINGS_DEFAULT_YEAR = '2025'  # Default ranking source to download
RANKINGS_ENABLED_SOURCES = ['THE', 'QS']  # Available ranking sources (ARWU handled by separate Selenium scraper)

# Country-Specific Rankings Configuration
COUNTRY_RANKINGS_ENABLED = ['US', 'China', 'UK', 'Australia']  # Available countries
COUNTRY_RANKINGS_CSV_COLUMNS = ['rank', 'university_name', 'state_province', 'country']  # Country rankings columns

# Country Rankings API Endpoints
COUNTRY_RANKINGS_ENDPOINTS = {
    'US': {
        '2024': {
            'url': 'https://www.usnews.com/best-colleges/rankings/national-universities',
            'type': 'web_scraping',
            'note': 'US News Best Colleges National Universities Rankings',
            'fallback_urls': [
                'https://www.usnews.com/best-colleges',
                'https://www.usnews.com/best-colleges/rankings',
                'https://www.usnews.com/best-colleges/rankings/national-universities',
                'https://www.usnews.com/best-colleges/rankings/liberal-arts-colleges',
                'https://www.usnews.com/best-colleges/rankings/regional-universities',
                'https://www.usnews.com/best-colleges/rankings/regional-colleges'
            ],
            'alternative_sources': [
                'https://www.forbes.com/lists/americas-top-colleges/',
                'https://www.wsj.com/rankings/college-rankings',
                'https://www.princetonreview.com/college-rankings',
                'https://www.niche.com/colleges/rankings/',
                'https://www.collegefactual.com/rankings/'
            ]
        }
    },
    'China': {
        '2025': {
            'type': 'selenium_scraping',
            'url': 'https://www.shanghairanking.com/rankings/bcur/2025',
            'note': 'Shanghai Ranking Best Chinese Universities Ranking (BCUR) - requires Selenium scraper'
        }
    },
    'UK': {
        '2024': {
            'type': 'web_scraping',
            'url': 'https://www.thecompleteuniversityguide.co.uk/league-tables/rankings',
            'note': 'Complete University Guide UK - requires web scraping implementation'
        }
    },
    'Australia': {
        '2024': {
            'type': 'web_scraping',
            'url': 'https://www.gooduniversitiesguide.com.au/rankings',
            'note': 'Good Universities Guide Australia - requires web scraping implementation'
        }
    }
}

# File Path Configuration
RANKINGS_BASE_PATH = os.path.join(DATA_PATH, "rankings")
RANKINGS_WORLD_PATH = os.path.join(RANKINGS_BASE_PATH, "world")
RANKINGS_COUNTRIES_PATH = os.path.join(RANKINGS_BASE_PATH, "countries")

# Ranking Source API Endpoints (update these when they change)
RANKINGS_API_ENDPOINTS = {
    'THE': {
        '2025': 'https://www.timeshighereducation.com/sites/default/files/the_data_rankings/world_university_rankings_2025_0__ba2fbd3409733a83fb62c3ee4219487c.json',
        # Add new years as they become available
        # Original website: https://www.timeshighereducation.com/world-university-rankings
    },
    'QS': {
        '2025': {
            'type': 'excel_download',
            'url': 'https://www.topuniversities.com/sites/default/files/2025-06/2025%20QS%20World%20University%20Rankings%202.2%20%28For%20qs.com%29.xlsx'
        },
        # Add new years as they become available
        # '2026': {
        #     'type': 'excel_download',
        #     'url': 'https://www.topuniversities.com/sites/default/files/2026-06/2026%20QS%20World%20University%20Rankings%20X.X%20%28For%20qs.com%29.xlsx'
        # },
        # Original website: https://www.topuniversities.com/world-university-rankings
    },
    'ARWU': {
        '2025': {
            'url': 'https://www.shanghairanking.com/rankings/arwu/2025',
            'type': 'selenium_scraping',
            'note': 'ShanghaiRanking Academic Ranking of World Universities - requires Selenium scraper'
        }
        # Original website: https://www.shanghairanking.com/rankings/arwu/2025
    }
}

# Default parameters (can be overridden via command-line arguments)
DEFAULT_FILL = 'all'  # Options: 'all', '1145', '9089', '140'
DEFAULT_EMAIL = 'zxiliang51@gmail.com' #'ziyuan1501040205@gmail.com'  #'ziyuan1501040205@gmail.com' Default email to process, set to None to process all emails
#'jacquelineliu1997@gmail.com'#