# NIW Automation Tools

This project provides various automation tools for NIW (National Interest Waiver) immigration processes.

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [Form Filling Automation](#1-form-filling-automation)
3. [Citation Analysis and Email Scraping](#2-citation-analysis-and-email-scraping)
4. [Survey Processing](#3-survey-processing)
5. [PDF Processing Tools](#4-pdf-processing-tools)
6. [Other Tools](#5-other-tools)

## Environment Setup

This project must be run in the conda base environment. To set up:

1. Make sure you have conda installed
2. Activate the base environment:
   ```bash
   conda activate base
   ```
3. Verify you're in the correct environment:
   ```bash
   which python3  # Should show /opt/homebrew/Caskroom/miniforge/base/bin/python3
   ```

## Project Structure

```
niw/
├── data/                      # All data files and outputs
│   ├── filled/               # Filled forms and outputs
│   │   └── [email]/         # Per-user output directory
│   ├── cache/               # Cached data for faster reruns
│   ├── log/                 # Log files
│   ├── credentials/         # API credentials
│   ├── forms/              # Form templates and mappings
│   │   └── mapping/       # Form field mappings
│   ├── university_rank.xlsx  # University ranking data
│   ├── survey.xlsx          # Survey data
│   ├── survey_template.json  # Survey template (auto-generated)
│   └── survey_questions_mapping_v1.json  # Survey question mappings
├── scripts/                  # Utility scripts
└── notebooks/               # Jupyter notebooks
```

## 1. Form Filling Automation

This tool automates the filling of immigration forms (I-140, ETA-9089, and G-1145) using data from Google Sheets.

### 1.1 Prerequisites

- Conda base environment activated (`conda activate base`)
- Python 3.9 or higher (path: `/opt/homebrew/Caskroom/miniforge/base/bin/python3`)
- Google Sheets API credentials
- Required Python packages (install using `pip install -r requirements.txt`)

### 1.2 Configuration

Before running the script, ensure you have:

1. A Google Sheet with the correct column headers matching the form fields
2. Google Sheets API credentials saved in the `data/credentials` folder
3. Updated `config.py` with:
   - Your Google Sheet ID
   - Path to your credentials file
   - Default email address to process

### 1.3 Usage

#### 1.3.1 Basic Usage

To fill forms for the default email address (configured in `config.py`):

```bash
python3 0-formfilling.py
```

This will:
1. Read data from the configured Google Sheet
2. Process the data for the default email address
3. Generate filled PDF forms in the `data/filled/[email]` directory

#### 1.3.2 Command Line Options

You can customize the behavior using command line arguments:

```bash
python3 0-formfilling.py --fill [form_type] --email [email_address]
```

Where:
- `--fill`: Specify which forms to fill (options: 'all', '1145', '9089', '140')
- `--email`: Specify which email address to process

Examples:
```bash
# Fill all forms for a specific email
python3 0-formfilling.py --email example@email.com

# Fill only I-140 form for the default email
python3 0-formfilling.py --fill 140

# Fill specific forms for a specific email
python3 0-formfilling.py --fill 140,9089 --email example@email.com
```

### 1.4 Output

Filled forms are saved in the following structure:
```
data/
  └── filled/
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
4. Check the logs in `data/log` for specific error messages

## 2. Citation Analysis and Email Scraping

This tool provides comprehensive citation analysis and visualization capabilities for Google Scholar profiles.

### 2.1 Features

- Generates citation map showing the geographic distribution of citing authors
- Implements caching to speed up repeated runs
- Provides proxy support to avoid rate limiting
- Generates detailed CSV reports with email, school rank, and journal/conference name

### 2.2 Prerequisites

- Conda base environment activated (`conda activate base`)
- Python 3.9 or higher (path: `/opt/homebrew/Caskroom/miniforge/base/bin/python3`)
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
python3 scripts/citation_map/citation_map.py
```

This will:
1. Fetch all publications from your Google Scholar profile
2. Identify citing authors and their affiliations
3. Generate a citation map and CSV with citation information
4. Save results in the `data/filled/[email]` directory

#### 2.3.2 Advanced Options

The script supports several configuration options:

```bash
python3 scripts/citation_map/citation_map.py --scholar_id [ID] --output_path [path] --csv_output_path [path] --parse_csv [True/False] --cache_folder [path] --affiliation_conservative [True/False] --num_processes [N] --use_proxy [True/False] --pin_colorful [True/False]
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
data/
  └── filled/
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
   - Check the logs in `data/log` for specific error messages

### 2.7 Performance Tips

1. Use caching to speed up repeated runs
2. Enable parallel processing with `--num_processes`
3. Use proxy support if experiencing rate limits
4. For large datasets, consider using conservative affiliation detection

## 3. Survey Processing

This tool processes survey responses from Google Sheets and generates structured JSON data for NIW petitions.

### 3.1 Features

- Reads survey responses from Google Sheets
- Maps survey questions to template JSON structure
- Generates structured data for petition letters
- Supports template caching for efficiency

### 3.2 Prerequisites

- Conda base environment activated (`conda activate base`)
- Python 3.9 or higher
- Google Sheets API credentials
- Survey Google Sheet shared with service account

### 3.3 Usage

#### 3.3.1 Basic Usage

To process survey responses:

```bash
python3 4.2-process_survey.py
```

This will:
1. Create or load the survey template from `data/survey_template.json`
2. Read survey data from the configured Google Sheet
3. Find the user's row based on email address
4. Map survey answers to the template structure
5. Save the filled template as `data/filled/[email]/survey_answers.json`

### 3.4 Configuration

Before running the script, ensure you have:
1. Survey Google Sheet shared with service account email
2. Correct email address configured in `config.py`
3. Survey questions mapping file in `data/survey_questions_mapping_v1.json`

### 3.5 Output

The tool generates:
```
data/
  ├── survey_template.json              # Template with null values (auto-generated)
  └── filled/
      └── [email_address]/
          └── survey_answers.json       # Filled survey responses
```

## 4. PDF Processing Tools

### 4.1 PDF Download and Processing

#### 4.1.1 Download PDFs from Google Scholar

```bash
python3 1.2-download_pdfs.py
python3 1.3-download_pdfs_comprehensive.py
```

These scripts download PDFs of publications from Google Scholar profiles.

#### 4.1.2 Extract First Pages

```bash
python3 1.4-extract_first_pages.py
```

Extracts the first page of each PDF for quick review.

### 4.2 Email Ranking and Analysis

```bash
python3 2.1-email_rank.py
```

Analyzes citation data and ranks institutions based on university rankings.

### 4.3 Venue Analysis

```bash
python3 3.1-venue_analysis.py
python3 3.1-save_venue_info.py
```

Analyzes publication venues and generates structured data for petitions.

## 5. Other Tools

### 5.1 Survey Creation

```bash
python3 4.1-create_niw_survey.py
```

Creates Google Forms for collecting NIW petition information.

### 5.2 Citation Analysis

```bash
python3 1-citation.py
```

Basic citation analysis and mapping generation.

### 5.3 Reference Reading

```bash
python3 read_reference.py
```

Utility for reading and processing reference materials.

## Configuration

### Google Sheets Setup

1. **Form Data Sheet**: Used by `0-formfilling.py` (ID: `1MLlEwKiCd06FXLN1uk0v22JRXIugU2YXrgzzjmnoJI0`)
2. **Survey Sheet**: Used by `4.2-process_survey.py` (ID: `1MhIzhJjdYXWfGDFtzcH4gyanzn6TyTeeBolop0-P9EY`)

### Credentials

- **Google Sheets API**: `data/credentials/turboniw-8093004799d6.json`
- **Google Form API**: `data/credentials/credentials-google-form-api.json`

### Service Account Setup

Share both Google Sheets with: `sheets-api-service-account@turboniw.iam.gserviceaccount.com`

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure Google Sheets are shared with the service account
2. **Missing Dependencies**: Install required packages in conda base environment
3. **Path Issues**: Verify all paths in `config.py` are correct
4. **Log Files**: Check `data/log/` for detailed error messages

### Performance Optimization

1. Use caching for repeated operations
2. Enable parallel processing where available
3. Use proxy support for rate-limited APIs
4. Consider conservative mode for large datasets

## Contributing

Feel free to submit issues and enhancement requests! 

How to push code to github:
git status
git add .
git commit -m "notes"
git push