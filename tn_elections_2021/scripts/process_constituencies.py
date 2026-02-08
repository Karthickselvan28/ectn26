#!/usr/bin/env python3
"""
Process all constituency CSV files to generate standardized JSON files.
Fixes the "Others" column by summing all non-DMK/AIADMK candidate votes.
"""

import pandas as pd
import json
from pathlib import Path
import re

# Paths
EXTRACTED_DIR = Path(__file__).parent.parent / 'extracted'
FRONTEND_DATA_DIR = Path(__file__).parent.parent / 'frontend' / 'data'
CONSTITUENCIES_FILE = Path(__file__).parent.parent / 'data' / 'constituencies.json'

# Ensure output directory exists
FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

def identify_party_columns(df):
    """Identify which candidate columns correspond to DMK and AIADMK."""
    dmk_col = None
    aiadmk_col = None
    
    # Column names are reversed! Check by reversing them
    candidate_cols = [col for col in df.columns if col.startswith('candidate_')]
    
    for col in candidate_cols:
        col_upper = col.upper()
        col_reversed = col_upper[::-1]
        
        # DMK patterns (reversed): ends with "AD" and contains "MUNNETRA" or "DMK"
        # Uthiramerur: "candidate_1_ARTENNUM MAGAHZAK AD" -> reversed has "DA KAZHAGAM MUNNETRA"
        # Alandur: "candidate_1_magahzaK artennuM ad" -> reversed has "da Munnetra Kazhagam"
        if col_upper.endswith('AD'):
            if 'MUNNETRA' in col_reversed or 'DMK' in col_reversed:
                if 'ANNA' not in col_reversed:  # Exclude AIADMK
                    dmk_col = col
        
        # AIADMK patterns (reversed): ends with "AI" or contains "ANNA"
        # Uthiramerur: "candidate_3_ARTENNUM MAGAHZAK AI" -> reversed has "IA KAZHAGAM MUNNETRA"
        # Alandur: "candidate_2_annA magahzaK artenn" -> reversed has "nnetra Kazhagam Anna"
        if col_upper.endswith('AI') or 'ANNA' in col_upper:
            if 'MUNNETRA' in col_reversed or 'ANNA' in col_reversed:
                aiadmk_col = col
    
    return dmk_col, aiadmk_col

