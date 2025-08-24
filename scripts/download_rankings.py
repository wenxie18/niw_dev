#!/usr/bin/env python3
"""
Unified script to download university rankings from multiple sources and convert to CSV
Supports: Times Higher Education (THE), QS World Rankings
"""

import json
import csv
import os
import sys
import time
import requests
import re
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

class RankingsDownloader:
    """Base class for downloading university rankings from different sources"""
    
    def __init__(self, source_name: str, output_dir: str):
        self.source_name = source_name
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def download(self) -> Optional[Dict]:
        """Download rankings data - to be implemented by subclasses"""
        raise NotImplementedError
        
    def parse(self, data: Dict) -> List[Dict]:
        """Parse rankings data - to be implemented by subclasses"""
        raise NotImplementedError
        
    def get_csv_filename(self, year: int) -> str:
        """Generate CSV filename based on source and year"""
        return f"{self.source_name.lower()}_{year}.csv"

class THERankingsDownloader(RankingsDownloader):
    """Downloader for Times Higher Education (THE) rankings"""
    
    def __init__(self, output_dir: str, year: str = None):
        super().__init__("THE", output_dir)
        self.year = year or config.RANKINGS_DEFAULT_YEAR
        self.api_url = self._get_api_url()
        
    def _get_api_url(self) -> str:
        """Get API URL for the specified year"""
        if self.year not in config.RANKINGS_API_ENDPOINTS.get('THE', {}):
            print(f"⚠️  No API endpoint found for THE {self.year}, using default year {config.RANKINGS_DEFAULT_YEAR}")
            self.year = config.RANKINGS_DEFAULT_YEAR
            
        return config.RANKINGS_API_ENDPOINTS['THE'][self.year]
        
    def download(self) -> Optional[Dict]:
        """Download THE rankings from JSON API"""
        try:
            print(f"📥 Downloading {self.source_name} {self.year} rankings from API...")
            print(f"🔗 URL: {self.api_url}")
            
            response = requests.get(self.api_url, headers=self.headers)
            response.raise_for_status()
            
            rankings_data = response.json()
            
            # Save raw data
            raw_file = os.path.join(self.output_dir, f"{self.source_name.lower()}_rankings_{self.year}_raw.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(rankings_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved raw data to: {raw_file}")
            
            return rankings_data
            
        except Exception as e:
            print(f"❌ Error downloading {self.source_name} rankings: {e}")
            return None
    
    def parse(self, data: Dict) -> List[Dict]:
        """Parse THE rankings data"""
        try:
            if 'data' not in data:
                print(f"❌ No 'data' field in {self.source_name} JSON")
                return []
            
            universities = []
            for item in data['data']:
                try:
                    university = {
                        'rank': item.get('rank', ''),
                        'university_name': item.get('name', '').split('(')[0].strip() if item.get('name') else '',
                        'country': item.get('location', ''),
                        'overall_score': item.get('scores_overall', ''),
                        'teaching': item.get('scores_teaching', ''),
                        'research_environment': item.get('scores_research', ''),
                        'research_quality': item.get('scores_citations', ''),
                        'industry': item.get('scores_industry_income', ''),
                        'international_outlook': item.get('scores_international_outlook', ''),
                        'student_count': item.get('stats_number_students', ''),
                        'student_staff_ratio': item.get('stats_student_staff_ratio', ''),
                        'international_students': item.get('stats_pc_intl_students', ''),
                        'female_male_ratio': item.get('stats_female_male_ratio', '')
                    }
                    
                    # Clean up country field
                    if university['country'] and 'Country' in university['country']:
                        university['country'] = university['country'].replace('Country', '').strip()
                    
                    universities.append(university)
                    
                except Exception as e:
                    print(f"Warning: Could not parse {self.source_name} university item: {e}")
                    continue
            
            return universities
            
        except Exception as e:
            print(f"❌ Error parsing {self.source_name} rankings: {e}")
            return []

