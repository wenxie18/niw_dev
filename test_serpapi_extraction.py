#!/usr/bin/env python3
"""
Test script to verify the fixed SerpAPI extraction function
"""

import sys
import os
sys.path.append('scripts')

from serpapi_helper import SerpAPIClient
from config import SERPAPI_KEY

def test_extraction():
    """Test the fixed extraction function"""
    
    if not SERPAPI_KEY:
        print("No SerpAPI API key found in config.py")
        return
    
    # Test with one of the cites_ids from the logs
    test_cites_id = "16849425716422464167"
    
    client = SerpAPIClient(SERPAPI_KEY)
    
    print(f"Testing SerpAPI extraction with cites_id: {test_cites_id}")
    print("=" * 50)
    
    # Get the response
    response = client.search_citations(test_cites_id, max_results=5)
    
    if response:
        # Test the extraction
        citing_authors = client.extract_citing_authors_from_response(response)
        
        print(f"Extracted {len(citing_authors)} citing authors:")
        for i, (author_id, paper_info) in enumerate(citing_authors, 1):
            print(f"  {i}. Author ID: {author_id}")
            print(f"     Name: {paper_info['author']}")
            print(f"     Paper: {paper_info['title']}")
            print()
    else:
        print("Failed to get response from SerpAPI")

if __name__ == "__main__":
    test_extraction() 