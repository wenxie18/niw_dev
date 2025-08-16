import json
import os
import logging
from pathlib import Path
import re
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PetitionLetterGenerator:
    def __init__(self, template_path: str, json_path: str, output_path: str, latex_template_path: str):
        self.template_path = template_path
        self.json_path = json_path
        self.output_path = output_path
        self.latex_template_path = latex_template_path

    def load_json_data(self) -> dict:
        """Load and validate JSON data."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info("Successfully loaded JSON data")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise
        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.json_path}")
            raise

    def check_missing_variables(self, template_content: str, data: dict) -> list:
        """Check for missing variables in the template."""
        try:
            # Extract variables using regex
            template_vars = set(re.findall(r'\[([A-Z0-9_]+)\]', template_content))
            
            # Get all available variables from data
            json_vars = set(data.keys())
            
            # Find missing variables
            missing_vars = template_vars - json_vars
            if missing_vars:
                logger.warning(f"Missing variables in JSON: {missing_vars}")
            return list(missing_vars)
            
        except Exception as e:
            logger.error(f"Error checking variables: {str(e)}")
            return []

    def escape_latex(self, value: str) -> str:
        """Escape special LaTeX characters and ensure proper command closure."""
        if not isinstance(value, str):
            return str(value)

        # Define LaTeX special characters and their escaped versions
        special_chars = {
            '&': '\&',
            '%': '\%',
            '$': '\$',
            '#': '\#',
            '_': '\_',
            '{': '\{',
            '}': '\}',
            '~': '\~',
            '^': '\^',   
            '<': '\<',
            '>': '\>',
            '|': '\|',
            '"': '``',  # Opening quotes
            "'": "'",
            '``': '``',  # Keep existing LaTeX quotes
            "''": "''"   # Keep existing LaTeX quotes
        }

        # Replace special characters
        for char, escape in special_chars.items():
            value = value.replace(char, escape)

        # Handle LaTeX commands properly
        value = re.sub(r'\\textit\s+', r'\\textit{', value)
        value = re.sub(r'\\textbf\s+', r'\\textbf{', value)
        value = re.sub(r'\\emph\s+', r'\\emph{', value)

        # Ensure proper command closure
        open_braces = value.count('{')
        close_braces = value.count('}')
        if open_braces > close_braces:
            value += '}' * (open_braces - close_braces)

        return value

    def generate_letter(self) -> bool:
        """Generate the petition letter."""
        try:
            # Load and validate data
            data = self.load_json_data()
            
            # Read template content
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Check for missing variables
            missing_vars = self.check_missing_variables(template_content, data)
            if missing_vars:
                logger.warning("Proceeding with missing variables")
            
            # Replace variables in template
            for key, value in data.items():
                if isinstance(value, str):
                    value = self.escape_latex(value)
                template_content = template_content.replace(f"[{key}]", str(value))
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            # Write output
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            logger.info(f"Successfully generated petition letter at {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating petition letter: {str(e)}")
            return False

    def generate_latex_file(self) -> bool:
        """Generate the final LaTeX file by replacing [MAINBODY] in the template."""
        try:
            # Read the generated petition letter
            with open(self.output_path, 'r', encoding='utf-8') as f:
                petition_content = f.read()

            # Read the LaTeX template
            with open(self.latex_template_path, 'r', encoding='utf-8') as f:
                latex_template = f.read()

            # Replace [MAINBODY] with the petition content
            latex_content = latex_template.replace('[MAINBODY]', petition_content)

            # Create output path for LaTeX file
            latex_output_path = os.path.join(
                os.path.dirname(self.output_path),
                'generated_main.tex'
            )

            # Write the final LaTeX file
            with open(latex_output_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)

            logger.info(f"Successfully generated LaTeX file at {latex_output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating LaTeX file: {str(e)}")
            return False

def main():
    # Define paths
    base_dir = Path(__file__).parent
    template_path = os.path.join(config.FOLDER_PATH, 'petition_letter_breakdown_basic_basic.md') 
    # json_path = base_dir / "data_collections_basic_basic_petition_letter.json"
    json_path = os.path.join(config.OUTPUT_BASE_FOLDER, config.DEFAULT_EMAIL, 'survey_answers.json')  
    output_path = os.path.join(config.OUTPUT_BASE_FOLDER, config.DEFAULT_EMAIL, 'generated_petition_letter.md')  
    latex_template_path = os.path.join(config.FOLDER_PATH, 'main_static.tex') 
    
    # Create generator instance
    generator = PetitionLetterGenerator(
        template_path=str(template_path),
        json_path=str(json_path),
        output_path=str(output_path),
        latex_template_path=str(latex_template_path)
    )
    
    # Generate letter
    success = generator.generate_letter()
    
    if success:
        logger.info("Petition letter generation completed successfully")
        
        # Generate LaTeX file
        latex_success = generator.generate_latex_file()
        if latex_success:
            logger.info("LaTeX file generation completed successfully")
        else:
            logger.error("LaTeX file generation failed")
    else:
        logger.error("Petition letter generation failed")

if __name__ == "__main__":
    main()