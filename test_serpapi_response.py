#!/usr/bin/env python3
"""
Test script to examine SerpAPI response structure for Google Scholar citations
"""

import json
import sys
import os
sys.path.append('scripts')

from scripts.serpapi_helper import SerpAPIClient
from config import SERPAPI_KEY

def test_serpapi_response():
    """Test SerpAPI response structure"""
    
    if not SERPAPI_KEY:
        print("No SerpAPI API key found in config.py")
        return
    
    # Test with one of the cites_ids from the logs
    test_cites_id = "16849425716422464167"
    
    client = SerpAPIClient(SERPAPI_KEY)
    
    print(f"Testing SerpAPI with cites_id: {test_cites_id}")
    print("=" * 50)
    
    # Get the raw response
    response = client.search_citations(test_cites_id, max_results=5)
    
    if response:
        print("Raw SerpAPI Response Structure:")
        print(json.dumps(response, indent=2, default=str))
        print("\n" + "=" * 50)
        
        # Check what fields are available
        print("Available top-level keys:")
        for key in response.keys():
            print(f"  - {key}")
        
        if 'organic_results' in response:
            print(f"\nNumber of organic_results: {len(response['organic_results'])}")
            
            if response['organic_results']:
                print("\nFirst result structure:")
                first_result = response['organic_results'][0]
                print(json.dumps(first_result, indent=2, default=str))
                
                print("\nAvailable keys in first result:")
                for key in first_result.keys():
                    print(f"  - {key}")
        else:
            print("\nNo 'organic_results' found. Available keys:")
            for key in response.keys():
                print(f"  - {key}")
    else:
        print("Failed to get response from SerpAPI")

if __name__ == "__main__":
    test_serpapi_response() 