#!/usr/bin/env python3
"""
ARWU (Shanghai Ranking) Selenium Scraper
Scrapes university rankings from ShanghaiRanking website using browser automation
Supports both worldwide ARWU rankings and China-specific rankings
"""

import json
import csv
import os
import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

class ARWUSeleniumScraper:
    """Selenium-based scraper for ARWU/ShanghaiRanking university rankings"""
    
    def __init__(self, ranking_type="worldwide", year="2025"):
        """
        Initialize the scraper
        
        Args:
            ranking_type: "worldwide" for ARWU world rankings, "china" for China-specific rankings
            year: Year of rankings (e.g., "2025")
        """
        self.ranking_type = ranking_type
        self.year = year
        
        # Set base URL and output paths based on ranking type
        if ranking_type == "worldwide":
            self.base_url = config.RANKINGS_API_ENDPOINTS.get('ARWU', {}).get(year, {}).get('url', 
                f"https://www.shanghairanking.com/rankings/arwu/{year}")
            self.output_dir = config.RANKINGS_WORLD_PATH
            self.output_filename = f"arwu_{year}"
        elif ranking_type == "china":
            self.base_url = config.COUNTRY_RANKINGS_ENDPOINTS.get('China', {}).get(year, {}).get('url',
                f"https://www.shanghairanking.com/rankings/bcur/{year}")
            # For China rankings, create china subdirectory under countries
            self.output_dir = os.path.join(config.RANKINGS_COUNTRIES_PATH, "china")
            self.output_filename = f"arwu_{year}"
        else:
            raise ValueError("ranking_type must be 'worldwide' or 'china'")
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.driver = None
        self.all_universities = []
        
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        print("🔧 Setting up Chrome driver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Try to use webdriver-manager to get the latest ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome driver setup successful")
        except Exception as e:
            print(f"⚠️  WebDriver manager failed: {e}")
            print("🔄 Trying to use system ChromeDriver...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Chrome driver setup successful (system)")
            except Exception as e2:
                print(f"❌ Failed to setup Chrome driver: {e2}")
                return False
        
        return True
    
    def navigate_to_page(self):
        """Navigate to the ARWU rankings page"""
        try:
            print(f"🌐 Navigating to: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for the page to load
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            
            print("✅ Page loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error navigating to page: {e}")
            return False
    
    def find_pagination_elements(self):
        """Find pagination buttons and elements"""
        try:
            print("🔍 Looking for pagination elements...")
            
            # Look for pagination container
            pagination_selectors = [
                "//div[contains(@class, 'ant-pagination')]",
                "//nav[contains(@class, 'pagination')]",
                "//div[contains(@class, 'pagination')]",
                "//ul[contains(@class, 'pagination')]"
            ]
            
            pagination_container = None
            for selector in pagination_selectors:
                try:
                    pagination_container = self.driver.find_element(By.XPATH, selector)
                    print(f"✅ Found pagination container with selector: {selector}")
                    break
                except:
                    continue
            
            if not pagination_container:
                print("❌ No pagination container found")
                return None
            
            # Look for page number buttons
            page_buttons = []
            
            # Try different selectors for page buttons
            button_selectors = [
                "//li[contains(@class, 'ant-pagination-item')]//a",
                "//a[contains(@class, 'page-link')]",
                "//a[contains(@class, 'pagination-item')]",
                "//button[contains(@class, 'page')]"
            ]
            
            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    if buttons:
                        page_buttons = buttons
                        print(f"✅ Found {len(buttons)} page buttons with selector: {selector}")
                        break
                except:
                    continue
            
            if not page_buttons:
                print("❌ No page buttons found")
                return None
            
            # Filter out non-numeric buttons (like "Previous", "Next", "...")
            numeric_buttons = []
            for button in page_buttons:
                text = button.text.strip()
                if text.isdigit():
                    numeric_buttons.append(button)
            
            print(f"✅ Found {len(numeric_buttons)} numeric page buttons")
            
            # Also look for "Next" button to expand pagination
            next_button = None
            next_selectors = [
                "//li[contains(@class, 'ant-pagination-next')]//a",
                "//a[contains(@class, 'next')]",
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]"
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.XPATH, selector)
                    print(f"✅ Found Next button with selector: {selector}")
                    break
                except:
                    continue
            
            # Look for "..." button that might expand pagination
            ellipsis_button = None
            ellipsis_selectors = [
                "//li[contains(@class, 'ant-pagination-item')]//span[contains(text(), '•••')]",
                "//span[contains(text(), '•••')]",
                "//span[contains(text(), '...')]"
            ]
            
            for selector in ellipsis_selectors:
                try:
                    ellipsis_button = self.driver.find_element(By.XPATH, selector)
                    print(f"✅ Found ellipsis button with selector: {selector}")
                    break
                except:
                    continue
            
            return {
                'numeric_buttons': numeric_buttons,
                'next_button': next_button,
                'ellipsis_button': ellipsis_button,
                'container': pagination_container
            }
            
        except Exception as e:
            print(f"❌ Error finding pagination elements: {e}")
            return None
    
    def extract_universities_from_current_page(self):
        """Extract universities from the current page based on ranking type"""
        try:
            if self.ranking_type == "worldwide":
                return self._extract_worldwide_arwu()
            elif self.ranking_type == "china":
                return self._extract_china_bcur()
            else:
                print(f"❌ Unknown ranking type: {self.ranking_type}")
                return []
        except Exception as e:
            print(f"❌ Error extracting universities: {e}")
            return []
    
    def _extract_worldwide_arwu(self):
        """Extract universities from worldwide ARWU page"""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for the main ranking table
            ranking_table = soup.find('table')
            
            if not ranking_table:
                print("❌ No ranking table found")
                return []
            
            # Find all table rows (skip header)
            rows = ranking_table.find_all('tr')[1:]  # Skip header row
            print(f"  Found {len(rows)} data rows in table")
            
            universities = []
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:  # ARWU table has: rank, institution, country, national_rank, total_score, alumni_score
                    try:
                        # Extract rank (first column)
                        rank_cell = cells[0].get_text(strip=True)
                        rank_match = re.search(r'(\d+)', rank_cell)
                        if not rank_match:
                            continue
                        
                        rank = rank_match.group(1)
                        
                        # Extract university name (second column)
                        name_cell = cells[1]
                        name_link = name_cell.find('a')
                        if name_link:
                            name = name_link.get_text(strip=True)
                        else:
                            name_text = name_cell.get_text(strip=True)
                            name = re.sub(r'\s+', ' ', name_text).strip()
                        
                        # Extract country from the third column (flag images)
                        country = "Unknown"
                        country_cell = cells[2]
                        country_img = country_cell.find('div', class_='region-img')
                        if country_img:
                            style = country_img.get('style', '')
                            # Map flag URLs to country names
                            if 'us.png' in style:
                                country = "United States"
                            elif 'gb.png' in style:
                                country = "United Kingdom"
                            elif 'cn.png' in style:
                                country = "China"
                            elif 'fr.png' in style:
                                country = "France"
                            elif 'de.png' in style:
                                country = "Germany"
                            elif 'jp.png' in style:
                                country = "Japan"
                            elif 'ca.png' in style:
                                country = "Canada"
                            elif 'au.png' in style:
                                country = "Australia"
                            else:
                                country = "Unknown"
                        
                        # Only add if we have valid data
                        if rank and name and len(name) > 3:
                            universities.append({
                                'rank': rank,
                                'university_name': name,
                                'country': country
                            })
                            
                    except Exception as e:
                        print(f"⚠️  Error parsing row: {e}")
                        continue
            
            print(f"  ✅ Extracted {len(universities)} universities from worldwide ARWU page")
            return universities
            
        except Exception as e:
            print(f"❌ Error in worldwide ARWU extraction: {e}")
            return []
    
    def _extract_china_bcur(self):
        """Extract universities from China BCUR page"""
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for the main ranking table
            ranking_table = soup.find('table')
            
            if not ranking_table:
                print("❌ No ranking table found")
                return []
            
            # Find all table rows (skip header)
            rows = ranking_table.find_all('tr')[1:]  # Skip header row
            print(f"  Found {len(rows)} data rows in China BCUR table")
            
            universities = []
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:  # BCUR table has: rank, institution, region, total_score
                    try:
                        # Extract rank (first column)
                        rank_cell = cells[0].get_text(strip=True)
                        rank_match = re.search(r'(\d+)', rank_cell)
                        if not rank_match:
                            continue
                        
                        rank = rank_match.group(1)
                        
                        # Extract university name (second column) - handle duplication
                        name_cell = cells[1]
                        name_text = name_cell.get_text(strip=True)
                        # Clean up duplicated names (e.g., "South China University of TechnologySouth China University of Technology")
                        name = re.sub(r'(.+?)\1', r'\1', name_text).strip()
                        
                        # Extract region (third column)
                        region = cells[2].get_text(strip=True) if len(cells) > 2 else "Unknown"
                        
                        # Only add if we have valid data
                        if rank and name and len(name) > 3:
                            universities.append({
                                'rank': rank,
                                'university_name': name,
                                'country': 'China',
                                'region': region
                            })
                            
                    except Exception as e:
                        print(f"⚠️  Error parsing China BCUR row: {e}")
                        continue
            
            print(f"  ✅ Extracted {len(universities)} universities from China BCUR page")
            return universities
            
        except Exception as e:
            print(f"❌ Error in China BCUR extraction: {e}")
            return []
    
    def click_page_button(self, button, page_number):
        """Click a specific page button"""
        try:
            print(f"🖱️  Clicking page {page_number} button...")
            
            # Scroll to the button to make it visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            
            # Click the button
            button.click()
            
            # Wait for the page content to change
            time.sleep(3)
            
            print(f"✅ Successfully clicked page {page_number}")
            return True
            
        except Exception as e:
            print(f"❌ Error clicking page {page_number} button: {e}")
            return False
    
    def safe_find_elements(self, xpath_selector, max_retries=3):
        """Safely find elements with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                elements = self.driver.find_elements(By.XPATH, xpath_selector)
                return elements
            except Exception as e:
                if "stale element" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️  Stale element on attempt {attempt + 1}, retrying...")
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ Error finding elements: {e}")
                    return []
        return []
    
    def safe_find_element(self, xpath_selector, max_retries=3):
        """Safely find a single element with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                element = self.driver.find_element(By.XPATH, xpath_selector)
                return element
            except Exception as e:
                if "stale element" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️  Stale element on attempt {attempt + 1}, retrying...")
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ Error finding element: {e}")
                    return None
        return None
    
    def scrape_all_pages(self):
        """Scrape all available pages by simply clicking Next button"""
        print("🚀 Starting to scrape all available pages...")
        
        # Setup driver and navigate to page first
        if not self.setup_driver():
            print("❌ Failed to setup driver")
            return None
            
        if not self.navigate_to_page():
            print("❌ Failed to navigate to page")
            return None
        
        # Start with page 1
        self.all_universities = []
        current_page = 1
        max_pages = 50  # Default safety limit, can be overridden for testing
        
        # Extract from first page
        print(f"\n📄 Processing page {current_page}...")
        universities = self.extract_universities_from_current_page()
        if universities:
            self.all_universities.extend(universities)
            print(f"✅ Page {current_page}: Added {len(universities)} universities")
        else:
            print(f"❌ Page {current_page}: No universities extracted")
            return None
        
        # Continue to next pages using Next button
        while current_page < max_pages:
            print(f"\n🔄 Looking for Next button to go to page {current_page + 1}...")
            
            # Find pagination elements
            pagination_data = self.find_pagination_elements()
            if not pagination_data:
                print("❌ No pagination elements found, stopping")
                break
            
            # Look for Next button
            next_button = pagination_data.get('next_button')
            if not next_button:
                print("❌ No Next button found, stopping")
                break
            
            # Check if Next button is disabled (we're on the last page)
            try:
                next_button_classes = next_button.get_attribute("class")
                if "disabled" in next_button_classes or "ant-pagination-disabled" in next_button_classes:
                    print("✅ Next button is disabled, reached last page")
                    break
            except:
                pass
            
            # Click Next button
            try:
                print(f"🔄 Clicking Next button to go to page {current_page + 1}...")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)
                next_button.click()
                time.sleep(3)
                
                current_page += 1
                print(f"✅ Successfully navigated to page {current_page}")
                
                # Extract universities from the new page
                universities = self.extract_universities_from_current_page()
                if universities:
                    self.all_universities.extend(universities)
                    print(f"✅ Page {current_page}: Added {len(universities)} universities")
                else:
                    print(f"⚠️  Page {current_page}: No universities extracted")
                
            except Exception as e:
                print(f"❌ Error clicking Next button: {e}")
                break
        
        print(f"\n🎉 Scraping completed! Total universities collected: {len(self.all_universities)}")
        print(f"📄 Pages processed: {current_page}")
        print(f"📊 Unique universities: {len(set(uni['university_name'] for uni in self.all_universities))}")
        return self.all_universities
        
    def save_results(self):
        """Save the scraped results to JSON and CSV in the correct locations"""
        try:
            # Remove duplicates based on university name
            unique_universities = []
            seen_names = set()
            
            for uni in self.all_universities:
                normalized_name = re.sub(r'\s+', ' ', uni['university_name'].strip()).lower()
                if normalized_name not in seen_names:
                    unique_universities.append(uni)
                    seen_names.add(normalized_name)
            
            print(f"🎯 Unique universities after deduplication: {len(unique_universities)}")
            
            # Sort by rank
            def sort_key(uni):
                rank = uni['rank']
                if '-' in rank:
                    base_num = int(rank.split('-')[0])
                    return base_num
                else:
                    return int(rank)
            
            unique_universities.sort(key=sort_key)
            
            # Save to JSON with metadata matching our other ranking files
            json_filename = f"{self.output_filename}.json"
            json_path = os.path.join(self.output_dir, json_filename)
            
            results = {
                'metadata': {
                    'source': f'ARWU {self.ranking_type.title()} {self.year}',
                    'year': self.year,
                    'download_date': time.strftime('%Y-%m-%d'),
                    'total_universities': len(unique_universities),
                    'scraping_method': 'Selenium browser automation',
                    'ranking_type': self.ranking_type
                },
                'universities': unique_universities
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Results saved to: {json_path}")
            
            # Save as CSV with same format as QS and THE files
            csv_filename = f"{self.output_filename}.csv"
            csv_path = os.path.join(self.output_dir, csv_filename)
            
            # Use the same CSV columns as defined in config
            csv_columns = config.RANKINGS_CSV_COLUMNS
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=csv_columns)
                writer.writeheader()
                
                for uni in unique_universities:
                    # Only include columns that exist in the data
                    row = {col: uni.get(col, '') for col in csv_columns}
                    writer.writerow(row)
            
            print(f"✅ CSV saved to: {csv_path}")
            
            # Show sample results
            print(f"\n📋 Sample universities:")
            for i, uni in enumerate(unique_universities[:10]):
                print(f"  {uni['rank']}: {uni['university_name']} ({uni['country']})")
            
            return unique_universities
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return None

