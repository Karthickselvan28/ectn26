#!/usr/bin/env python3
"""
Booth Classification Analysis - Categorize booths as Strong DMK, Strong AIADMK, or Swing.

Classification Methodology (based on political science standards):
- STRONG: Margin >= 10% (winner has clear advantage)  
- LEAN: Margin 5-10% (advantage but competitive)
- SWING: Margin < 5% (highly competitive, can go either way)

Reference: Cook Political Report uses 5% threshold for competitive districts,
academic research often uses 5-10% for swing/competitive classification.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
from tabulate import tabulate


# Classification thresholds (as percentage of total votes in booth)
SWING_THRESHOLD = 5.0      # < 5% margin = Swing
LEAN_THRESHOLD = 10.0      # 5-10% margin = Lean
# > 10% margin = Strong

# Column mappings for parties (decoded from reversed text)
PARTY_COLUMNS = {
    '028': {  # Alandur
        'DMK': 'candidate_1_magahzaK artennuM ad',
        'AIADMK': 'candidate_2_annA magahzaK artenn',
    },
    '029': {  # Sriperumbudur
        'INC': 'candidate_1_LANOITAN SSERGNOC NA',
        'AIADMK': 'candidate_2_ARTENNUM ANNA MAGAHZ',
    },
    '036': {  # Uthiramerur
        'DMK': 'candidate_1_ARTENNUM MAGAHZAK AD',
        'AIADMK': 'candidate_3_ARTENNUM MAGAHZAK AI',
        'AMMK': 'candidate_7_ARTTENNUM MAGAZAK LA',
    },
    '037': {  # Kancheepuram
        'DMK': 'candidate_1_ARTENNUM MAGAHZAK AD',
        'PMK': 'candidate_5_ILATTAP LAKKAM IHCTA',
    },
}


def classify_booth(margin_pct):
    """Classify booth based on margin percentage."""
    if margin_pct < SWING_THRESHOLD:
        return "SWING"
    elif margin_pct < LEAN_THRESHOLD:
        return "LEAN"
    else:
        return "STRONG"


def analyze_booths(csv_path, constituency_num):
    """Analyze booth-level data and classify each booth."""
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        return None
    
    # Get party columns for this constituency
    party_cols = PARTY_COLUMNS.get(constituency_num, {})
    
    results = []
    category_counts = defaultdict(lambda: defaultdict(int))
    
    for row in rows:
        booth_no = row.get('polling_station_no', 'Unknown')
        
        # Get votes for main parties
        party_votes = {}
        for party, col in party_cols.items():
            try:
                party_votes[party] = int(row.get(col, 0) or 0)
            except (ValueError, TypeError):
                party_votes[party] = 0
        
        if not party_votes:
            continue
            
        # Calculate total votes (for main 2 parties for margin)
        sorted_parties = sorted(party_votes.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_parties) < 2:
            continue
            
        winner_party, winner_votes = sorted_parties[0]
        runner_party, runner_votes = sorted_parties[1]
        
        # Calculate margin percentage
        total_two_party = winner_votes + runner_votes
        if total_two_party > 0:
            margin = winner_votes - runner_votes
            margin_pct = (margin / total_two_party) * 100
        else:
            margin_pct = 0
        
        # Classify
        category = classify_booth(margin_pct)
        full_category = f"{category} {winner_party}"
        
        category_counts[category][winner_party] += 1
        
        results.append({
            'booth': booth_no,
            'winner': winner_party,
            'winner_votes': winner_votes,
            'runner_up': runner_party,
            'runner_votes': runner_votes,
            'margin': margin,
            'margin_pct': margin_pct,
            'category': category,
            'full_category': full_category,
        })
    
    return results, category_counts


def print_classification_summary(results, category_counts, constituency_name):
    """Print formatted classification summary."""
    
    print("\n" + "=" * 80)
    print(f"🗳️  BOOTH CLASSIFICATION: {constituency_name.upper()}")
    print("=" * 80)
    print(f"\nMethodology: Based on Two-Party Vote Margin Percentage")
    print(f"  SWING:  Margin < {SWING_THRESHOLD}% (Highly competitive)")
    print(f"  LEAN:   Margin {SWING_THRESHOLD}-{LEAN_THRESHOLD}% (Competitive advantage)")
    print(f"  STRONG: Margin > {LEAN_THRESHOLD}% (Clear advantage)")
    
    # Summary counts
    total = len(results)
    print(f"\nTotal Booths Analyzed: {total}\n")
    
    print("📊 CLASSIFICATION BREAKDOWN:")
    print("-" * 50)
    
    # Calculate totals per category
    swing_total = sum(category_counts['SWING'].values())
    lean_total = sum(category_counts['LEAN'].values())
    strong_total = sum(category_counts['STRONG'].values())
    
    table_data = []
    
    # Swing booths
    for party, count in sorted(category_counts['SWING'].items()):
        table_data.append(['🔄 SWING', party, count, f"{count/total*100:.1f}%"])
    if swing_total:
        table_data.append(['🔄 SWING', 'TOTAL', swing_total, f"{swing_total/total*100:.1f}%"])
    table_data.append(['---', '---', '---', '---'])
    
    # Lean booths  
    for party, count in sorted(category_counts['LEAN'].items()):
        table_data.append([f'↗️ LEAN', party, count, f"{count/total*100:.1f}%"])
    if lean_total:
        table_data.append([f'↗️ LEAN', 'TOTAL', lean_total, f"{lean_total/total*100:.1f}%"])
    table_data.append(['---', '---', '---', '---'])
    
    # Strong booths
    for party, count in sorted(category_counts['STRONG'].items()):
        table_data.append(['💪 STRONG', party, count, f"{count/total*100:.1f}%"])
    if strong_total:
        table_data.append(['💪 STRONG', 'TOTAL', strong_total, f"{strong_total/total*100:.1f}%"])
    
    print(tabulate(table_data, headers=['Category', 'Party', 'Booths', '%'], tablefmt='grid'))
    
    # Show swing booths detail
    swing_booths = [r for r in results if r['category'] == 'SWING']
    if swing_booths:
        print(f"\n\n🔄 SWING BOOTHS DETAIL ({len(swing_booths)} booths):")
        print("-" * 70)
        swing_table = []
        for b in sorted(swing_booths, key=lambda x: x['margin_pct']):
            swing_table.append([
                b['booth'],
                b['winner'],
                b['winner_votes'],
                b['runner_up'],
                b['runner_votes'],
                b['margin'],
                f"{b['margin_pct']:.1f}%"
            ])
        print(tabulate(swing_table[:30], 
                      headers=['Booth', 'Winner', 'Votes', 'Runner-up', 'Votes', 'Margin', 'Margin%'],
                      tablefmt='grid'))
        if len(swing_booths) > 30:
            print(f"\n  ... and {len(swing_booths) - 30} more swing booths")
    
    print("\n" + "=" * 80)
    
    return {
        'swing': swing_total,
        'lean': lean_total, 
        'strong': strong_total,
        'total': total
    }


def save_booth_classification(results, output_path):
    """Save detailed booth classification to CSV."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'booth', 'category', 'winner', 'winner_votes', 
            'runner_up', 'runner_votes', 'margin', 'margin_pct'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'booth': r['booth'],
                'category': r['full_category'],
                'winner': r['winner'],
                'winner_votes': r['winner_votes'],
                'runner_up': r['runner_up'],
                'runner_votes': r['runner_votes'],
                'margin': r['margin'],
                'margin_pct': round(r['margin_pct'], 2)
            })
    print(f"✅ Booth classification saved to: {output_path}")


def main():
    base_dir = Path(__file__).parent.parent
    extracted_dir = base_dir / "extracted"
    output_dir = base_dir / "output"
    
    # Analyze Uthiramerur specifically (as requested)
    constituency = "036"
    name = "Uthiramerur"
    csv_file = extracted_dir / f"AC{constituency}_uthiramerur_booths.csv"
    
    if csv_file.exists():
        results, category_counts = analyze_booths(csv_file, constituency)
        summary = print_classification_summary(results, category_counts, name)
        
        # Save to CSV
        output_file = output_dir / f"booth_classification_{name.lower()}.csv"
        save_booth_classification(results, output_file)
        
        # Print strategic summary
        print("\n📈 STRATEGIC INSIGHTS:")
        print(f"  • Swing booths ({summary['swing']}): Key battleground - small shifts can flip these")
        print(f"  • Lean booths ({summary['lean']}): Monitor closely - can become swing with good campaign")
        print(f"  • Strong booths ({summary['strong']}): Base voters - focus on turnout here")
        
        if summary['swing'] > 0:
            print(f"\n  ⚡ In a constituency won by just 1,034 votes, these {summary['swing']} swing booths")
            print(f"     are CRITICAL - they represent the real battleground!")


if __name__ == "__main__":
    main()