class QSRankingsDownloader(RankingsDownloader):
    """Downloader for QS World Rankings"""
    
    def __init__(self, output_dir: str, year: str = None):
        super().__init__("QS", output_dir)
        self.year = year or config.RANKINGS_DEFAULT_YEAR
        self.base_url = self._get_base_url()
        
    def _get_base_url(self) -> str:
        """Get base URL for the specified year"""
        if self.year not in config.RANKINGS_API_ENDPOINTS.get('QS', {}):
            print(f"⚠️  No QS endpoint found for {self.year}, using default year {config.RANKINGS_DEFAULT_YEAR}")
            self.year = config.RANKINGS_DEFAULT_YEAR
            
        return config.RANKINGS_API_ENDPOINTS['QS'][self.year]
        
    def download(self) -> Optional[Dict]:
        """Download QS rankings from Excel file"""
        try:
            print(f"📥 Downloading {self.source_name} {self.year} rankings from Excel file...")
            
            # Get Excel download URL from config
            if self.year not in config.RANKINGS_API_ENDPOINTS.get('QS', {}):
                print(f"⚠️  No QS endpoint found for {self.year}, using default year {config.RANKINGS_DEFAULT_YEAR}")
                self.year = config.RANKINGS_DEFAULT_YEAR
            
            qs_config = config.RANKINGS_API_ENDPOINTS['QS'][self.year]
            if qs_config.get('type') != 'excel_download':
                print(f"❌ Invalid QS config type: {qs_config.get('type')}")
                return None
                
            excel_url = qs_config['url']
            print(f"🔗 Excel URL: {excel_url}")
            
            # Download the Excel file
            response = requests.get(excel_url, headers=self.headers)
            if response.status_code == 200:
                # Save Excel file
                excel_file = os.path.join(self.output_dir, f"{self.source_name.lower()}_rankings_{self.year}.xlsx")
                with open(excel_file, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded Excel file: {excel_file}")
                
                # Try to parse Excel and convert to our format
                try:
                    import pandas as pd
                    df = pd.read_excel(excel_file)
                    
                    # Save raw data as JSON
                    raw_data = {
                        'source': 'QS',
                        'year': self.year,
                        'excel_file': excel_file,
                        'columns': df.columns.tolist(),
                        'total_rows': len(df),
                        'sample_data': df.head().to_dict('records')
                    }
                    
                    raw_file = os.path.join(self.output_dir, f"{self.source_name.lower()}_rankings_{self.year}_raw.json")
                    with open(raw_file, 'w', encoding='utf-8') as f:
                        json.dump(raw_data, f, indent=2, ensure_ascii=False)
                    print(f"✅ Saved raw data to: {raw_file}")
                    
                    return raw_data
                    
                except ImportError:
                    print("⚠️  pandas not available, saving Excel file only")
                    raw_data = {
                        'source': 'QS',
                        'year': self.year,
                        'excel_file': excel_file,
                        'note': 'Excel file downloaded but pandas not available for parsing'
                    }
                    return raw_data
                    
            else:
                print(f"⚠️  Could not download Excel file (status: {response.status_code})")
                # Fallback to HTML download
                return self._download_html_fallback()
                
        except Exception as e:
            print(f"❌ Error downloading {self.source_name} rankings: {e}")
            return self._download_html_fallback()
    
    def _download_html_fallback(self) -> Optional[Dict]:
        """Fallback to HTML download if Excel fails"""
        try:
            print(f"📥 Falling back to HTML download...")
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            raw_data = {
                'source': 'QS',
                'year': self.year,
                'note': 'Excel download failed, using HTML fallback',
                'html_content_length': len(response.text)
            }
            
            # Save HTML
            html_file = os.path.join(self.output_dir, f"{self.source_name.lower()}_rankings_{self.year}_raw.html")
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"✅ Saved HTML fallback to: {html_file}")
            
            return raw_data
            
        except Exception as e:
            print(f"❌ HTML fallback also failed: {e}")
            return None
        
    def parse(self, data: Dict) -> List[Dict]:
        """Parse QS rankings data from Excel or HTML"""
        try:
            # Check if we have Excel data
            if 'excel_file' in data and os.path.exists(data['excel_file']):
                print(f"📊 Parsing QS rankings from Excel file...")
                return self._parse_excel_data(data)
            else:
                print(f"📊 Parsing QS rankings from HTML (fallback)...")
                return self._parse_html_data(data)
                
        except Exception as e:
            print(f"❌ Error parsing {self.source_name} rankings: {e}")
            return []
    
    def _parse_excel_data(self, data: Dict) -> List[Dict]:
        """Parse QS rankings from Excel file"""
        try:
            import pandas as pd
            
            excel_file = data['excel_file']
            df = pd.read_excel(excel_file)
            
            print(f"📋 Excel columns: {data.get('columns', [])}")
            print(f"📊 Total rows: {data.get('total_rows', len(df))}")
            
            universities = []
            
            # Based on QS Excel structure analysis
            # Column 0: Index (1,2,3...), Column 1: 2025 Rank, Column 3: Institution Name, Column 4: Location
            rank_col = df.columns[1]  # 2025 QS World University Rankings
            name_col = df.columns[3]  # Institution Name
            country_col = df.columns[4]  # Location
            
            if rank_col and name_col and country_col:
                print(f"✅ Found columns: Rank={rank_col}, Name={name_col}, Country={country_col}")
                
                # Skip first 3 rows (headers) and start from row 3 (index 3)
                for idx in range(3, len(df)):
                    try:
                        row = df.iloc[idx]
                        
                        # Check if this is a valid data row (rank can be numeric or range like "601-610")
                        rank_val = row[rank_col]
                        if pd.isna(rank_val):
                            continue
                        
                        # Accept any rank format: individual (1,2,3...) or group (601-610, 851-900, 1401+)
                        rank_str = str(rank_val).strip()
                        if not rank_str or rank_str == '':
                            continue
                            
                        university = {
                            'rank': rank_str,  # Keep original format (1, 2, 3... or 601-610, 851-900, 1401+)
                            'university_name': str(row[name_col]).strip() if pd.notna(row[name_col]) else '',
                            'country': str(row[country_col]).strip() if pd.notna(row[country_col]) else ''
                        }
                        
                        # Only add if we have valid data
                        if university['rank'] and university['university_name'] and university['country']:
                            universities.append(university)
                            
                    except Exception as e:
                        print(f"Warning: Could not parse row {idx}: {e}")
                        continue
                        
            else:
                print(f"⚠️  Could not identify required columns. Available columns: {list(df.columns)}")
                # Return sample data as fallback
                return self._get_sample_universities()
            
            return universities
            
        except Exception as e:
            print(f"❌ Error parsing Excel: {e}")
            return self._get_sample_universities()
    
    def _parse_html_data(self, data: Dict) -> List[Dict]:
        """Parse QS rankings from HTML (fallback)"""
        print(f"⚠️  HTML parsing not yet implemented - returning sample data")
        return self._get_sample_universities()
    
    def _get_sample_universities(self) -> List[Dict]:
        """Return sample universities for demonstration"""
        print(f"📝 Returning sample data for demonstration")
        
        sample_universities = [
            {
                'rank': '1',
                'university_name': 'Massachusetts Institute of Technology (MIT)',
                'country': 'United States'
            },
            {
                'rank': '2', 
                'university_name': 'University of Cambridge',
                'country': 'United Kingdom'
            },
            {
                'rank': '3',
                'university_name': 'University of Oxford',
                'country': 'United Kingdom'
            },
            {
                'rank': '4',
                'university_name': 'Harvard University',
                'country': 'United States'
            },
            {
                'rank': '5',
                'university_name': 'Stanford University',
                'country': 'United States'
            }
        ]
        
        return sample_universities