def process_constituency_csv(csv_path, ac_number, ac_name):
    """Process a single constituency CSV file."""
    try:
        df = pd.read_csv(csv_path)
        
        # Check if file is empty or just header
        if len(df) == 0:
            print(f"  ⚠️  Empty file: {ac_name}")
            return None
        
        # Identify party columns
        dmk_col, aiadmk_col = identify_party_columns(df)
        
        if not dmk_col or not aiadmk_col:
            print(f"  ⚠️  Could not identify party columns for {ac_name}")
            return None
        
        print(f"  ✓ {ac_name}: DMK={dmk_col}, AIADMK={aiadmk_col}")
        
        # Get all candidate columns (columns starting with 'candidate_')
        candidate_cols = [col for col in df.columns if col.startswith('candidate_') and col not in [dmk_col, aiadmk_col]]
        
        booths = []
        for idx, row in df.iterrows():
            # Use row index + 1 as unique identifier since table_no resets per page
            # booth_no = polling_station_no (the actual booth identifier like "5 (M)")
            polling_station = str(row.get('polling_station_no', row.get('table_no', ''))).strip()
            
            # table_no is sequential within PDF pages (1-28 per page), NOT unique
            # Use row index as a unique sequential number
            booth_no = str(idx + 1)  # 1-indexed unique ID
            
            # Extract numeric station number from polling_station_no for lookups
            try:
                match = re.search(r'\d+', polling_station)
                station_no = int(match.group()) if match else idx + 1
            except:
                station_no = idx + 1
            
            dmk_votes = int(row[dmk_col]) if pd.notna(row[dmk_col]) else 0
            aiadmk_votes = int(row[aiadmk_col]) if pd.notna(row[aiadmk_col]) else 0
            
            # Extract individual party votes from other candidate columns
            other_parties = {}
            others_total = 0
            
            for col in candidate_cols:
                if pd.notna(row[col]):
                    val = int(row[col])
                    # Skip if value is greater than DMK + AIADMK (likely cumulative total)
                    if val < dmk_votes + aiadmk_votes:
                        # Extract party name from column (reversed)
                        party_name = col.replace('candidate_', '').split('_', 1)
                        if len(party_name) > 1:
                            # Reverse the party name back
                            party_abbr = party_name[1].upper()[::-1].strip()
                            # Simplify common party names
                            if 'BAHUJAN' in party_abbr or 'BSP' in party_abbr:
                                party_abbr = 'BSP'
                            elif 'MAKKAL NEEDHI' in party_abbr or 'MAIAM' in party_abbr:
                                party_abbr = 'MDMK'
                            elif 'TAMILAR' in party_abbr and 'NAAM' in party_abbr:
                                party_abbr = 'NTK'
                            elif 'PATTALI' in party_abbr or 'PMK' in party_abbr:
                                party_abbr = 'PMK'
                            elif party_abbr == '':
                                party_abbr = 'IND'
                            
                            # Aggregate if party already exists
                            if party_abbr in other_parties:
                                other_parties[party_abbr] += val
                            else:
                                other_parties[party_abbr] = val
                            others_total += val
            
            total_votes = dmk_votes + aiadmk_votes + others_total
            
            # Determine winner
            if dmk_votes > aiadmk_votes:
                winner = "DMK"
                margin = dmk_votes - aiadmk_votes
            else:
                winner = "AIADMK"
                margin = aiadmk_votes - dmk_votes
            
            margin_pct = (margin / total_votes * 100) if total_votes > 0 else 0
            
            # Category based on margin
            if margin_pct > 10:
                category = "STRONG"
            elif margin_pct > 5:
                category = "LEAN"
            else:
                category = "SWING"
            
            booth = {
                "booth_no": booth_no,
                "station_no": int(station_no) if pd.notna(station_no) else 0,
                "winner": winner,
                "dmk_votes": dmk_votes,
                "aiadmk_votes": aiadmk_votes,
                "other_parties": other_parties,
                "others_votes": others_total,  # Keep for backward compatibility
                "total_votes": total_votes,
                "margin": margin,
                "margin_pct": round(margin_pct, 2),
                "category": category,
                "village": "",
                "building": "",
                "lat": None,
                "lng": None
            }
            
            booths.append(booth)
        
        # Calculate summary
        dmk_won = sum(1 for b in booths if b['winner'] == 'DMK')
        aiadmk_won = sum(1 for b in booths if b['winner'] == 'AIADMK')
        swing = sum(1 for b in booths if b['category'] == 'SWING')
        lean = sum(1 for b in booths if b['category'] == 'LEAN')
        strong = sum(1 for b in booths if b['category'] == 'STRONG')
        
        result = {
            "constituency": f"{ac_name} (AC{ac_number})",
            "ac_number": ac_number,
            "summary": {
                "total_booths": len(booths),
                "dmk_won": dmk_won,
                "aiadmk_won": aiadmk_won,
                "swing": swing,
                "lean": lean,
                "strong": strong
            },
            "booths": booths
        }
        
        return result
        
    except Exception as e:
        print(f"  ❌ Error processing {ac_name}: {e}")
        return None

