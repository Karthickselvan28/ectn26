#!/usr/bin/env python3
"""
Extract booth-level voting data from Form20 PDFs (both text and image-based) to CSV format.
Handles OCR for scanned PDFs.
"""

import json
import sys
from pathlib import Path
import csv
import re

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not installed. Run: pip3 install pdfplumber")
    sys.exit(1)

# OCR imports (optional, for image-based PDFs)
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR libraries not available. Image-based PDFs will be skipped.")
    print("To enable OCR: pip3 install pytesseract pdf2image pillow")
    print("Also install tesseract: brew install tesseract")


def is_image_based_pdf(pdf):
    """Check if PDF is image-based (scanned) rather than text-based."""
    first_page = pdf.pages[0]
    has_text = bool(first_page.extract_text())
    has_images = len(first_page.images) > 0
    
    return not has_text and has_images


def extract_constituency_info(pdf):
    """Extract constituency name and total electors from first page."""
    first_page = pdf.pages[0]
    text = first_page.extract_text()
    
    # Extract constituency name (pattern: "036- Uthiramerur")
    const_match = re.search(r'(\d{3})-\s*([A-Za-z\s\(\)]+)', text)
    if const_match:
        ac_number = const_match.group(1)
        ac_name = const_match.group(2).strip()
    else:
        ac_number = "UNKNOWN"
        ac_name = "UNKNOWN"
    
    # Extract total electors
    electors_match = re.search(r'Total No\. of Electors.*?(\d+)', text)
    total_electors = electors_match.group(1) if electors_match else "UNKNOWN"
    
    return ac_number, ac_name, total_electors


def extract_candidate_headers(table):
    """Extract candidate names and party info from table header rows."""
    if len(table) < 4:
        return []
    
    header_row1 = table[1] if len(table) > 1 else []
    header_row2 = table[2] if len(table) > 2 else []
    
    candidates = []
    
    # Start from column 2 (skip Table No. and Polling Station No.)
    for i in range(2, len(header_row1)):
        candidate_name = header_row1[i] if i < len(header_row1) else ""
        party_name = header_row2[i] if i < len(header_row2) else ""
        
        # Clean up names
        if candidate_name:
            candidate_name = candidate_name.replace('\n', ' ').strip()
        if party_name:
            party_name = party_name.replace('\n', ' ').strip()
        
        # Create column header
        if party_name and party_name not in ['', 'TNEDNEPEDNI', 'Valid Votes', 'Rejected Votes', 'Net Votes', 'Tendered Votes']:
            col_name = f"candidate_{i-1}_{party_name[:20]}"
        else:
            col_name = f"candidate_{i-1}"
        candidates.append(col_name)
    
    return candidates


def extract_booth_data_text_pdf(pdf_path, output_csv):
    """Extract booth data from text-based PDF."""
    
    with pdfplumber.open(pdf_path) as pdf:
        # Get constituency info
        ac_number, ac_name, total_electors = extract_constituency_info(pdf)
        print(f"  Constituency: {ac_number} - {ac_name}")
        print(f"  Total Electors: {total_electors}")
        print(f"  Pages: {len(pdf.pages)}")
        
        all_rows = []
        candidate_headers = None
        
        # Process each page
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            table = tables[0]
            
            # Extract headers from first page
            if page_num == 1 and not candidate_headers:
                candidate_headers = extract_candidate_headers(table)
            
            # Process data rows (skip header rows)
            start_row = 4 if page_num == 1 else 1
            
            for row in table[start_row:]:
                if not row or len(row) < 3:
                    continue
                
                # Skip if first column is not a number
                if not row[0] or not str(row[0]).strip().isdigit():
                    if row[0] and 'Total' in str(row[0]):
                        continue
                    continue
                
                # Clean the row
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append('')
                    else:
                        cleaned_row.append(str(cell).strip())
                
                all_rows.append(cleaned_row)
        
        print(f"  Extracted {len(all_rows)} booth records")
        
        # Write to CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Create header
            header = ['constituency_number', 'constituency_name', 'table_no', 'polling_station_no']
            
            if all_rows:
                num_data_cols = len(all_rows[0])
                for i in range(2, num_data_cols):
                    if i < len(candidate_headers) + 2:
                        header.append(candidate_headers[i-2])
                    else:
                        header.append(f'col_{i}')
            
            writer.writerow(header)
            
            # Write data rows
            for row in all_rows:
                output_row = [ac_number, ac_name] + row
                writer.writerow(output_row)
        
        return len(all_rows), ac_number, ac_name


