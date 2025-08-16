import os
import shutil
from PyPDF2 import PdfReader, PdfWriter
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_pages.log'),
        logging.StreamHandler()
    ]
)

def extract_pages(pdf_path, page_numbers):
    """Extract specified pages from a PDF and save them to a new file."""
    try:
        # Create temporary output path
        temp_output_path = pdf_path + '.temp'
        
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create a PDF reader object
            reader = PdfReader(file)
            
            # Check if the PDF has enough pages
            if len(reader.pages) < max(page_numbers):
                logging.warning(f"PDF {pdf_path} has fewer pages than requested")
                return False
            
            # Create a PDF writer object
            writer = PdfWriter()
            
            # Add the specified pages to the writer
            for page_num in page_numbers:
                if page_num <= len(reader.pages):
                    writer.add_page(reader.pages[page_num - 1])
                else:
                    logging.warning(f"Page {page_num} not found in {pdf_path}")
            
            # Write the pages to a temporary PDF file
            with open(temp_output_path, 'wb') as output_file:
                writer.write(output_file)
            
            # Replace original file with the new version
            shutil.move(temp_output_path, pdf_path)
            
            return True
            
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {str(e)}")
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        return False

def process_pdf(pdf_path, page_numbers):
    """Process a single PDF file."""
    logging.info(f"Starting page extraction for: {pdf_path}")
    
    if extract_pages(pdf_path, page_numbers):
        logging.info(f"Successfully extracted pages {page_numbers} from {pdf_path}")
        return True
    else:
        logging.error(f"Failed to extract pages from {pdf_path}")
        return False

if __name__ == '__main__':
    # Example usage:
    pdf_path = 'Exhibit10.pdf'  # Replace with actual PDF path
    page_numbers = [1, 5, 13]  # Replace with desired page numbers to extract
    
    logging.info("Starting page extraction process")
    process_pdf(pdf_path, page_numbers)
    logging.info("Page extraction process completed")