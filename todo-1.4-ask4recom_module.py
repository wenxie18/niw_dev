#!/usr/bin/env python3
"""
Recommendation Request Email Generator
This script generates personalized recommendation request emails using Jinja2 templating.
"""

import os
import re
import json
from jinja2 import Template
import logging
from typing import Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recommendation_email.log'),
        logging.StreamHandler()
    ]
)

def load_template(template_path: str) -> str:
    """Load and convert markdown template to Jinja2 format."""
    try:
        with open(template_path, "r") as file:
            raw_template = file.read()
        
        # Convert template syntax for Jinja2 (replace [VAR] with {{ VAR }})
        jinja_template_text = re.sub(r"\[([A-Z0-9_]+)\]", r"{{ \1 }}", raw_template)
        return jinja_template_text
    except Exception as e:
        logging.error(f"Error loading template: {str(e)}")
        raise

def render_email(template_text: str, data: Dict) -> str:
    """Render email using Jinja2 template and data."""
    try:
        template = Template(template_text)
        return template.render(**data)
    except Exception as e:
        logging.error(f"Error rendering email: {str(e)}")
        raise

def save_email(email_text: str, output_path: str) -> None:
    """Save rendered email to file."""
    try:
        with open(output_path, "w") as out_file:
            out_file.write(email_text)
        logging.info(f"Email saved to: {output_path}")
    except Exception as e:
        logging.error(f"Error saving email: {str(e)}")
        raise

def generate_recommendation_email(
    template_path: str,
    data_path: Optional[str] = None,
    output_path: Optional[str] = None,
    data: Optional[Dict] = None
) -> str:
    """
    Generate a recommendation request email.
    
    Args:
        template_path: Path to the markdown template file
        data_path: Optional path to JSON data file
        output_path: Optional path to save the rendered email
        data: Optional dictionary containing template variables
    
    Returns:
        str: The rendered email text
    """
    try:
        # Load template
        template_text = load_template(template_path)
        
        # Load data if path is provided
        if data_path and not data:
            with open(data_path, 'r') as f:
                data = json.load(f)
        
        # Render email
        email_text = render_email(template_text, data)
        
        # Save email if output path is provided
        if output_path:
            save_email(email_text, output_path)
        
        return email_text
        
    except Exception as e:
        logging.error(f"Error generating recommendation email: {str(e)}")
        raise

def main():
    """Main function to demonstrate usage."""
    # Example data
    mock_data = {
        "PERSONAL_FULL_NAME": "Yuan Zi",
        "PERSONAL_FIRST_NAME": "Yuan",
        "PERSONAL_LAST_NAME": "Zi",
        "EDU_DEGREE_2": "Ph.D.",
        "EDU_UNIVERSITY_2": "University of Houston",
        "MENTOR_1_NAME": "Jiefu Chen and Zhu Han",
        "CURRENT_POSITION": "Research Scientist",
        "CURRENT_COMPANY": "Gowell International",
        "RESEARCH_FIELD_PRIMARY": "electromagnetic (EM) well-logging",
        "INDUSTRY_APPLICATION": "well-integrity monitoring",
        "NATIONAL_PRIORITY_AREAS": "environmental monitoring and sustainability",
        "PUBLICATION_1": """Jin, Y., Zi, Y., Hu, W., Hu, Y., Wu, X., Chen, J., 2022. A Robust Learning Method for Low-Frequency Extrapolation in GPR Full Waveform Inversion, IEEE Geosci. Remote Sens. Lett., 19, 1–5.
Jin, Y., Hu, W., Wang, S., Zi, Y., Wu, X., Chen, J., 2022. Efficient Progressive Transfer Learning for Full-Waveform Inversion with Extrapolated Low-Frequency Reflection Seismic Data, IEEE Trans. Geosci. Remote Sens., vol. 60, pp. 1-10.""",
        "RECOMMENDER_LAST_NAME": "Demanet",
        "RECOMMENDER_FIELD": "AI in geophysics",
        "RECOMMENDER_PAPER_TITLE": "Learning with Real Data Without Real Labels: A Strategy for Extrapolated Full-Waveform Inversion with Field Data",
        "RECOMMENDER_RESEARCH_FOCUS": "leveraging low-frequency extrapolation for FWI",
        "RECOMMENDER_EXPERTISE": "AI for geophysics"
    }
    
    # Example usage
    template_path = "ask_rec_email_template.md"  # Update this path
    output_path = "rendered_email.txt"
    
    try:
        email_text = generate_recommendation_email(
            template_path=template_path,
            data=mock_data,
            output_path=output_path
        )
        print("\nGenerated Email:")
        print(email_text)
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main() 