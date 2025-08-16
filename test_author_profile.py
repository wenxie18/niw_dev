#!/usr/bin/env python3
"""
Test script to examine Google Scholar author profile structure via SerpAPI
"""

import json
import sys
import os
sys.path.append('scripts')

from serpapi_helper import SerpAPIClient
from config import SERPAPI_KEY

def test_author_profile():
    """Test SerpAPI author profile structure"""
    
    if not SERPAPI_KEY:
        print("No SerpAPI API key found in config.py")
        return
    
    # Test with one of the author IDs we found in the previous test
    test_author_id = "aiHz0J4AAAAJ"  # G Overgoor from the previous test
    
    client = SerpAPIClient(SERPAPI_KEY)
    
    print(f"Testing SerpAPI author profile with author_id: {test_author_id}")
    print("=" * 60)
    
    # Get the author profile
    response = client.get_author_profile(test_author_id)
    
    if response:
        print("Raw SerpAPI Author Profile Response Structure:")
        print(json.dumps(response, indent=2, default=str))
        print("\n" + "=" * 60)
        
        # Check what fields are available
        print("Available top-level keys:")
        for key in response.keys():
            print(f"  - {key}")
        
        # Look for affiliation-related fields
        print("\nLooking for affiliation information:")
        
        # Check common affiliation field names
        affiliation_fields = ['affiliation', 'organization', 'institution', 'university', 'department']
        for field in affiliation_fields:
            if field in response:
                print(f"  Found '{field}': {response[field]}")
        
        # Also check if there are any nested structures that might contain affiliation
        if 'author' in response:
            author_info = response['author']
            print(f"\nAuthor info structure:")
            print(json.dumps(author_info, indent=2, default=str))
            
            # Check for affiliation in author info
            for field in affiliation_fields:
                if field in author_info:
                    print(f"  Found '{field}' in author info: {author_info[field]}")
        
        # Test the extraction function
        print("\n" + "=" * 60)
        print("Testing affiliation extraction function:")
        affiliation = client.extract_author_affiliation_from_response(response)
        if affiliation:
            print(f"Extracted affiliation: {affiliation}")
        else:
            print("No affiliation extracted")
            
    else:
        print("Failed to get author profile from SerpAPI")

if __name__ == "__main__":
    test_author_profile() 