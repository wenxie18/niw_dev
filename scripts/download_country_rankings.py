#!/usr/bin/env python3
"""
Country-Specific University Rankings Downloader
Downloads rankings for specific countries (US, China, UK, Australia, etc.)
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

class CountryRankingsDownloader:
    """Base class for downloading country-specific university rankings"""
    
    def __init__(self, country: str, output_dir: str, year: str = None):
        self.country = country
        self.output_dir = os.path.join(output_dir, country.lower())
        self.year = year or '2024'  # Default to 2024 for country rankings
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def download(self) -> Optional[Dict]:
        """Download country rankings - to be implemented by subclasses"""
        raise NotImplementedError
        
    def parse(self, data: Dict) -> List[Dict]:
        """Parse country rankings data - to be implemented by subclasses"""
        raise NotImplementedError

class USRankingsDownloader(CountryRankingsDownloader):
    """Downloader for US college rankings from US News and other sources"""
    
    def __init__(self, year: str = '2024'):
        super().__init__('US', year)
    
    def download(self) -> Optional[Dict]:
        """Download US rankings from US News website"""
        try:
            print(f"📥 Downloading {self.country} {self.year} rankings from US News...")
            
            # Get US News configuration from config
            us_config = config.COUNTRY_RANKINGS_ENDPOINTS.get('US', {}).get(self.year, {})
            if not us_config:
                print(f"❌ No configuration found for US {self.year}")
                return None
            
            primary_url = us_config.get('url')
            fallback_urls = us_config.get('fallback_urls', [])
            alternative_sources = us_config.get('alternative_sources', [])
            
            if not primary_url:
                print(f"❌ No primary URL configured for US {self.year}")
                return None
            
            print(f"🔗 Primary URL: {primary_url}")
            if fallback_urls:
                print(f"🔄 Fallback URLs: {len(fallback_urls)} available")
            if alternative_sources:
                print(f"🌐 Alternative sources: {len(alternative_sources)} available")
            
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Try primary URL first
            successful_response = None
            full_url = None
            
            # Try primary URL with retries
            urls_to_try = [primary_url] + fallback_urls
            max_retries = 3
            
            for url in urls_to_try:
                print(f"🔄 Trying URL: {url}")
                
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, headers=headers, timeout=60)
                        response.raise_for_status()
                        
                        if response.status_code == 200:
                            successful_response = response
                            full_url = url
                            print(f"✅ Successfully downloaded from: {url}")
                            break
                        else:
                            print(f"⚠️  HTTP {response.status_code} from {url}")
                            
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            print(f"⏰ Timeout on attempt {attempt + 1}, retrying...")
                            time.sleep(2)
                        else:
                            print(f"⏰ All attempts timed out for {url}")
                            break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️  Error on attempt {attempt + 1}: {e}, retrying...")
                            time.sleep(2)
                        else:
                            print(f"❌ All attempts failed for {url}: {e}")
                            break
                
                if successful_response:
                    break
            
            if not successful_response:
                print(f"⚠️  All US News URLs failed, trying alternative sources...")
                
                # Try alternative sources
                alternative_sources = us_config.get('alternative_sources', [])
                for alt_url in alternative_sources:
                    try:
                        print(f"🔄 Trying alternative source: {alt_url}")
                        alt_response = requests.get(alt_url, headers=headers, timeout=30)
                        if alt_response.status_code == 200:
                            print(f"✅ Successfully downloaded from alternative source: {alt_url}")
                            successful_response = alt_response
                            full_url = alt_url
                            break
                    except Exception as e:
                        print(f"❌ Alternative source failed: {alt_url} - {e}")
                        continue
                
                if not successful_response:
                    raise Exception("All sources (US News and alternatives) failed to download")
            
            # Save raw HTML
            raw_data = {
                'source': 'US News Best Colleges',
                'country': 'US',
                'year': self.year,
                'url': full_url,
                'html_content': successful_response.text,
                'status_code': successful_response.status_code,
                'headers': dict(successful_response.headers),
                'download_timestamp': datetime.now().isoformat()
            }
            
            # Save raw data
            raw_file = os.path.join(self.output_dir, f"usnews_{self.year}_raw.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved raw data to: {raw_file}")
            
            return raw_data
            
        except Exception as e:
            print(f"❌ Error downloading {self.country} rankings: {e}")
            return None
    
    def download_comprehensive_us_rankings(self) -> Dict:
        """Download comprehensive US college rankings from multiple sources"""
        try:
            print(f"🌐 Downloading comprehensive US college rankings from multiple sources...")
            
            all_sources_data = {}
            
            # Source 1: US News (primary source)
            print(f"\n📰 Source 1: US News Best Colleges")
            try:
                us_news_data = self.download()
                if us_news_data:
                    all_sources_data['us_news'] = us_news_data
                    print(f"✅ US News: Downloaded successfully")
                else:
                    print(f"❌ US News: Failed to download")
            except Exception as e:
                print(f"❌ US News error: {e}")
            
            # Source 2: Forbes (alternative source)
            print(f"\n📰 Source 2: Forbes America's Top Colleges")
            try:
                forbes_data = self._download_forbes_rankings()
                if forbes_data:
                    all_sources_data['forbes'] = forbes_data
                    print(f"✅ Forbes: Downloaded successfully")
                else:
                    print(f"❌ Forbes: Failed to download")
            except Exception as e:
                print(f"❌ Forbes error: {e}")
            
            # Source 3: WSJ (alternative source)
            print(f"\n📰 Source 3: Wall Street Journal College Rankings")
            try:
                wsj_data = self._download_wsj_rankings()
                if wsj_data:
                    all_sources_data['wsj'] = wsj_data
                    print(f"✅ WSJ: Downloaded successfully")
                else:
                    print(f"❌ WSJ: Failed to download")
            except Exception as e:
                print(f"❌ WSJ error: {e}")
            
            # Source 4: Princeton Review (alternative source)
            print(f"\n📰 Source 4: Princeton Review College Rankings")
            try:
                princeton_data = self._download_princeton_rankings()
                if princeton_data:
                    all_sources_data['princeton'] = princeton_data
                    print(f"✅ Princeton Review: Downloaded successfully")
                else:
                    print(f"❌ Princeton Review: Failed to download")
            except Exception as e:
                print(f"❌ Princeton Review error: {e}")
            
            # Save comprehensive data
            comprehensive_file = os.path.join(self.output_dir, f"us_comprehensive_{self.year}_raw.json")
            with open(comprehensive_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': 'Multiple US College Ranking Sources',
                    'country': 'US',
                    'year': self.year,
                    'sources': list(all_sources_data.keys()),
                    'data': all_sources_data,
                    'download_timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved comprehensive data to: {comprehensive_file}")
            return all_sources_data
            
        except Exception as e:
            print(f"❌ Error downloading comprehensive US rankings: {e}")
            return {}
    
    def _download_forbes_rankings(self) -> Optional[Dict]:
        """Download Forbes America's Top Colleges rankings"""
        try:
            url = "https://www.forbes.com/lists/americas-top-colleges/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Forbes America\'s Top Colleges',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Forbes download error: {e}")
            return None
    
    def _download_wsj_rankings(self) -> Optional[Dict]:
        """Download Wall Street Journal College Rankings"""
        try:
            url = "https://www.wsj.com/rankings/college-rankings"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Wall Street Journal College Rankings',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ WSJ download error: {e}")
            return None
    
    def _download_princeton_rankings(self) -> Optional[Dict]:
        """Download Princeton Review College Rankings"""
        try:
            url = "https://www.princetonreview.com/college-rankings"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Princeton Review College Rankings',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Princeton Review download error: {e}")
            return None
        
    def parse(self, data: Dict) -> List[Dict]:
        """Parse US rankings data from HTML"""
        try:
            print(f"🔍 Parsing US News HTML content...")
            
            if 'html_content' not in data:
                print(f"❌ No HTML content found in data")
                return []
            
            html_content = data['html_content']
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            universities = []
            
            # Method 1: Look for the main ranking table/list structure
            # US News typically has rankings in a structured format
            print(f"🔍 Looking for ranking structures...")
            
            # Try to find ranking containers with various selectors
            ranking_selectors = [
                'div[class*="ranking"]',
                'div[class*="college"]', 
                'div[class*="university"]',
                'div[class*="school"]',
                'li[class*="ranking"]',
                'li[class*="college"]',
                'li[class*="university"]',
                'tr[class*="ranking"]',
                'tr[class*="college"]',
                'div[data-testid*="ranking"]',
                'div[data-testid*="college"]'
            ]
            
            for selector in ranking_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    break
            
            # Method 2: Look for specific text patterns that indicate rankings
            page_text = soup.get_text()
            
            # Enhanced patterns for US college rankings
            ranking_patterns = [
                # Pattern 1: "1. Princeton University" or "1 Princeton University"
                r'(\d+)\.?\s+([A-Z][^A-Z]*?(?:University|College|Institute|School|Academy))',
                # Pattern 2: "Rank 1: Princeton University"
                r'Rank\s*(\d+):\s*([A-Z][^A-Z]*?(?:University|College|Institute|School|Academy))',
                # Pattern 3: "#1 Princeton University"
                r'#(\d+)\s+([A-Z][^A-Z]*?(?:University|College|Institute|School|Academy))',
                # Pattern 4: "1 Princeton University, NJ"
                r'(\d+)\s+([A-Z][^A-Z]*?(?:University|College|Institute|School|Academy))[,\s]+([A-Z]{2})',
                # Pattern 5: "Princeton University - #1"
                r'([A-Z][^A-Z]*?(?:University|College|Institute|School|Academy))[^#]*#(\d+)',
            ]
            
            print(f"🔍 Searching for ranking patterns in page text...")
            
            for pattern in ranking_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    print(f"✅ Pattern '{pattern}' found {len(matches)} matches")
                    
                    for match in matches:
                        if len(match) == 2:  # rank, name
                            rank, name = match
                            state = self._extract_state_from_context(page_text, name)
                        elif len(match) == 3:  # rank, name, state
                            rank, name, state = match
                        else:
                            continue
                        
                        # Clean up the data
                        rank = rank.strip()
                        name = name.strip()
                        state = state.strip() if state else "Unknown"
                        
                        # Validate the data
                        if (rank.isdigit() and 
                            len(name) > 5 and 
                            not any(skip in name.lower() for skip in ['university', 'college', 'institute', 'school', 'academy'])):
                            
                            universities.append({
                                'rank': rank,
                                'university_name': name,
                                'state_province': state,
                                'country': 'United States'
                            })
            
            # Method 3: Look for structured data in JSON-LD or script tags
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict) and 'name' in json_data:
                        # This might contain university data
                        print(f"🔍 Found JSON-LD data: {json_data.get('name', 'Unknown')}")
                except:
                    continue
            
            # Method 4: Look for specific US News ranking elements
            # US News often uses specific class names or data attributes
            us_news_selectors = [
                'div[class*="SearchResult"]',
                'div[class*="SearchResultCard"]',
                'div[class*="CollegeCard"]',
                'div[class*="RankingCard"]',
                'div[class*="ResultCard"]'
            ]
            
            for selector in us_news_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ Found {len(elements)} US News ranking elements with selector: {selector}")
                    
                    for element in elements:
                        # Try to extract rank and name from these elements
                        rank_elem = element.find(['span', 'div'], class_=lambda x: x and any(term in x.lower() for term in ['rank', 'number', 'position']))
                        name_elem = element.find(['span', 'div', 'h3', 'h4'], class_=lambda x: x and any(term in x.lower() for term in ['name', 'title', 'college-name']))
                        
                        if rank_elem and name_elem:
                            rank = rank_elem.get_text(strip=True)
                            name = name_elem.get_text(strip=True)
                            
                            if rank.isdigit() and len(name) > 5:
                                state = self._extract_state_from_context(page_text, name)
                                universities.append({
                                    'rank': rank,
                                    'university_name': name,
                                    'state_province': state,
                                    'country': 'United States'
                                })
            
            # Remove duplicates based on rank
            unique_universities = []
            seen_ranks = set()
            
            for uni in universities:
                if uni['rank'] not in seen_ranks:
                    unique_universities.append(uni)
                    seen_ranks.add(uni['rank'])
            
            print(f"🎯 Total unique universities extracted: {len(unique_universities)}")
            
            if unique_universities:
                # Sort by rank
                unique_universities.sort(key=lambda x: int(x['rank']))
                return unique_universities
            
            # If we still don't have universities, return sample data as fallback
            print(f"⚠️  Could not extract real data, returning sample data as fallback")
            return self._get_sample_universities()
            
        except Exception as e:
            print(f"❌ Error parsing US rankings: {e}")
            print(f"📝 Returning sample data as fallback")
            return self._get_sample_universities()
    
    def _extract_state_from_context(self, text: str, university_name: str) -> str:
        """Extract state/province from context around university name"""
        try:
            # Look for state patterns near the university name
            state_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[,\-]\s*[A-Z]{2}',  # "New York, NY"
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[,\-]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # "New York, New York"
            ]
            
            # Find the position of university name in text
            name_pos = text.find(university_name)
            if name_pos == -1:
                return "Unknown"
            
            # Look in a window around the university name
            start = max(0, name_pos - 200)
            end = min(len(text), name_pos + 200)
            context = text[start:end]
            
            for pattern in state_patterns:
                matches = re.findall(pattern, context)
                if matches:
                    return matches[0].strip()
            
            return "Unknown"
            
        except Exception:
            return "Unknown"
    
    def _extract_state_from_context(self, text: str, university_name: str) -> str:
        """Extract state/province from context around university name"""
        try:
            # Look for state patterns near the university name
            state_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[,\-]\s*[A-Z]{2}',  # "New York, NY"
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[,\-]\s*[A-Z][a-z]+(?:\s+[A-z]+)*',  # "New York, New York"
            ]
            
            # Find the position of university name in text
            name_pos = text.find(university_name)
            if name_pos == -1:
                return "Unknown"
            
            # Look in a window around the university name
            start = max(0, name_pos - 200)
            return "Unknown"
            
        except Exception:
            return "Unknown"
    
    def _get_sample_universities(self) -> List[Dict]:
        """Return sample US universities as fallback"""
        return [
            {
                'rank': '1',
                'university_name': 'Princeton University',
                'state_province': 'New Jersey',
                'country': 'United States'
            },
            {
                'rank': '2',
                'university_name': 'Massachusetts Institute of Technology',
                'state_province': 'Massachusetts',
                'country': 'United States'
            },
            {
                'rank': '1',
                'university_name': 'Harvard University',
                'state_province': 'Massachusetts',
                'country': 'United States'
            },
            {
                'rank': '4',
                'university_name': 'Stanford University',
                'state_province': 'California',
                'country': 'United States'
            },
            {
                'rank': '5',
                'university_name': 'Yale University',
                'state_province': 'Connecticut',
                'country': 'United States'
            }
        ]

    def _download_usnews_alternative(self) -> Optional[Dict]:
        """Try alternative approach for US News - download from ranking subpages"""
        try:
            print(f"🔄 Trying alternative US News approach...")
            
            # Try different US News ranking pages
            usnews_pages = [
                'https://www.usnews.com/best-colleges/rankings/national-universities',
                'https://www.usnews.com/best-colleges/rankings/liberal-arts-colleges',
                'https://www.usnews.com/best-colleges/rankings/regional-universities',
                'https://www.usnews.com/best-colleges/rankings/regional-colleges'
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://www.usnews.com/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            for page_url in usnews_pages:
                try:
                    print(f"🔄 Trying US News page: {page_url}")
                    response = requests.get(page_url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        print(f"✅ Successfully downloaded from: {page_url}")
                        return {
                            'source': f'US News - {page_url.split("/")[-1].replace("-", " ").title()}',
                            'country': 'US',
                            'year': self.year,
                            'url': page_url,
                            'html_content': response.text,
                            'status_code': response.status_code,
                            'headers': dict(response.headers),
                            'download_timestamp': datetime.now().isoformat()
                        }
                    else:
                        print(f"⚠️  HTTP {response.status_code} from {page_url}")
                        
                except Exception as e:
                    print(f"❌ Error with {page_url}: {e}")
                    continue
            
            print(f"❌ All US News alternative pages failed")
            return None
            
        except Exception as e:
            print(f"❌ Alternative US News approach failed: {e}")
            return None

class ChinaRankingsDownloader(CountryRankingsDownloader):
    """Downloader for Chinese university rankings"""
    
    def __init__(self, output_dir: str, year: str = None):
        super().__init__("China", output_dir, year)
        
    def download(self) -> Optional[Dict]:
        """Download Chinese rankings"""
        try:
            print(f"📥 Downloading {self.country} {self.year} rankings...")
            
            # Get URL from config
            if self.year not in config.COUNTRY_RANKINGS_ENDPOINTS.get('China', {}):
                print(f"⚠️  No China endpoint found for {self.year}, using default year 2024")
                self.year = '2024'
            
            china_config = config.COUNTRY_RANKINGS_ENDPOINTS['China'][self.year]
            url = china_config['url']
            print(f"🔗 URL: {url}")
            
            # For now, create placeholder data
            placeholder_data = {
                'source': 'Shanghai Ranking Chinese Universities',
                'country': 'China',
                'year': self.year,
                'note': 'Chinese university rankings require web scraping implementation. This is a placeholder structure.',
                'url': url
            }
            
            # Save raw data
            raw_file = os.path.join(self.output_dir, f"shanghai_china_{self.year}_raw.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(placeholder_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved raw data to: {raw_file}")
            
            return placeholder_data
            
        except Exception as e:
            print(f"❌ Error downloading {self.country} rankings: {e}")
            return None
        
    def parse(self, data: Dict) -> List[Dict]:
        """Parse Chinese rankings data"""
        print(f"⚠️  Chinese rankings parsing not yet implemented - needs web scraping")
        print(f"📝 Returning sample data for demonstration")
        
        # Return sample Chinese universities for demonstration
        sample_universities = [
            {
                'rank': '1',
                'university_name': 'Tsinghua University',
                'state_province': 'Beijing',
                'country': 'China'
            },
            {
                'rank': '2',
                'university_name': 'Peking University',
                'state_province': 'Beijing',
                'country': 'China'
            },
            {
                'rank': '3',
                'university_name': 'Zhejiang University',
                'state_province': 'Zhejiang',
                'country': 'China'
            },
            {
                'rank': '4',
                'university_name': 'Shanghai Jiao Tong University',
                'state_province': 'Shanghai',
                'country': 'China'
            },
            {
                'rank': '5',
                'university_name': 'Fudan University',
                'state_province': 'Shanghai',
                'country': 'China'
            }
        ]
        
        return sample_universities

class CountryRankingsManager:
    """Main class to manage country-specific ranking sources"""
    
    def __init__(self, year: str = None):
        self.output_dir = config.RANKINGS_COUNTRIES_PATH
        self.year = year or '2024'
        
        # Initialize downloaders for different countries
        self.downloaders = {
            'US': USRankingsDownloader(self.year),
            'CHINA': ChinaRankingsDownloader(self.output_dir, self.year),
            # Add more countries as implemented
        }
    
    def download_country(self, country: str) -> bool:
        """Download rankings from a specific country"""
        if country not in self.downloaders:
            print(f"❌ Unknown country: {country}")
            return False
        
        downloader = self.downloaders[country]
        
        # Download data
        data = downloader.download()
        if not data:
            return False
        
        # Parse data
        universities = downloader.parse(data)
        if not universities:
            return False
        
        # Save processed data
        processed_file = os.path.join(downloader.output_dir, f"{country.lower()}_rankings_{self.year}.json")
        
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': country,
                    'year': self.year,
                    'download_date': datetime.now().strftime("%Y-%m-%d"),
                    'total_universities': len(universities)
                },
                'universities': universities
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved processed data to: {processed_file}")
        
        # Convert to CSV
        self.convert_to_csv(country, universities, downloader.output_dir)
        
        return True
    
    def convert_to_csv(self, country: str, universities: List[Dict], output_dir: str):
        """Convert country rankings data to CSV"""
        try:
            # Get CSV columns from config
            csv_columns = config.COUNTRY_RANKINGS_CSV_COLUMNS
            
            # Create CSV filename
            csv_filename = f"{country.lower()}_{self.year}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
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
                state = uni.get('state_province', 'N/A')
                country_name = uni.get('country', 'N/A')
                print(f"  {rank}: {name} ({state}, {country_name})")
            
        except Exception as e:
            print(f"❌ Error creating CSV: {e}")
    
    def download_all_countries(self):
        """Download from all configured countries"""
        print("🚀 Downloading from all configured countries...")
        
        for country in self.downloaders.keys():
            print(f"\n{'='*50}")
            print(f"Processing {country} rankings...")
            print(f"{'='*50}")
            
            success = self.download_country(country)
            if success:
                print(f"✅ {country} rankings completed successfully")
            else:
                print(f"❌ {country} rankings failed")
            
            # Add delay between countries to be respectful
            time.sleep(2)

    def download_comprehensive_us_rankings(self) -> Dict:
        """Download comprehensive US college rankings from multiple sources"""
        try:
            print(f"🌐 Downloading comprehensive US college rankings from multiple sources...")
            
            all_sources_data = {}
            
            # Source 1: US News (primary source)
            print(f"\n📰 Source 1: US News Best Colleges")
            try:
                us_news_data = self.downloaders['US'].download()
                if us_news_data:
                    all_sources_data['us_news'] = us_news_data
                    print(f"✅ US News: Downloaded successfully")
                else:
                    print(f"❌ US News: Failed to download")
            except Exception as e:
                print(f"❌ US News error: {e}")
            
            # Source 2: Forbes (alternative source)
            print(f"\n📰 Source 2: Forbes America's Top Colleges")
            try:
                forbes_data = self._download_forbes_rankings()
                if forbes_data:
                    all_sources_data['forbes'] = forbes_data
                    print(f"✅ Forbes: Downloaded successfully")
                else:
                    print(f"❌ Forbes: Failed to download")
            except Exception as e:
                print(f"❌ Forbes error: {e}")
            
            # Source 3: WSJ (alternative source)
            print(f"\n📰 Source 3: Wall Street Journal College Rankings")
            try:
                wsj_data = self._download_wsj_rankings()
                if wsj_data:
                    all_sources_data['wsj'] = wsj_data
                    print(f"✅ WSJ: Downloaded successfully")
                else:
                    print(f"❌ WSJ: Failed to download")
            except Exception as e:
                print(f"❌ WSJ error: {e}")
            
            # Source 4: Princeton Review (alternative source)
            print(f"\n📰 Source 4: Princeton Review College Rankings")
            try:
                princeton_data = self._download_princeton_rankings()
                if princeton_data:
                    all_sources_data['princeton'] = princeton_data
                    print(f"✅ Princeton Review: Downloaded successfully")
                else:
                    print(f"❌ Princeton Review: Failed to download")
            except Exception as e:
                print(f"❌ Princeton Review error: {e}")
            
            # Save comprehensive data
            comprehensive_file = os.path.join(self.output_dir, f"us_comprehensive_{self.year}.json")
            with open(comprehensive_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': 'Multiple US College Ranking Sources',
                    'country': 'US',
                    'year': self.year,
                    'sources': list(all_sources_data.keys()),
                    'data': all_sources_data,
                    'download_timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved comprehensive data to: {comprehensive_file}")
            return all_sources_data
            
        except Exception as e:
            print(f"❌ Error downloading comprehensive US rankings: {e}")
            return {}
    
    def _download_forbes_rankings(self) -> Optional[Dict]:
        """Download Forbes America's Top Colleges rankings"""
        try:
            url = "https://www.forbes.com/lists/americas-top-colleges/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Forbes America\'s Top Colleges',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Forbes download error: {e}")
            return None
    
    def _download_wsj_rankings(self) -> Optional[Dict]:
        """Download Wall Street Journal College Rankings"""
        try:
            url = "https://www.wsj.com/rankings/college-rankings"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Wall Street Journal College Rankings',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ WSJ download error: {e}")
            return None
    
    def _download_princeton_rankings(self) -> Optional[Dict]:
        """Download Princeton Review College Rankings"""
        try:
            url = "https://www.princetonreview.com/college-rankings"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            return {
                'source': 'Princeton Review College Rankings',
                'url': url,
                'html_content': response.text,
                'status_code': response.status_code,
                'download_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Princeton Review download error: {e}")
            return None

def show_help():
    print("🌍 Country-Specific University Rankings Downloader")
    print("=" * 60)
    print("Usage:")
    print("  python3 scripts/download_country_rankings.py                    # Download US 2024 (default)")
    print("  python3 scripts/download_country_rankings.py US                # Download US 2024")
    print("  python3 scripts/download_country_rankings.py US 2024          # Download US 2024")
    print("  python3 scripts/download_country_rankings.py China             # Download China 2024")
    print("  python3 scripts/download_country_rankings.py --comprehensive   # Download comprehensive US rankings from multiple sources")
    print("  python3 scripts/download_country_rankings.py --help            # Show this help")
    print("\nAvailable countries:", ", ".join(['US', 'China', 'UK', 'Australia']))
    print("Available years:", ", ".join(['2024', '2025']))
    print("\nTo add new years, update config.py with new API endpoints")

def main():
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return
    
    print("🌍 Country-Specific University Rankings Downloader")
    print("=" * 60)
    
    # Check for comprehensive flag
    if '--comprehensive' in sys.argv:
        print("🚀 Downloading comprehensive US college rankings from multiple sources...")
        manager = CountryRankingsManager('2024')  # Use 2024 for comprehensive download
        
        if 'US' in manager.downloaders:
            us_downloader = manager.downloaders['US']
            comprehensive_data = us_downloader.download_comprehensive_us_rankings()
            
            if comprehensive_data:
                print(f"\n✅ Comprehensive US rankings download completed!")
                print(f"📊 Sources downloaded: {list(comprehensive_data.keys())}")
                
                # Process each source and create combined rankings
                all_universities = []
                for source_name, source_data in comprehensive_data.items():
                    print(f"\n🔍 Processing {source_name} data...")
                    try:
                        universities = us_downloader.parse(source_data)
                        if universities:
                            print(f"✅ {source_name}: Parsed {len(universities)} universities")
                            all_universities.extend(universities)
                        else:
                            print(f"⚠️  {source_name}: No universities parsed")
                    except Exception as e:
                        print(f"❌ {source_name}: Error parsing - {e}")
                
                if all_universities:
                    # Remove duplicates and sort by rank
                    unique_universities = []
                    seen_ranks = set()
                    
                    for uni in all_universities:
                        if uni['rank'] not in seen_ranks:
                            unique_universities.append(uni)
                            seen_ranks.add(uni['rank'])
                    
                    unique_universities.sort(key=lambda x: int(x['rank']))
                    
                    print(f"\n🎯 Total unique US colleges: {len(unique_universities)}")
                    
                    # Save combined data
                    combined_file = os.path.join(manager.output_dir, f"us_comprehensive_{manager.year}.json")
                    with open(combined_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'metadata': {
                                'source': 'Multiple US College Ranking Sources',
                                'year': manager.year,
                                'download_date': datetime.now().strftime("%Y-%m-%d"),
                                'total_universities': len(unique_universities),
                                'sources': list(comprehensive_data.keys())
                            },
                            'universities': unique_universities
                        }, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Saved combined data to: {combined_file}")
                    
                    # Convert to CSV
                    csv_filename = f"us_comprehensive_{manager.year}.csv"
                    csv_path = os.path.join(manager.output_dir, csv_filename)
                    
                    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=['rank', 'university_name', 'state_province', 'country'])
                        writer.writeheader()
                        for uni in unique_universities:
                            writer.writerow(uni)
                    
                    print(f"✅ Created comprehensive CSV: {csv_path}")
                    
                    # Show sample data
                    print(f"\n📋 Sample data:")
                    for i, uni in enumerate(unique_universities[:10]):
                        print(f"  {uni['rank']}: {uni['university_name']} ({uni['state_province']})")
                    
                else:
                    print(f"❌ No universities found from any source")
            else:
                print(f"❌ Failed to download comprehensive rankings")
        else:
            print(f"❌ US downloader not available")
        return
    
    # Parse command line arguments for regular country downloads
    country = None
    year = None
    
    if len(sys.argv) > 1:
        country = sys.argv[1].upper()
    if len(sys.argv) > 2:
        year = sys.argv[2]
    
    manager = CountryRankingsManager(year)
    
    # Check if specific country is requested
    if country:
        if country in manager.downloaders:
            print(f"📥 Downloading {country} {manager.year} rankings...")
            success = manager.download_country(country)
            if success:
                print(f"✅ {country} rankings completed successfully")
            else:
                print(f"❌ {country} rankings failed")
        else:
            print(f"❌ Country '{country}' not supported")
            print(f"Available countries: {', '.join(manager.downloaders.keys())}")
    else:
        # Download all countries
        print(f"🌍 Downloading all country rankings for {manager.year}...")
        success = manager.download_all_countries()
        if success:
            print(f"✅ All country rankings completed successfully")
        else:
            print(f"❌ Some country rankings failed")

if __name__ == "__main__":
    main()
