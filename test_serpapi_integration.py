#!/usr/bin/env python3
"""
Test script to verify SerpAPI integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import SERPAPI_KEY, SERPAPI_ENABLED
from scripts.serpapi_helper import SerpAPIClient, get_citing_authors_serpapi_fallback

def test_serpapi_config():
    """Test if SerpAPI is properly configured"""
    print("=== Testing SerpAPI Configuration ===")
    print(f"SERPAPI_ENABLED: {SERPAPI_ENABLED}")
    print(f"SERPAPI_KEY: {'Set' if SERPAPI_KEY and SERPAPI_KEY != 'YOUR_SERPAPI_KEY_HERE' else 'Not set'}")
    
    if not SERPAPI_ENABLED:
        print("❌ SerpAPI is disabled in config")
        return False
        
    if not SERPAPI_KEY or SERPAPI_KEY == 'YOUR_SERPAPI_KEY_HERE':
        print("❌ SerpAPI key not set in config")
        return False
        
    print("✅ SerpAPI configuration looks good")
    return True

def test_serpapi_client():
    """Test SerpAPI client initialization"""
    print("\n=== Testing SerpAPI Client ===")
    
    try:
        client = SerpAPIClient()
        print("✅ SerpAPI client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize SerpAPI client: {str(e)}")
        return False

def test_serpapi_citation_search():
    """Test SerpAPI citation search"""
    print("\n=== Testing SerpAPI Citation Search ===")
    
    if not test_serpapi_config():
        return False
        
    # Test with a known citation ID
    test_cites_id = "11213583859550251514"
    
    try:
        client = SerpAPIClient()
        response = client.search_citations(test_cites_id, max_results=10)
        
        if response:
            print(f"✅ SerpAPI citation search successful")
            print(f"   Found {len(response.get('organic_results', []))} results")
            
            # Test extracting authors
            authors = client.extract_citing_authors_from_response(response)
            print(f"   Extracted {len(authors)} citing authors")
            
            return True
        else:
            print("❌ SerpAPI citation search failed")
            return False
            
    except Exception as e:
        print(f"❌ SerpAPI citation search error: {str(e)}")
        return False

def test_serpapi_fallback_function():
    """Test the fallback function"""
    print("\n=== Testing SerpAPI Fallback Function ===")
    
    if not test_serpapi_config():
        return False
        
    test_cites_id = "11213583859550251514"
    
    try:
        results = get_citing_authors_serpapi_fallback(test_cites_id)
        print(f"✅ SerpAPI fallback function successful")
        print(f"   Found {len(results)} citing authors")
        return True
    except Exception as e:
        print(f"❌ SerpAPI fallback function error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("Starting SerpAPI integration tests...")
    
    tests = [
        ("Configuration", test_serpapi_config),
        ("Client Initialization", test_serpapi_client),
        ("Citation Search", test_serpapi_citation_search),
        ("Fallback Function", test_serpapi_fallback_function),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            success = test_func()
            results[test_name] = success
            print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            print(f"Test crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    # Overall result
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\nTo fix issues:")
        print("1. Make sure you've set your SerpAPI key in config.py")
        print("2. Check that SERPAPI_ENABLED is set to True")
        print("3. Verify your SerpAPI account has sufficient credits")

if __name__ == "__main__":
    main() 