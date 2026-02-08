#!/usr/bin/env python3
"""
Extract polling station locations from multiple constituency PDFs and prepare for geocoding.
"""

import pdfplumber
import csv
import json
import re
from pathlib import Path


def extract_polling_stations(pdf_path, constituency_name):
    """Extract polling station data from PDF using table extraction."""
    stations = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                    
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    
                    # Skip header rows
                    first_col = str(row[0] or '').strip()
                    if first_col in ['Sl.No', 'Sl. No', 'S.No', ''] or not first_col.isdigit():
                        continue
                    
                    try:
                        sl_no = int(first_col)
                        station_no = row[1] if len(row) > 1 else ""
                        building = row[2] if len(row) > 2 else ""
                        polling_areas = row[3] if len(row) > 3 else ""
                        
                        # Skip if no building info
                        if not building:
                            continue
                        
                        # Clean building name
                        building = str(building).replace('\n', ' ').strip()
                        
                        # Extract village name from building (after comma usually)
                        village_match = re.search(r',\s*([A-Za-z][A-Za-z\s]+)', building)
                        village = village_match.group(1).strip() if village_match else ""
                        
                        # Create search address
                        search_address = f"{building}, {constituency_name}, Kanchipuram, Tamil Nadu, India"
                        
                        stations.append({
                            'sl_no': sl_no,
                            'station_no': str(station_no).strip() if station_no else str(sl_no),
                            'building': building,
                            'village': village,
                            'search_address': search_address
                        })
                        
                    except (ValueError, IndexError) as e:
                        continue
    
    # Remove duplicates based on sl_no
    seen = set()
    unique_stations = []
    for s in stations:
        if s['sl_no'] not in seen:
            seen.add(s['sl_no'])
            unique_stations.append(s)
    
    return sorted(unique_stations, key=lambda x: x['sl_no'])


def main():
    base_dir = Path(__file__).parent.parent
    raw_data_dir = base_dir / "raw_data"
    data_dir = base_dir / "data"
    
    # Constituencies to process
    constituencies = [
        ("alandur_polling_stations.pdf", "Alandur", "028"),
        ("sriperumbudur_polling_stations.pdf", "Sriperumbudur", "029"),
        ("kancheepuram_polling_stations.pdf", "Kancheepuram", "037"),
    ]
    
    for pdf_name, const_name, ac_number in constituencies:
        pdf_path = raw_data_dir / pdf_name
        
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            continue
        
        print(f"\n📄 Processing {const_name} (AC{ac_number})...")
        
        stations = extract_polling_stations(pdf_path, const_name)
        
        if not stations:
            print(f"  ⚠️ No stations extracted")
            continue
        
        print(f"  📊 Found {len(stations)} unique polling stations")
        
        # Save to JSON
        output_path = data_dir / f"{const_name.lower()}_polling_stations.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stations, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved: {output_path}")
        
        # Show sample
        print("  Sample entries:")
        for s in stations[:3]:
            print(f"    Station {s['station_no']}: {s['building'][:50]}...")


if __name__ == "__main__":
    main()
