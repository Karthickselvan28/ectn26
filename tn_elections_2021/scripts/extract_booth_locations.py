#!/usr/bin/env python3
"""
Extract polling station locations from PDF and prepare for geocoding.
Uses table extraction for accurate parsing.
"""

import pdfplumber
import csv
import json
import re
from pathlib import Path


def extract_polling_stations(pdf_path):
    """Extract polling station data from PDF using table extraction."""
    stations = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Processing {len(pdf.pages)} pages...")
        
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            
            for table in tables:
                for row in table:
                    # Skip header rows
                    if not row or row[0] in ['Sl.No', '1', None]:
                        continue
                    if row[0] == 'Sl.No' or (row[1] and row[1].startswith('Polling')):
                        continue
                    
                    try:
                        sl_no = row[0]
                        station_no = row[1]
                        building = row[2] if len(row) > 2 else ""
                        polling_areas = row[3] if len(row) > 3 else ""
                        voter_type = row[4] if len(row) > 4 else "All Voters"
                        
                        # Skip if not valid data
                        if not sl_no or not station_no:
                            continue
                        if not sl_no.isdigit():
                            continue
                            
                        # Clean building name
                        building = building.replace('\n', ' ').strip() if building else ""
                        
                        # Extract village name from building
                        village_match = re.search(r',\s*([A-Za-z]+)', building)
                        village = village_match.group(1) if village_match else ""
                        
                        # Create search address for geocoding
                        # Format: "Building Name, Village, Uthiramerur, Kanchipuram, Tamil Nadu"
                        search_address = f"{building}, Uthiramerur, Kanchipuram, Tamil Nadu, India"
                        
                        stations.append({
                            'station_no': int(station_no),
                            'building': building,
                            'village': village,
                            'polling_areas': polling_areas.replace('\n', ' ') if polling_areas else "",
                            'voter_type': voter_type.strip() if voter_type else "All Voters",
                            'search_address': search_address
                        })
                        
                    except (ValueError, IndexError) as e:
                        continue
    
    # Remove duplicates based on station_no
    seen = set()
    unique_stations = []
    for s in stations:
        if s['station_no'] not in seen:
            seen.add(s['station_no'])
            unique_stations.append(s)
    
    return sorted(unique_stations, key=lambda x: x['station_no'])


def save_data(stations, base_dir):
    """Save extracted stations to CSV and JSON."""
    
    # CSV
    csv_path = base_dir / "data" / "uthiramerur_polling_stations.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['station_no', 'building', 'village', 'search_address'])
        writer.writeheader()
        for s in stations:
            writer.writerow({
                'station_no': s['station_no'],
                'building': s['building'],
                'village': s['village'],
                'search_address': s['search_address']
            })
    print(f"✅ Saved CSV: {csv_path}")
    
    # JSON
    json_path = base_dir / "data" / "uthiramerur_polling_stations.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(stations, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved JSON: {json_path}")


def main():
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "raw_data" / "polling_stations_locations.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📄 Extracting from: {pdf_path}")
    stations = extract_polling_stations(pdf_path)
    print(f"📊 Found {len(stations)} unique polling stations")
    
    # Show sample
    print("\n📋 Sample entries:")
    for s in stations[:5]:
        print(f"  Station {s['station_no']}: {s['building'][:60]}...")
    
    save_data(stations, base_dir)
    
    print(f"\n🗺️  Next step: Geocode addresses using Google Maps API or similar")


if __name__ == "__main__":
    main()