def main():
    """Main function to run the ARWU scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ARWU ShanghaiRanking University Rankings Scraper')
    parser.add_argument('--type', choices=['worldwide', 'china'], default='worldwide',
                       help='Type of rankings to scrape: worldwide (ARWU) or china (BCUR)')
    parser.add_argument('--year', default='2025', 
                       help='Year of rankings to scrape (default: 2025)')
    
    args = parser.parse_args()
    
    print(f"🎓 ARWU ShanghaiRanking University Rankings Scraper")
    print(f"📊 Type: {args.type.title()} rankings")
    print(f"📅 Year: {args.year}")
    print("=" * 60)
    
    try:
        scraper = ARWUSeleniumScraper(ranking_type=args.type, year=args.year)
        
        universities = scraper.scrape_all_pages()
        if universities:
            scraper.save_results()
            print(f"\n🎉 Successfully scraped {len(universities)} universities!")
        else:
            print("❌ No universities scraped")
            
    except Exception as e:
        print(f"❌ Error in main: {e}")
    finally:
        if 'scraper' in locals() and scraper.driver:
            scraper.driver.quit()
            print("�� Browser closed")

def show_help():
    """Show help information"""
    print("🎓 ARWU ShanghaiRanking University Rankings Scraper")
    print("=" * 60)
    print("Usage:")
    print("  python3 scripts/arwu_selenium_scraper.py                    # Scrape worldwide ARWU 2025 rankings")
    print("  python3 scripts/arwu_selenium_scraper.py --type worldwide   # Scrape worldwide ARWU rankings")
    print("  python3 scripts/arwu_selenium_scraper.py --type china       # Scrape China-specific rankings")
    print("  python3 scripts/arwu_selenium_scraper.py --year 2024        # Scrape 2024 rankings")
    print("  python3 scripts/arwu_selenium_scraper.py --help             # Show this help")
    print("\nOutput locations:")
    print("  Worldwide rankings: data/rankings/world/arwu_YYYY.csv")
    print("  China rankings: data/rankings/countries/china/arwu_YYYY.csv")
    print("\nNote: This scraper uses Selenium browser automation for JavaScript-based pagination")

if __name__ == "__main__":
    main()
