from geopy.geocoders import GoogleV3
import time

# Your API key
api_key = 'AIzaSyDx4DZ734PQXD-_aoIUhPqrPsXioE_ZrlM'

def test_geocoding():
    print("Testing Google Maps Geocoding API...")
    
    # Initialize the geocoder
    geolocator = GoogleV3(api_key=api_key)
    
    # Test with a simple address
    test_location = "MIT"
    print(f"\nTrying to geocode: {test_location}")
    
    try:
        location = geolocator.geocode(test_location)
        if location:
            print("Success! Location found:")
            print(f"Address: {location.address}")
            print(f"Latitude: {location.latitude}")
            print(f"Longitude: {location.longitude}")
        else:
            print("No location found")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_geocoding() 