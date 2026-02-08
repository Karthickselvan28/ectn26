#!/usr/bin/env python3
"""
TN Elections 2021 - Summary Analysis
Analyzes booth-level data and creates summary reports with party-wise breakdowns.
"""

import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from tabulate import tabulate


# Constituency name lookup from filename pattern ACxxx
CONSTITUENCY_LOOKUP = {
    "027": "Shozhinganallur",
    "028": "Alandur", 
    "029": "Sriperumbudur",
    "030": "Pallavaram",
    "031": "Tambaram",
    "032": "Chengalpattu",
    "033": "Thiruporur",
    "034": "Cheyyur",
    "035": "Madurantakam",
    "036": "Uthiramerur",
    "037": "Kancheepuram",
}

# Party name mappings - decoded from reversed text in PDFs
PARTY_MAPPINGS = {
    # DMK and allies
    "magahzak artennum ad": "DMK",
    "artennum magahzak ad": "DMK",
    "lanoitan ssergnoc na": "INC (Congress)",
    "lanoitan ssergnoc naidni": "INC (Congress)",
    
    # AIADMK and allies
    "anna magahzak artenn": "AIADMK",
    "artennum anna magahz": "AIADMK",
    "artennum magahzak ai": "AIADMK",
    "ilattap lakkam ihcta": "PMK",
    "arttennum magazak lak": "AMMK",
    "arttenum magazak lak": "AMMK",
    "lakkam arttennum mag": "AMMK",
    
    # Other parties
    "ralimat maan ihctak": "NTK",
    "ralimat ihctak maan": "NTK",
    "maiam lakkam ihdeen": "MNM",
    "lakkam ihdeen maiam": "MNM",
    "ihdeen lakkam maiam": "MNM",
    "ytrap najuhab jamas": "BSP",
    "jamas najuhab ytrap": "BSP",
    "najuhab jamas ytrap": "BSP",
    "lakkam ihctak ayised": "Desiya Makkal Katchi",
    "ayised lakkam ihtkas": "Desiya Makkal Sakthi",
    "uhtiana lakkam layis": "Social Democratic Party",
    "aakihdavanam ayitrah": "Bharatiya Manavadika",
    "aidni citarcoomed fo": "Democratic Party of India",
    "htuo citarcoomed lan": "Democratic South",
    "aidni nacilbuper )el": "Republican Party of India",
    "nacilbuper )elawahta": "Republican Party (Athawale)",
    "oitareneg selpoep we": "Peoples New Generation",
    
    # Independent
    "tnednepedni": "Independent",
    "ednepedni tn": "Independent",
}

# Columns to exclude (these are total/grand total columns, not actual candidates)
# They appear as candidateN without any party name suffix
EXCLUDE_COLUMNS = {
    'candidate_8', 'candidate_9', 'candidate_10', 'candidate_11', 'candidate_12', 
    'candidate_13', 'candidate_14', 'candidate_15', 'candidate_16', 'candidate_17', 
    'candidate_18', 'candidate_19', 'candidate_20', 'candidate_21', 'candidate_22',
    'candidate_23', 'candidate_24', 'candidate_25', 'candidate_26', 'candidate_27', 
    'candidate_28', 'candidate_29', 'candidate_30'
}


def decode_party_name(raw_name):
    """Decode reversed party name to actual party name."""
    # Extract party name from column (remove candidate_ prefix and number)
    if raw_name.startswith("candidate_"):
        parts = raw_name.split("_", 2)
        if len(parts) >= 3:
            party_text = parts[2].lower().strip()
        else:
            return "Unknown"
    else:
        party_text = raw_name.lower().strip()
    
    # Check mappings
    for pattern, party in PARTY_MAPPINGS.items():
        if pattern in party_text:
            return party
    
    # If contains "tnednepedni" anywhere, it's independent
    if "tnednepedni" in party_text or "ednepedni" in party_text:
        return "Independent"
    
    return "Other"


def get_constituency_from_filename(filepath):
    """Extract constituency number from filename like AC029_sriperumbudur_booths.csv"""
    match = re.search(r'AC(\d{3})', filepath.name)
    if match:
        return match.group(1)
    return None