def merge_with_geocoded_data(processed_data, ac_number, ac_name):
    """Merge with existing geocoded data if available."""
    # Try multiple filename patterns
    name_clean = ac_name.lower().replace(' ', '_')
    possible_files = [
        FRONTEND_DATA_DIR / f"{name_clean}_map_data.json",
        FRONTEND_DATA_DIR / f"ac{ac_number}_map_data.json",
        FRONTEND_DATA_DIR / f"{ac_number}_map_data.json",
    ]
    
    geocoded_file = None
    for fp in possible_files:
        if fp.exists():
            geocoded_file = fp
            break
    
    if not geocoded_file:
        return processed_data
    
    print(f"  📍 Merging geocoded data for AC{ac_number}")
    
    try:
        with open(geocoded_file, 'r') as f:
            geocoded = json.load(f)
        
        # Create lookup by booth_no
        geocoded_lookup = {str(b['booth_no']): b for b in geocoded.get('booths', [])}
        
        # Merge lat/lng and location data
        for booth in processed_data['booths']:
            booth_no = str(booth['booth_no'])
            if booth_no in geocoded_lookup:
                geo_booth = geocoded_lookup[booth_no]
                booth['lat'] = geo_booth.get('lat')
                booth['lng'] = geo_booth.get('lng')
                booth['village'] = geo_booth.get('village', '')
                booth['building'] = geo_booth.get('building', '')
        
        return processed_data
        
    except Exception as e:
        print(f"  ⚠️  Error merging geocoded data: {e}")
        return processed_data

def generate_master_json(constituencies_data):
    """Generate master.json with hierarchy."""
    # Load constituency metadata
    with open(CONSTITUENCIES_FILE, 'r') as f:
        meta = json.load(f)
    
    # Group by district
    districts = {}
    for const in meta['kanchipuram_area']:
        district_name = const['district_name']
        if district_name not in districts:
            districts[district_name] = {
                "code": const['district_code'],
                "name": district_name,
                "constituencies": []
            }
        
        ac_number = const['ac_number']
        const_data = constituencies_data.get(ac_number)
        
        districts[district_name]['constituencies'].append({
            "ac_number": ac_number,
            "name": const['name'],
            "type": const['type'],
            "data_file": f"{const['name'].lower()}.json",
            "has_geocoding": const_data and any(b.get('lat') for b in const_data['booths']) if const_data else False,
            "total_booths": const_data['summary']['total_booths'] if const_data else 0
        })
    
    master = {
        "state": "Tamil Nadu",
        "election_year": 2021,
        "districts": list(districts.values())
    }
    
    return master

def main():
    print("🔄 Processing constituency CSV files...\n")
    
    constituencies_data = {}
    
    # Process each CSV file
    csv_files = sorted(EXTRACTED_DIR.glob("AC*_booths.csv"))
    
    for csv_path in csv_files:
        # Extract AC number and name from filename
        match = re.match(r'AC(\d+)_(.+)_booths\.csv', csv_path.name)
        if not match:
            continue
        
        ac_number = match.group(1)
        ac_name = match.group(2).replace('_', ' ').title()
        
        print(f"Processing AC{ac_number} - {ac_name}...")
        
        # Process CSV
        data = process_constituency_csv(csv_path, ac_number, ac_name)
        
        if data:
            # Merge with geocoded data if available
            data = merge_with_geocoded_data(data, ac_number, ac_name)
            
            constituencies_data[ac_number] = data
            
            # Save individual constituency file
            output_file = FRONTEND_DATA_DIR / f"{ac_name.lower().replace(' ', '_')}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"  ✅ Saved: {output_file.name} ({data['summary']['total_booths']} booths)\n")
    
    # Generate master.json
    print("\n📋 Generating master.json...")
    master = generate_master_json(constituencies_data)
    
    master_file = FRONTEND_DATA_DIR / 'master.json'
    with open(master_file, 'w') as f:
        json.dump(master, f, indent=2)
    
    print(f"✅ Saved: {master_file.name}")
    
    # Summary
    print(f"\n✨ Processed {len(constituencies_data)} constituencies")
    print(f"📁 Output directory: {FRONTEND_DATA_DIR}")

if __name__ == '__main__':
    main()
