import pandas as pd
import json
import re
import os
from pathlib import Path

def get_booth_num(booth_cell):
    # Extract digit from booth cell (e.g. "5 (M)" -> 5, "5 A" -> 5, "5" -> 5)
    match = re.search(r'(\d+)', str(booth_cell))
    if match:
        return int(match.group(1))
    return None

def analyze_constituency(ac_id, mapping, dir_2016, dir_2021):
    print(f"Analyzing {ac_id} - {mapping['name']}...")
    
    # Load 2016 Data
    f_2016 = dir_2016 / f"Ac{ac_id[2:]}.csv"
    df_2016 = pd.read_csv(f_2016)
    
    # Load 2021 Data
    files_2021 = list(dir_2021.glob(f"{ac_id}*.csv"))
    if not files_2021:
        print(f"  Error: 2021 file not found for {ac_id}")
        return None
    df_2021 = pd.read_csv(files_2021[0])
    
    # Clean 2016 Data
    df_2016['booth_no'] = df_2016['polling_station_no'].apply(get_booth_num)
    
    # Identify Candidate Columns for 2016
    cand_cols_16 = [c for c in df_2016.columns if c.startswith('candidate_')]
    
    # Aggregate 2016 (some booths might have multiple entries due to PDF parsing)
    agg_16 = {c: 'sum' for c in cand_cols_16}
    df_16_agg = df_2016.groupby('booth_no').agg(agg_16).reset_index()
    
    df_16_clean = pd.DataFrame()
    df_16_clean['booth_no'] = df_16_agg['booth_no']
    df_16_clean['total_votes_2016'] = df_16_agg[cand_cols_16].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
    
    for party, col in mapping['2016'].items():
        df_16_clean[f'{party}_2016'] = pd.to_numeric(df_16_agg[col], errors='coerce').fillna(0)
    
    # Clean 2021 Data
    df_2021['booth_no'] = df_2021['polling_station_no'].apply(get_booth_num)
    
    # Identify Candidate Columns for 2021
    cand_cols_21 = [c for c in df_2021.columns if c.startswith('candidate_') and not any(x in c for x in ['valid', 'rejected', 'total', 'tendered'])]
    # Filter out columns that are clearly totals (though 2021 extraction was messy)
    # Most 2021 files have ~20 candidates, then totals.
    # Let's just use the ones mapped or sum all candidate_* that are numeric
    
    df_2021_nums = df_2021.copy()
    for col in cand_cols_21:
        df_2021_nums[col] = pd.to_numeric(df_2021[col], errors='coerce').fillna(0)
    
    # Calculated Total for 2021
    # We'll only sum the ones that seem like actual candidate columns (usually up to Candidate 20 or so)
    # Actually, let's just trust the sum of candidate columns we mapped + NOTA if we can find it.
    
    map_21 = mapping['2021']
    df_21_agg_base = df_2021_nums.groupby('booth_no')
    
    # Aggregate only necessary columns
    agg_cols = list(map_21.values())
    # Add NOTA if possible (usually candidate_16 or 20)
    # For simplicity, let's calculate total as sum of ALL candidate_ columns that aren't the very end ones
    # In 2021, columns[-4:] are totals.
    actual_cand_cols_21 = cand_cols_21[:-4] if len(cand_cols_21) > 4 else cand_cols_21
    
    df_21_agg = df_21_agg_base[actual_cand_cols_21].sum().reset_index()
    df_21_agg['total_votes_2021'] = df_21_agg[actual_cand_cols_21].sum(axis=1)
    
    for party, col in map_21.items():
        df_21_agg.rename(columns={col: f'{party}_2021'}, inplace=True)
    
    # Merge
    merged = pd.merge(df_16_clean, df_21_agg, on='booth_no', how='inner')
    
    # Filter out rows with 0 total votes to avoid Infinity
    merged = merged[(merged['total_votes_2016'] > 0) & (merged['total_votes_2021'] > 0)]
    
    # Calculate Swings
    common_parties = set(mapping['2016'].keys()).intersection(set(mapping['2021'].keys()))
    
    # Handle INC/DMK alliance in Sriperumbudur
    if 'INC' in mapping['2016'] and 'DMK' in mapping['2021']:
        merged['DMK_INC_2016'] = merged.get('INC_2016', 0)
        merged['DMK_INC_2021'] = merged.get('DMK_2021', 0)
        common_parties.add('DMK_INC')

    for party in common_parties:
        merged[f'{party}_share_2016'] = (merged[f'{party}_2016'] / merged['total_votes_2016'] * 100).round(2)
        merged[f'{party}_share_2021'] = (merged[f'{party}_2021'] / merged['total_votes_2021'] * 100).round(2)
        merged[f'{party}_swing'] = (merged[f'{party}_share_2021'] - merged[f'{party}_share_2016']).round(2)
    
    merged['turnout_change'] = ((merged['total_votes_2021'] - merged['total_votes_2016']) / merged['total_votes_2016'] * 100).round(2)
    
    return merged
    

def main():
    base_dir = Path("/Users/karthikselvan/Desktop/eeze")
    dir_16 = base_dir / "tn_elections_2016/extracted"
    dir_21 = base_dir / "tn_elections_2021/extracted"
    out_dir = base_dir / "tn_elections_2016/output"
    out_dir.mkdir(exist_ok=True)
    
    with open(base_dir / "tn_elections_2016/scripts/candidate_mapping.json", 'r') as f:
        mapping = json.load(f)
    
    all_summary = []
    
    for ac_id, m in mapping.items():
        results = analyze_constituency(ac_id, m, dir_16, dir_21)
        if results is not None:
            results.to_csv(out_dir / f"{ac_id}_comparison.csv", index=False)
            print(f"  ✓ Saved to {ac_id}_comparison.csv")
            
            # Summary stats
            summary = {
                "ac_id": ac_id,
                "name": m['name'],
                "avg_dmk_swing": results.get('DMK_swing', results.get('DMK_INC_swing', 0)).mean(),
                "avg_aiadmk_swing": results.get('AIADMK_swing', 0).mean(),
                "avg_turnout_change": results['turnout_change'].mean()
            }
            all_summary.append(summary)
    
    with open(out_dir / "election_comparison_summary.json", 'w') as f:
        json.dump(all_summary, f, indent=2)
    print("\nOverall Analysis Complete!")

if __name__ == "__main__":
    main()
