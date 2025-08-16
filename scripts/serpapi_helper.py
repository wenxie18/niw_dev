"""
SerpAPI Helper Module for Google Scholar searches
Provides fallback functionality when direct scraping fails
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
from config import SERPAPI_KEY, SERPAPI_ENABLED

logger = logging.getLogger(__name__)

class SerpAPIClient:
    """Client for SerpAPI Google Scholar searches"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or SERPAPI_KEY
        self.base_url = "https://serpapi.com/search"
        
    def search_citations(self, cites_id: str, max_results: int = 100) -> Optional[Dict]:
        """
        Search for citations using SerpAPI
        
        Args:
            cites_id: Google Scholar citation ID
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with citation results or None if failed
        """
        if not SERPAPI_ENABLED or not self.api_key:
            logger.warning("SerpAPI is disabled or no API key provided")
            return None
            
        try:
            params = {
                "engine": "google_scholar",
                "cites": cites_id,
                "api_key": self.api_key,
                "num": min(max_results, 100),  # SerpAPI max is 100
                "hl": "en"
            }
            
            logger.info(f"Searching citations via SerpAPI for cites_id: {cites_id}")
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SerpAPI search successful, found {len(data.get('organic_results', []))} results")
                return data
            else:
                logger.error(f"SerpAPI request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"SerpAPI search failed: {str(e)}")
            return None
    
    def get_author_profile(self, scholar_id: str) -> Optional[Dict]:
        """
        Get author profile using SerpAPI
        
        Args:
            scholar_id: Google Scholar author ID
            
        Returns:
            Dictionary with author profile or None if failed
        """
        if not SERPAPI_ENABLED or not self.api_key:
            logger.warning("SerpAPI is disabled or no API key provided")
            return None
            
        try:
            params = {
                "engine": "google_scholar_author",
                "author_id": scholar_id,
                "api_key": self.api_key,
                "hl": "en"
            }
            
            logger.info(f"Getting author profile via SerpAPI for scholar_id: {scholar_id}")
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SerpAPI author profile successful")
                return data
            else:
                logger.error(f"SerpAPI author profile request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"SerpAPI author profile failed: {str(e)}")
            return None
    
    def extract_citing_authors_from_response(self, serpapi_response: Dict) -> List[Tuple[str, Dict]]:
        """
        Extract citing authors from SerpAPI response
        
        Args:
            serpapi_response: Response from SerpAPI citation search
            
        Returns:
            List of tuples (author_id, paper_info)
        """
        citing_authors = []
        
        if not serpapi_response or 'organic_results' not in serpapi_response:
            return citing_authors
            
        for result in serpapi_response['organic_results']:
            try:
                # Extract author information from each citing paper
                title = result.get('title', 'Unknown Title')
                
                # Look for authors in publication_info.authors
                publication_info = result.get('publication_info', {})
                authors = publication_info.get('authors', [])
                
                for author in authors:
                    if isinstance(author, dict):
                        author_id = author.get('author_id')
                        author_name = author.get('name', 'Unknown Author')
                        
                        if author_id:
                            paper_info = {
                                'author': author_name,
                                'title': title
                            }
                            citing_authors.append((author_id, paper_info))
                        
            except Exception as e:
                logger.warning(f"Error extracting author from result: {str(e)}")
                continue
                
        logger.info(f"Extracted {len(citing_authors)} citing authors from SerpAPI response")
        return citing_authors
    
    def extract_author_affiliation_from_response(self, serpapi_response: Dict) -> Optional[str]:
        """
        Extract author affiliation from SerpAPI author profile response
        
        Args:
            serpapi_response: Response from SerpAPI author profile search
            
        Returns:
            Affiliation string or None
        """
        if not serpapi_response:
            return None
            
        try:
            # Check if there's an author section
            if 'author' in serpapi_response:
                author_info = serpapi_response['author']
                
                # Try different possible field names for affiliation in author info
                affiliation = (
                    author_info.get('affiliations') or  # Plural - this is what SerpAPI uses
                    author_info.get('affiliation') or   # Singular - fallback
                    author_info.get('organization') or
                    author_info.get('institution')
                )
                
                if affiliation:
                    logger.info(f"Found affiliation via SerpAPI: {affiliation}")
                    return affiliation
            
            # Also try top-level fields as fallback
            affiliation = (
                serpapi_response.get('affiliation') or
                serpapi_response.get('organization') or
                serpapi_response.get('institution')
            )
            
            if affiliation:
                logger.info(f"Found affiliation via SerpAPI (top-level): {affiliation}")
                return affiliation
                
        except Exception as e:
            logger.warning(f"Error extracting affiliation from SerpAPI response: {str(e)}")
            
        return None

# Global SerpAPI client instance
serpapi_client = SerpAPIClient()

def get_citing_authors_serpapi_fallback(cites_id: str) -> List[Tuple[str, Dict]]:
    """
    Fallback function to get citing authors using SerpAPI
    
    Args:
        cites_id: Google Scholar citation ID
        
    Returns:
        List of tuples (author_id, paper_info)
    """
    logger.info(f"Attempting SerpAPI fallback for cites_id: {cites_id}")
    
    # Add delay to respect rate limits
    time.sleep(2)
    
    response = serpapi_client.search_citations(cites_id)
    if response:
        return serpapi_client.extract_citing_authors_from_response(response)
    else:
        logger.warning("SerpAPI fallback failed")
        return []

def get_author_affiliation_serpapi_fallback(scholar_id: str) -> Optional[str]:
    """
    Fallback function to get author affiliation using SerpAPI
    
    Args:
        scholar_id: Google Scholar author ID
        
    Returns:
        Affiliation string or None
    """
    logger.info(f"Attempting SerpAPI fallback for author affiliation: {scholar_id}")
    
    # Add delay to respect rate limits
    time.sleep(1)
    
    response = serpapi_client.get_author_profile(scholar_id)
    if response:
        return serpapi_client.extract_author_affiliation_from_response(response)
    else:
        logger.warning("SerpAPI author profile fallback failed")
        return None 