class RankingsManager:
    """Main class to manage multiple ranking sources"""
    
    def __init__(self, year: str = None):
        self.output_dir = config.RANKINGS_WORLD_PATH
        os.makedirs(self.output_dir, exist_ok=True)
        self.year = year or config.RANKINGS_DEFAULT_YEAR
        
        # Initialize downloaders for different sources (THE and QS only)
        self.downloaders = {
            'THE': THERankingsDownloader(self.output_dir, self.year),
            'QS': QSRankingsDownloader(self.output_dir, self.year)
        }
    
    def download_source(self, source: str) -> bool:
        """Download rankings from a specific source"""
        if source not in self.downloaders:
            print(f"❌ Unknown source: {source}")
            return False
        
        downloader = self.downloaders[source]
        
        # Download data
        data = downloader.download()
        if not data:
            return False
        
        # Parse data
        universities = downloader.parse(data)
        if not universities:
            return False
        
        # Save processed data
        processed_file = os.path.join(self.output_dir, f"{source.lower()}_rankings_{self.year}.json")
        
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': source,
                    'year': datetime.now().year,
                    'download_date': datetime.now().strftime("%Y-%m-%d"),
                    'total_universities': len(universities)
                },
                'universities': universities
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved processed data to: {processed_file}")
        
        # Convert to CSV
        self.convert_to_csv(source, universities)
        
        return True
    
    def convert_to_csv(self, source: str, universities: List[Dict]):
        """Convert rankings data to CSV with configurable columns"""
        try:
            # Get CSV columns from config or use defaults
            csv_columns = getattr(config, 'RANKINGS_CSV_COLUMNS', ['rank', 'university_name', 'country'])
            
            # Create CSV filename based on current year
            current_year = datetime.now().year
            csv_filename = f"{source.lower()}_{current_year}.csv"
            csv_path = os.path.join(self.output_dir, csv_filename)
            
            # Write to CSV
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                
                for uni in universities:
                    # Only include columns that exist in the data
                    row = {col: uni.get(col, '') for col in csv_columns}
                    writer.writerow(row)
            
            print(f"✅ Created CSV: {csv_path}")
            print(f"📊 Total universities: {len(universities)}")
            
            # Show sample data
            print(f"\n📋 Sample data:")
            for i, uni in enumerate(universities[:5]):
                rank = uni.get('rank', 'N/A')
                name = uni.get('university_name', 'N/A')
                country = uni.get('country', 'N/A')
                print(f"  {rank}: {name} ({country})")
            
            # Show country statistics
            self.show_country_stats(universities)
            
        except Exception as e:
            print(f"❌ Error creating CSV: {e}")
    
    def show_country_stats(self, universities: List[Dict]):
        """Show statistics by country"""
        country_counts = {}
        for uni in universities:
            country = uni.get('country', 'Unknown')
            country_counts[country] = country_counts.get(country, 0) + 1
        
        print(f"\n🌍 Top 10 countries by university count:")
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (country, count) in enumerate(sorted_countries[:10]):
            print(f"  {i+1:2d}. {country}: {count} universities")
    
    def download_all_sources(self):
        """Download from all configured sources"""
        print("🚀 Downloading from all configured ranking sources...")
        
        for source in self.downloaders.keys():
            print(f"\n{'='*50}")
            print(f"Processing {source} rankings...")
            print(f"{'='*50}")
            
            success = self.download_source(source)
            if success:
                print(f"✅ {source} rankings completed successfully")
            else:
                print(f"❌ {source} rankings failed")
            
            # Add delay between sources to be respectful
            time.sleep(2)

