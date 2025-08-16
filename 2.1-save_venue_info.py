import json
import os
from config import FOLDER_PATH, DEFAULT_EMAIL

def save_venue_info(venue_data):
    # Create the output directory if it doesn't exist
    output_dir = os.path.join(FOLDER_PATH, 'filled', DEFAULT_EMAIL)
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the output file path
    output_file = os.path.join(output_dir, 'venue_info.json')
    
    # Convert array to object with venue names as keys
    venue_object = {}
    for venue in venue_data:
        venue_name = venue["venue_name"]
        venue_object[venue_name] = venue
    
    # Save the data to JSON file
    with open(output_file, 'w') as f:
        json.dump(venue_object, f, indent=2)
    
    print(f"Venue information saved to: {output_file}")

def main():
    # The venue information you provided
    venue_data = [
        {
            "venue_name": "Journal of Advertising",
            "venue_scope": "International",
            "venue_field": "Advertising, Marketing, Communication",
            "venue_impact_factor": "5.4",
            "venue_type": "Journal",
            "venue_rank": "Q1"
        },
        {
            "venue_name": "AMA Winter Academic Conference",
            "venue_scope": "International",
            "venue_field": "Marketing, Business, Consumer Behavior",
            "venue_impact_factor": "N/A",
            "venue_type": "Conference",
            "venue_rank": "A"
        }
    ]
    
    save_venue_info(venue_data)

if __name__ == "__main__":
    main() 