def analyze_constituency(csv_path):
    """Analyze a single constituency CSV file."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    # Get constituency info from filename if data has UNKNOWN
    const_num = rows[0].get('constituency_number', 'UNKNOWN')
    const_name = rows[0].get('constituency_name', 'UNKNOWN')
    
    # Fix UNKNOWN constituency using filename
    if const_num == 'UNKNOWN' or const_name == 'UNKNOWN':
        ac_num = get_constituency_from_filename(csv_path)
        if ac_num:
            const_num = ac_num
            const_name = CONSTITUENCY_LOOKUP.get(ac_num, const_name)
    
    # Count booths
    num_booths = len(rows)
    
    # Identify vote columns (skip metadata and total columns)
    metadata_cols = {'constituency_number', 'constituency_name', 'table_no', 'polling_station_no', 'note'}
    vote_columns = [col for col in rows[0].keys() 
                   if col not in metadata_cols and col not in EXCLUDE_COLUMNS]
    
    # Calculate votes per candidate and aggregate by party
    candidate_votes = defaultdict(int)
    party_votes = defaultdict(int)
    
    for row in rows:
        for col in vote_columns:
            try:
                votes = int(row[col]) if row[col] else 0
                candidate_votes[col] += votes
                party = decode_party_name(col)
                party_votes[party] += votes
            except ValueError:
                pass
    
    # Sort candidates by votes
    sorted_candidates = sorted(candidate_votes.items(), key=lambda x: x[1], reverse=True)
    
    # Get total valid votes
    total_votes = sum(v for _, v in sorted_candidates)
    
    # Determine winner and runner-up
    winner = sorted_candidates[0] if sorted_candidates else ("Unknown", 0)
    runner_up = sorted_candidates[1] if len(sorted_candidates) > 1 else ("Unknown", 0)
    
    return {
        'constituency_number': const_num,
        'constituency_name': const_name,
        'num_booths': num_booths,
        'winner': {
            'raw_name': winner[0],
            'party': decode_party_name(winner[0]),
            'votes': winner[1]
        },
        'runner_up': {
            'raw_name': runner_up[0],
            'party': decode_party_name(runner_up[0]),
            'votes': runner_up[1]
        },
        'margin': winner[1] - runner_up[1],
        'party_votes': dict(party_votes),
        'total_votes': total_votes,
        'candidate_votes': dict(candidate_votes)
    }


def print_summary_table(results):
    """Print formatted summary table."""
    print("\n" + "=" * 100)
    print("🗳️  TN ASSEMBLY ELECTIONS 2021 - SUMMARY (Kanchipuram Region)")
    print("=" * 100)
    
    # Winners table
    table_data = []
    for r in results:
        table_data.append([
            r['constituency_number'],
            r['constituency_name'],
            r['winner']['party'],
            f"{r['winner']['votes']:,}",
            r['runner_up']['party'],
            f"{r['runner_up']['votes']:,}",
            f"{r['margin']:,}",
            f"{r['total_votes']:,}"
        ])
    
    headers = ["AC No", "Constituency", "Winner", "Votes", "Runner-up", "Votes", "Margin", "Total Votes"]
    print("\n📊 CONSTITUENCY-WISE RESULTS:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Party-wise aggregate
    print("\n📈 PARTY-WISE VOTE SHARE (Across all constituencies):")
    party_totals = defaultdict(int)
    for r in results:
        for party, votes in r['party_votes'].items():
            if party not in ["Unknown", "Other"]:
                party_totals[party] += votes
    
    grand_total = sum(party_totals.values())
    party_table = []
    for party, votes in sorted(party_totals.items(), key=lambda x: x[1], reverse=True):
        pct = (votes / grand_total * 100) if grand_total > 0 else 0
        party_table.append([party, f"{votes:,}", f"{pct:.2f}%"])
    
    print(tabulate(party_table, headers=["Party", "Total Votes", "Vote Share %"], tablefmt="grid"))
    
    # Seats won
    print("\n🏆 SEATS WON:")
    seats_won = defaultdict(int)
    for r in results:
        seats_won[r['winner']['party']] += 1
    
    for party, seats in sorted(seats_won.items(), key=lambda x: x[1], reverse=True):
        print(f"  {party}: {seats} seat(s)")
    
    print("\n" + "=" * 100)


def save_detailed_report(results, output_path):
    """Save detailed JSON report."""
    report = {
        'election': 'Tamil Nadu Legislative Assembly 2021',
        'region': 'Kanchipuram Area',
        'constituencies_analyzed': len(results),
        'results': results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ Detailed report saved to: {output_path}")


def main():
    base_dir = Path(__file__).parent.parent
    extracted_dir = base_dir / "extracted"
    output_dir = base_dir / "output"
    
    # Find CSV files with actual data (size > 100 bytes)
    csv_files = []
    for f in sorted(extracted_dir.glob("AC*_booths.csv")):
        if f.stat().st_size > 100:  # Skip placeholder files
            csv_files.append(f)
    
    print(f"📂 Found {len(csv_files)} constituencies with extracted data\n")
    
    results = []
    for csv_file in csv_files:
        result = analyze_constituency(csv_file)
        if result and result['num_booths'] > 0:
            results.append(result)
            print(f"  ✓ Analyzed: AC{result['constituency_number']} - {result['constituency_name']} ({result['num_booths']} booths)")
    
    if results:
        print_summary_table(results)
        
        # Save detailed report
        report_path = output_dir / "election_analysis_2021.json"
        save_detailed_report(results, report_path)
    else:
        print("❌ No data found to analyze")


if __name__ == "__main__":
    main()
