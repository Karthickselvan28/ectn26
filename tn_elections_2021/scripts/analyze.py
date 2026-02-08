#!/usr/bin/env python3
"""
Analyze extracted booth-level data and create summary reports.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict


def analyze_constituency(csv_path):
    """Analyze a single constituency CSV file."""
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    # Get constituency info
    const_num = rows[0]['constituency_number']
    const_name = rows[0]['constituency_name']
    
    # Count booths
    num_booths = len(rows)
    
    # Calculate total votes per candidate
    # Identify vote columns (skip metadata columns)
    metadata_cols = {'constituency_number', 'constituency_name', 'table_no', 'polling_station_no', 'note'}
    vote_columns = [col for col in rows[0].keys() if col not in metadata_cols]
    
    candidate_totals = defaultdict(int)
    
    for row in rows:
        for col in vote_columns:
            try:
                votes = int(row[col]) if row[col] else 0
                candidate_totals[col] += votes
            except ValueError:
                pass
    
    # Sort by votes
    sorted_candidates = sorted(candidate_totals.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'constituency_number': const_num,
        'constituency_name': const_name,
        'num_booths': num_booths,
        'candidate_totals': sorted_candidates,
        'total_votes': sum(candidate_totals.values())
    }


def main():
    base_dir = Path(__file__).parent.parent
    extracted_dir = base_dir / "extracted"
    output_dir = base_dir / "output"
    
    # Find all CSV files
    csv_files = sorted(extracted_dir.glob("AC*_booths.csv"))
    
    print(f"Analyzing {len(csv_files)} constituency files\n")
    print("=" * 80)
    
    all_results = []
    total_booths = 0
    
    for csv_file in csv_files:
        result = analyze_constituency(csv_file)
        
        if result and result['num_booths'] > 0:
            all_results.append(result)
            total_booths += result['num_booths']
            
            print(f"\n{result['constituency_number']} - {result['constituency_name']}")
            print(f"  Booths: {result['num_booths']}")
            print(f"  Total Votes: {result['total_votes']:,}")
            print(f"  Top 3 candidates by votes:")
            for i, (candidate, votes) in enumerate(result['candidate_totals'][:3], 1):
                percentage = (votes / result['total_votes'] * 100) if result['total_votes'] > 0 else 0
                print(f"    {i}. {candidate}: {votes:,} ({percentage:.1f}%)")
    
    print("\n" + "=" * 80)
    print(f"\nSummary:")
    print(f"  Constituencies analyzed: {len(all_results)}")
    print(f"  Total polling booths: {total_booths}")
    print(f"  Total votes across all constituencies: {sum(r['total_votes'] for r in all_results):,}")
    
    # Save summary to JSON
    summary_file = output_dir / "kanchipuram_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'constituencies': all_results,
            'total_booths': total_booths,
            'total_votes': sum(r['total_votes'] for r in all_results)
        }, f, indent=2)
    
    print(f"\n✓ Summary saved to: {summary_file}")
    
    # Create combined CSV
    combined_csv = output_dir / "kanchipuram_all_booths.csv"
    
    with open(combined_csv, 'w', newline='', encoding='utf-8') as outfile:
        writer = None
        
        for csv_file in csv_files:
            with open(csv_file, 'r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                
                # Skip if it's a placeholder (has 'note' column with OCR message)
                first_row = next(reader, None)
                if first_row and first_row.get('note'):
                    continue
                
                if writer is None:
                    # Initialize writer with first file's headers
                    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                    writer.writeheader()
                
                if first_row:
                    writer.writerow(first_row)
                
                for row in reader:
                    writer.writerow(row)
    
    print(f"✓ Combined data saved to: {combined_csv}")
    print("=" * 80)


if __name__ == "__main__":
    main()
