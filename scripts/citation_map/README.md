# Local Citation Map Package

This is a local version of the citation-map package with added Google Scholar links in the CSV output.

## Installation

1. Make sure you have Python 3.7+ installed
2. Install the required dependencies:
```bash
pip install bs4 folium geopy pandas pycountry requests scholarly tqdm
```

## Usage

1. Import the package in your Python script:
```python
from citation_map.citation_map import generate_citation_map
```

2. Generate the citation map:
```python
generate_citation_map(
    scholar_id='YOUR_GOOGLE_SCHOLAR_ID',
    output_path='citation_map.html',
    csv_output_path='citation_info.csv',
    parse_csv=False,
    affiliation_conservative=False,
    num_processes=16,
    use_proxy=False,
    pin_colorful=True,
    print_citing_affiliations=True
)
```

The CSV output will now include a 'google_scholar_link' column with direct links to the Google Scholar citations.

## Parameters

- `scholar_id`: Your Google Scholar ID
- `output_path`: Path to save the HTML map (default: 'citation_map.html')
- `csv_output_path`: Path to save the CSV file (default: 'citation_info.csv')
- `parse_csv`: Whether to read from existing CSV file (default: False)
- `affiliation_conservative`: Whether to use conservative affiliation matching (default: False)
- `num_processes`: Number of parallel processes (default: 16)
- `use_proxy`: Whether to use proxy for Google Scholar (default: False)
- `pin_colorful`: Whether to use colorful pins on the map (default: True)
- `print_citing_affiliations`: Whether to print citing affiliations (default: True) 