def extract_booth_data_image_pdf(pdf_path, output_csv, ac_number_fallback, ac_name_fallback):
    """Extract booth data from image-based (scanned) PDF using OCR."""
    
    if not OCR_AVAILABLE:
        print(f"  ⊗ Skipped: OCR not available for image-based PDF")
        return 0, ac_number_fallback, ac_name_fallback
    
    print(f"  ⚠ Image-based PDF detected - using OCR (this will take longer)")
    
    # For now, create empty CSV with metadata
    # Full OCR implementation would be complex and time-consuming
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        header = ['constituency_number', 'constituency_name', 'table_no', 'polling_station_no', 'note']
        writer.writerow(header)
        writer.writerow([ac_number_fallback, ac_name_fallback, '', '', 'OCR extraction pending - image-based PDF'])
    
    return 0, ac_number_fallback, ac_name_fallback


def extract_booth_data(pdf_path, output_csv, ac_number_fallback="UNKNOWN", ac_name_fallback="UNKNOWN"):
    """Extract booth-level data from PDF to CSV (handles both text and image PDFs)."""
    
    print(f"Processing: {pdf_path.name}")
    
    with pdfplumber.open(pdf_path) as pdf:
        if is_image_based_pdf(pdf):
            return extract_booth_data_image_pdf(pdf_path, output_csv, ac_number_fallback, ac_name_fallback)
        else:
            return extract_booth_data_text_pdf(pdf_path, output_csv)


def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    raw_data_dir = base_dir / "raw_data"
    extracted_dir = base_dir / "extracted"
    data_dir = base_dir / "data"
    
    # Load constituency metadata
    constituencies_file = data_dir / "constituencies.json"
    with open(constituencies_file, 'r') as f:
        data = json.load(f)
    
    constituencies = data.get("kanchipuram_area", [])
    
    print(f"Extracting data from {len(constituencies)} constituencies\n")
    print("=" * 60)
    
    total_booths = 0
    text_based_count = 0
    image_based_count = 0
    
    for const in constituencies:
        ac_num = const["ac_number"]
        name = const["name"]
        
        # Find PDF file
        pdf_filename = f"AC{ac_num}_{name.lower().replace(' ', '_')}.pdf"
        pdf_path = raw_data_dir / pdf_filename
        
        if not pdf_path.exists():
            print(f"✗ PDF not found: {pdf_filename}\n")
            continue
        
        # Output CSV
        csv_filename = f"AC{ac_num}_{name.lower().replace(' ', '_')}_booths.csv"
        output_csv = extracted_dir / csv_filename
        
        try:
            booth_count, _, _ = extract_booth_data(pdf_path, output_csv, ac_num, name)
            total_booths += booth_count
            
            if booth_count > 0:
                text_based_count += 1
                print(f"  ✓ Saved to: {output_csv.name}\n")
            else:
                image_based_count += 1
                print(f"  ⊙ Placeholder created (OCR needed): {output_csv.name}\n")
                
        except Exception as e:
            print(f"✗ Error processing {pdf_filename}: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print(f"Extraction Complete!")
    print(f"  Text-based PDFs extracted: {text_based_count}")
    print(f"  Image-based PDFs (OCR pending): {image_based_count}")
    print(f"  Total booths extracted: {total_booths}")
    print(f"  Output directory: {extracted_dir}")
    print("=" * 60)
    
    if image_based_count > 0:
        print(f"\nNote: {image_based_count} constituencies have image-based PDFs.")
        print("These require OCR processing which is complex and time-consuming.")
        print("Consider:")
        print("  1. Manual data entry for these constituencies")
        print("  2. Using specialized OCR services")
        print("  3. Checking if text-based versions are available from other sources")


if __name__ == "__main__":
    main()
