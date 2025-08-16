import pandas as pd
import re
import os
import config
import time
import json

def extract_venue_from_citation(citation):
    """
    Extract venue name and type from citation string.
    """
    # Skip empty citations
    if pd.isna(citation) or not citation:
        return None, None
    
    # SSRN working papers
    if "SSRN" in citation:
        return "SSRN", "Working Paper"
    
    # Conference proceedings
    conference_patterns = [
        r'([A-Za-z\s]+Conference)\s*\d+',
        r'([A-Za-z\s]+Proceedings)\s*\d+',
        r'([A-Za-z\s]+Symposium)\s*\d+',
        r'([A-Za-z\s]+Workshop)\s*\d+'
    ]
    
    for pattern in conference_patterns:
        match = re.search(pattern, citation)
        if match:
            return match.group(1).strip(), "Conference"
    
    # Journal articles
    journal_patterns = [
        r'([A-Za-z\s]+)\s*\d+\s*\(\d+\)',  # Journal name with volume and issue
        r'([A-Za-z\s]+)\s*\d+',  # Journal name with volume
        r'([A-Za-z\s]+)\s*,\s*\d+'  # Journal name with year
    ]
    
    for pattern in journal_patterns:
        match = re.search(pattern, citation)
        if match:
            return match.group(1).strip(), "Journal"
    
    # Books
    if "[BOOK]" in citation:
        return citation.split("[BOOK]")[1].strip(), "Book"
    
    return None, None

# def analyze_venue_with_llm(venue_name, venue_type):
#     """
#     Use OpenAI API to analyze venue information.
#     """
#     client = OpenAI()
    
#     prompt = f"""Please analyze the academic venue "{venue_name}" (Type: {venue_type}) and provide the following information in JSON format:
#     1. venue_scope: The scope of the venue (e.g., "International", "Regional", "National")
#     2. venue_field: The main academic field(s) of the venue (e.g., "Computer Science", "Marketing", "Psychology")
#     3. venue_impact_factor: The most recent impact factor if available, or "N/A" if not available
#     4. venue_type: The type of venue (e.g., "Journal", "Conference", "Book", "Working Paper")
#     5. venue_rank: The venue's ranking in its field if available (e.g., "A*", "A", "B", "C" or specific ranking)
    
#     Please provide only the JSON response, no additional text."""

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4-turbo-preview",
#             messages=[
#                 {"role": "system", "content": "You are an expert in academic publishing and venue analysis."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3
#         )
        
#         # Extract JSON from response
#         result = response.choices[0].message.content
#         return json.loads(result)
#     except Exception as e:
#         print(f"Error analyzing venue {venue_name}: {str(e)}")
#         return None

def main():
    # Read the CSV file
    csv_path = os.path.join(config.OUTPUT_BASE_FOLDER, config.DEFAULT_EMAIL, 'citation_info_with_ranks.csv')
    df = pd.read_csv(csv_path)
    
    # Extract unique venues
    venues = {}
    for citation in df['citation']:
        venue_name, venue_type = extract_venue_from_citation(citation)
        if venue_name:
            venues[venue_name] = venue_type
    
    # Print unique venues
    print("\nUnique Venues Found:")
    print("=" * 50)
    for venue, venue_type in venues.items():
        print(f"{venue} ({venue_type})")
    
    # Generate ChatGPT prompt
    print("\nChatGPT Prompt:")
    print("=" * 50)
    print("""Please analyze the following academic venues and provide the information in a JSON format. Each venue info should be a {} line in the json file with the following structure:

{
    "venue_name": "Name of the venue",
    "venue_scope": "International/Regional/National",
    "venue_field": "Main academic field(s)",
    "venue_impact_factor": "Most recent impact factor or N/A",
    "venue_type": "Journal/Conference/Book/Working Paper",
    "venue_rank": "A*/A/B/C or specific ranking"
}

Venues to analyze:
""")
    
    # Save venues to a JSON file
    output_path = os.path.join(config.OUTPUT_BASE_FOLDER, config.DEFAULT_EMAIL, 'venues_to_analyze.json')
    with open(output_path, 'w') as f:
        json.dump(venues, f, indent=2)
    print(f"\nVenues saved to: {output_path}")

if __name__ == "__main__":
    main() 