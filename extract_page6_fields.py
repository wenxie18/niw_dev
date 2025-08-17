#!/usr/bin/env python3
"""
Script to extract all field names from page 6 of the I-140 PDF form.
"""

import fitz  # PyMuPDF

def main():
    pdf_path = "data/forms/i-140.pdf"
    doc = fitz.open(pdf_path)
    
    print("Extracting field names from I-140 PDF, Page 6...")
    print(f"PDF path: {pdf_path}")
    print(f"Total pages: {len(doc)}")
    print()
    
    # Get page 6 (index 5)
    page = doc[5]  # Page 6 (0-indexed)
    
    # Get all form fields (widgets) on this page
    fields = page.widgets()
    
    all_fields = []
    for field in fields:
        position = field.rect
        x0, y0, x1, y1 = position
        x0 = x0 
        y0 = y0 + (y1 - y0) * 3 // 4
        
        all_fields.append(field.field_name)
        print('page: 6, field name: ', field.field_name, (round(x0), round(y0)))
    
    print(f"\nTotal fields on page 6: {len(all_fields)}")
    doc.close()

if __name__ == "__main__":
    main()