def show_help():
    print("🎓 University Rankings Downloader & Converter")
    print("=" * 60)
    print("Usage:")
    print("  python3 scripts/download_rankings.py                    # Download THE 2025 (default)")
    print("  python3 scripts/download_rankings.py THE               # Download THE 2025")
    print("  python3 scripts/download_rankings.py THE 2024          # Download THE 2024")
    print("  python3 scripts/download_rankings.py QS                # Download QS rankings")
    print("  python3 scripts/download_rankings.py --help            # Show this help")
    print("\nAvailable sources:", ", ".join(['THE', 'QS']))
    print("Available years:", ", ".join(['2024', '2025']))
    print("\nTo add new years, update config.py with new API endpoints")
    print("\nNote: ARWU rankings are now handled by the separate Selenium scraper")

def main():
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return
    
    print("🎓 University Rankings Downloader & Converter")
    print("=" * 60)
    
    # Parse command line arguments
    source = None
    year = None
    
    if len(sys.argv) > 1:
        source = sys.argv[1].upper()
    if len(sys.argv) > 2:
        year = sys.argv[2]
    
    manager = RankingsManager(year)
    
    # Check if specific source is requested
    if source:
        if source in manager.downloaders:
            print(f"📥 Downloading {source} {manager.year} rankings...")
            success = manager.download_source(source)
            if success:
                print(f"🎉 {source} {manager.year} rankings completed successfully!")
            else:
                print(f"❌ {source} {manager.year} rankings failed!")
        else:
            print(f"❌ Unknown source: {source}")
            print(f"Available sources: {', '.join(manager.downloaders.keys())}")
    else:
        # Download from default source (THE)
        print(f"📥 Downloading from default source (THE) for {manager.year}...")
        success = manager.download_source('THE')
        if success:
            print(f"🎉 THE {manager.year} rankings completed successfully!")
        else:
            print(f"❌ THE {manager.year} rankings failed!")

if __name__ == "__main__":
    main()
