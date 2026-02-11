#!/usr/bin/env python3
import pdfplumber
import csv
import re
import os
from pathlib import Path

def extract_constituency_info(pdf):
    first_page = pdf.pages[0]
    text = first_page.extract_text()
    
    # Extract constituency name (pattern: "036-UTHIRAMERUR" or similar)
    const_match = re.search(r'(\d{3})-([A-Za-z\s\(\)]+)', text)
    if const_match:
        ac_number = const_match.group(1)
        # Just take the first word or line as the name to avoid capturing candidate list
        ac_name = const_match.group(2).strip().split('\n')[0].strip()
    else:
        ac_number = "UNKNOWN"
        ac_name = "UNKNOWN"
    
    return ac_number, ac_name

def extract_2016_pdf(pdf_path, output_csv):
    print(f"Processing 2016 PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        ac_num, ac_name = extract_constituency_info(pdf)
        print(f"  Constituency: {ac_num} - {ac_name}")
        
        all_rows = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            table = page.extract_table()
            if not table:
                continue
            
            for row in table:
                if not row or not row[0]:
                    continue
                
                # Check if it's a booth row (starts with digit and first column is not '1 2 3...')
                row_str = " ".join([str(c) for c in row if c])
                if str(row[0]).strip().isdigit() and not re.match(r'^1 2 3 4', row_str):
                    # Clean row
                    cleaned_row = [str(cell).strip().replace('\n', ' ') if cell else '0' for cell in row]
                    all_rows.append(cleaned_row)
        
        print(f"  Extracted {len(all_rows)} booths")
        
        # Write to CSV
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if all_rows:
                num_cols = len(all_rows[0])
                # Col 0: Table No, Col 1: PS No, Col 2..N-4: Candidates, N-3: Valid, N-2: Rejected, N-1: Total, N: Tendered
                header = ['ac_number', 'ac_name', 'table_no', 'polling_station_no']
                for i in range(1, num_cols - 5):
                    header.append(f'candidate_{i}')
                header += ['total_valid', 'rejected', 'total', 'tendered']
                
                # If column count doesn't match this schema exactly, just use generic headers
                if len(header) != num_cols + 2:
                    header = ['ac_number', 'ac_name'] + [f'col_{i}' for i in range(num_cols)]
                
                writer.writerow(header)
                for row in all_rows:
                    writer.writerow([ac_num, ac_name] + row)
    
    return len(all_rows)

def main():
    base_dir = Path("/Users/karthikselvan/Desktop/eeze/tn_elections_2016")
    raw_dir = base_dir / "raw_data"
    out_dir = base_dir / "extracted"
    out_dir.mkdir(exist_ok=True)
    
    files = [
        "Ac036.pdf",
        "Ac037.pdf",
        "Ac029.pdf",
        "Ac028.pdf"
    ]
    
    for f in files:
        pdf_path = raw_dir / f
        if pdf_path.exists():
            csv_path = out_dir / f.replace(".pdf", ".csv")
            extract_2016_pdf(pdf_path, csv_path)

if __name__ == "__main__":
    main()
