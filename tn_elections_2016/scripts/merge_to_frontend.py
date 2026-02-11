import pandas as pd
import json
import os
from pathlib import Path

def merge_comparison_to_json(ac_id, name, output_dir, json_dir):
    csv_path = output_dir / f"{ac_id}_comparison.csv"
    json_path = json_dir / f"{name.lower()}.json"
    
    if not csv_path.exists() or not json_path.exists():
        print(f"Skipping {ac_id}: CSV or JSON not found")
        return

    # Load Comparison CSV
    df_comp = pd.read_csv(csv_path)
    
    # Load Existing JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # Create a lookup for comparison data
    comp_map = df_comp.set_index('booth_no').to_dict('index')
    
    # Identify swing columns
    dmk_swing_col = next((c for c in df_comp.columns if 'swing' in c and 'DMK' in c and 'AIADMK' not in c), None)
    aiadmk_swing_col = next((c for c in df_comp.columns if 'swing' in c and 'AIADMK' in c), None)
    
    # Update Booths in JSON
    for booth in data['booths']:
        try:
            b_no = int(booth['booth_no'])
            if b_no in comp_map:
                c = comp_map[b_no]
                booth['comparison'] = {
                    'dmk_swing': round(float(c.get(dmk_swing_col, 0)), 2) if dmk_swing_col else 0,
                    'aiadmk_swing': round(float(c.get(aiadmk_swing_col, 0)), 2) if aiadmk_swing_col else 0,
                    'turnout_change': round(float(c.get('turnout_change', 0)), 2)
                }
        except (ValueError, KeyError):
            continue

    # Update Summary in JSON
    if dmk_swing_col:
        data['summary']['avg_dmk_swing'] = float(df_comp[dmk_swing_col].mean())
    if aiadmk_swing_col:
        data['summary']['avg_aiadmk_swing'] = float(df_comp[aiadmk_swing_col].mean())
    data['summary']['avg_turnout_change'] = float(df_comp['turnout_change'].mean())

    # Save updated JSON
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated {json_path}")

def main():
    root = Path("/Users/karthikselvan/Desktop/eeze")
    output_dir = root / "tn_elections_2016/output"
    json_dir = root / "tn_elections_2021/frontend/data"
    
    constituencies = [
        ("AC036", "Uthiramerur"),
        ("AC037", "Kancheepuram"),
        ("AC029", "Sriperumbudur"),
        ("AC028", "Alandur")
    ]
    
    for ac_id, name in constituencies:
        merge_comparison_to_json(ac_id, name, output_dir, json_dir)

if __name__ == "__main__":
    main()
