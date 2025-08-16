# NIW Automation Tools

This project provides various automation tools for NIW (National Interest Waiver) immigration processes.

## Table of Contents
1. [Form Filling Automation](#1-form-filling-automation)
2. [Citation Analysis and Email Scraping](#2-citation-analysis-and-email-scraping)
3. [Other Tools](#3-other-tools) (Coming Soon)

## 1. Form Filling Automation

This tool automates the filling of immigration forms (I-140, ETA-9089, and G-1145) using data from Google Sheets.

### 1.1 Prerequisites

- Python 3.9 or higher
- Google Sheets API credentials
- Required Python packages (install using `pip install -r requirements.txt`)

### 1.2 Configuration

Before running the script, ensure you have:

1. A Google Sheet with the correct column headers matching the form fields
2. Google Sheets API credentials saved in the `credentials` folder
3. Updated `config.py` with:
   - Your Google Sheet ID
   - Path to your credentials file
   - Default email address to process

### 1.3 Usage

#### 1.3.1 Basic Usage

To fill forms for the default email address (configured in `config.py`):

```bash
python 0-formfilling.py
```

This will:
1. Read data from the configured Google Sheet
2. Process the data for the default email address
3. Generate filled PDF forms in the `filled/[email]` directory

#### 1.3.2 Command Line Options

You can customize the behavior using command line arguments:

```bash
python 0-formfilling.py --fill [form_type] --email [email_address]
```

Where:
- `--fill`: Specify which forms to fill (options: 'all', '1145', '9089', '140')
- `--email`: Specify which email address to process

Examples:
```bash
# Fill all forms for a specific email
python 0-formfilling.py --email example@email.com

# Fill only I-140 form for the default email
python 0-formfilling.py --fill 140

# Fill specific forms for a specific email
python 0-formfilling.py --fill 140,9089 --email example@email.com
```

### 1.4 Output

Filled forms are saved in the following structure:
```
filled/
  └── [email_address]/
      ├── filled_1145.pdf
      ├── filled_9089.pdf
      └── filled_140.pdf
```

### 1.5 Supported Forms

The script supports filling the following forms:
1. I-140 (Immigrant Petition for Alien Worker)
2. ETA-9089 (Application for Permanent Employment Certification)
3. G-1145 (E-Notification of Application/Petition Acceptance)

### 1.6 Troubleshooting

If you encounter errors:
1. Check that your Google Sheet has all required columns
2. Verify your Google Sheets API credentials are valid
3. Ensure the email address exists in the Google Sheet data
4. Check the logs for specific error messages

## 2. Citation Analysis and Email Scraping

This tool provides comprehensive citation analysis and visualization capabilities for Google Scholar profiles.

### 2.1 Features

- Generates citation map showing the geographic distribution of citing authors
- Implements caching to speed up repeated runs
- Provides proxy support to avoid rate limiting
- Generates detailed CSV reports with email, school rank, and journal/conference name

### 2.2 Prerequisites

- Python 3.9 or higher
- Google Scholar profile ID
- Google Maps API key (for geocoding)
- Required Python packages (install using `pip install -r requirements.txt`):
  - scholarly
  - folium
  - geopy
  - pandas
  - pycountry
  - tqdm

### 2.3 Usage

#### 2.3.1 Basic Usage

To generate a citation map and analyze citations:

```bash
python scripts/citation_map/citation_map.py
```

This will:
1. Fetch all publications from your Google Scholar profile
2. Identify citing authors and their affiliations
3. Generate a citation map and CSV with citation information
4. Save results in the `filled/[email]` directory

#### 2.3.2 Advanced Options

The script supports several configuration options:

```bash
python scripts/citation_map/citation_map.py --scholar_id [ID] --output_path [path] --csv_output_path [path] --parse_csv [True/False] --cache_folder [path] --affiliation_conservative [True/False] --num_processes [N] --use_proxy [True/False] --pin_colorful [True/False]
```

Where:
- `--scholar_id`: Your Google Scholar ID
- `--output_path`: Path for the HTML map output
- `--csv_output_path`: Path for the CSV data output
- `--parse_csv`: Skip to map generation using existing CSV data
- `--cache_folder`: Directory for caching intermediate results
- `--affiliation_conservative`: Use conservative affiliation detection
- `--num_processes`: Number of parallel processes
- `--use_proxy`: Enable proxy support
- `--pin_colorful`: Use colorful pins on the map

### 2.4 Output

The tool generates several output files:
```
filled/
  └── [email_address]/
      ├── citation_map.html        # Interactive map of citing authors
      ├── citation_info.csv        # Raw citation data with affiliations
      └── cache/                   # Cached data for faster reruns
```

### 2.5 Configuration

Before running the script, ensure you have:
1. Updated `config.py` with:
   - Your Google Scholar ID
   - Google Maps API key for geocoding
2. Set up proxy configuration if needed (see Troubleshooting)

### 2.6 Troubleshooting

If you encounter issues:
1. Check that your Google Scholar profile is public
2. Verify your Google Maps API key is valid
3. If experiencing rate limits:
   - Enable proxy support with `--use_proxy`
   - Use caching with `--cache_folder`
4. For affiliation detection issues:
   - Try conservative mode with `--affiliation_conservative`
   - Check the generated CSV for accuracy
5. For debugging:
   - Use `save_author_ids_for_debugging()` and `save_citation_info_for_debugging()`
   - Check the logs for specific error messages

### 2.7 Performance Tips

1. Use caching to speed up repeated runs
2. Enable parallel processing with `--num_processes`
3. Use proxy support if experiencing rate limits
4. For large datasets, consider using conservative affiliation detection

## 3. Other Tools

More automation tools will be added in the future. Stay tuned!

## Contributing

Feel free to submit issues and enhancement requests! 