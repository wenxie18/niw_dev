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
        logging.FileHandler('extract_first_pages.log'),
        logging.StreamHandler()
    ]
)

def create_first_pages_folder(base_folder):
    """Create a folder for storing first pages."""
    first_pages_folder = os.path.join(base_folder, 'first-pages')
    os.makedirs(first_pages_folder, exist_ok=True)
    return first_pages_folder

def extract_first_page(pdf_path, output_path):
    """Extract the first page of a PDF and save it to a new file."""
    try:
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create a PDF reader object
            reader = PdfReader(file)
            
            # Check if the PDF has at least one page
            if len(reader.pages) == 0:
                logging.warning(f"No pages found in {pdf_path}")
                return False
            
            # Create a PDF writer object
            writer = PdfWriter()
            
            # Add the first page to the writer
            writer.add_page(reader.pages[0])
            
            # Write the first page to a new PDF file
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
            
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {str(e)}")
        return False

def process_pdfs(pdfs_folder):
    """Process all PDFs in the given folder."""
    # Create first-pages folder
    first_pages_folder = create_first_pages_folder(pdfs_folder)
    logging.info(f"Created first-pages folder at: {first_pages_folder}")
    
    # Get all PDF files in the folder
    pdf_files = [f for f in os.listdir(pdfs_folder) if f.endswith('.pdf')]
    total_files = len(pdf_files)
    logging.info(f"Found {total_files} PDF files to process")
    
    # Process each PDF file
    success_count = 0
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(pdfs_folder, pdf_file)
        output_path = os.path.join(first_pages_folder, f"first_page_{pdf_file}")
        
        if extract_first_page(pdf_path, output_path):
            success_count += 1
    
    # Print summary
    logging.info("\nExtraction Summary:")
    logging.info(f"Total PDFs processed: {total_files}")
    logging.info(f"Successfully extracted first pages: {success_count}")
    logging.info(f"Failed extractions: {total_files - success_count}")
    logging.info(f"First pages saved to: {first_pages_folder}")

if __name__ == '__main__':
    # Path to the PDFs folder
    pdfs_folder = '/Users/wenxie/Documents/GitHub/niw/filled/vaneshieh@gmail.com/pdfs'
    
    logging.info("Starting first page extraction process")
    process_pdfs(pdfs_folder)
    logging.info("First page extraction process completed") 