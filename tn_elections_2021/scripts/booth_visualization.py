#!/usr/bin/env python3
"""
Booth Classification Visualization
Creates visual charts showing booth-level voting patterns.
"""

import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from collections import defaultdict

# Color schemes
COLORS = {
    'DMK': '#E31A1C',        # Red
    'AIADMK': '#33A02C',     # Green  
    'AMMK': '#6A3D9A',       # Purple
    'INC': '#1F78B4',        # Blue
    'PMK': '#FF7F00',        # Orange
    'NTK': '#FFFF33',        # Yellow
    'SWING': '#FFD700',      # Gold
    'LEAN': '#87CEEB',       # Light Blue
    'STRONG': '#228B22',     # Forest Green
}

CATEGORY_COLORS = {
    'SWING DMK': '#FF6B6B',
    'SWING AIADMK': '#69DB7C',
    'LEAN DMK': '#E03131',
    'LEAN AIADMK': '#2F9E44',
    'STRONG DMK': '#A61E1E',
    'STRONG AIADMK': '#1B6D2D',
    'STRONG AMMK': '#6A3D9A',
    'LEAN AMMK': '#9C7BC0',
}


def load_classification_data(csv_path):
    """Load booth classification data from CSV."""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def create_pie_chart(data, output_path):
    """Create pie chart of booth categories."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left: Category breakdown
    category_counts = defaultdict(int)
    for row in data:
        cat = row['category'].split()[0]  # SWING, LEAN, or STRONG
        category_counts[cat] += 1
    
    labels = list(category_counts.keys())
    sizes = list(category_counts.values())
    colors = ['#FFD700', '#87CEEB', '#228B22']
    explode = (0.05, 0, 0)
    
    axes[0].pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
    axes[0].set_title('Booth Classification Distribution', fontsize=14, fontweight='bold')
    
    # Right: Party breakdown within categories
    party_cat_counts = defaultdict(lambda: defaultdict(int))
    for row in data:
        parts = row['category'].split()
        cat = parts[0]
        party = parts[1] if len(parts) > 1 else 'Unknown'
        party_cat_counts[cat][party] += 1
    
    # Stacked bar data
    categories = ['SWING', 'LEAN', 'STRONG']
    parties = ['DMK', 'AIADMK', 'AMMK']
    
    x = np.arange(len(categories))
    width = 0.25
    
    for i, party in enumerate(parties):
        counts = [party_cat_counts[cat].get(party, 0) for cat in categories]
        if sum(counts) > 0:
            bars = axes[1].bar(x + i*width, counts, width, label=party, 
                              color=COLORS.get(party, '#999999'))
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                if count > 0:
                    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                               str(count), ha='center', va='bottom', fontsize=9)
    
    axes[1].set_xlabel('Category')
    axes[1].set_ylabel('Number of Booths')
    axes[1].set_title('Party Distribution by Category', fontsize=14, fontweight='bold')
    axes[1].set_xticks(x + width)
    axes[1].set_xticklabels(categories)
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {output_path}")


def create_margin_histogram(data, output_path):
    """Create histogram of vote margins."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    dmk_margins = []
    aiadmk_margins = []
    
    for row in data:
        margin = float(row['margin_pct'])
        if row['winner'] == 'DMK':
            dmk_margins.append(margin)
        elif row['winner'] == 'AIADMK':
            aiadmk_margins.append(-margin)  # Negative for AIADMK wins
    
    # Create histogram
    bins = np.linspace(-50, 50, 51)
    
    ax.hist(dmk_margins, bins=[b for b in bins if b >= 0], 
            color=COLORS['DMK'], alpha=0.7, label='DMK Won', edgecolor='black')
    ax.hist(aiadmk_margins, bins=[b for b in bins if b <= 0], 
            color=COLORS['AIADMK'], alpha=0.7, label='AIADMK Won', edgecolor='black')
    
    # Add swing zone
    ax.axvspan(-5, 5, alpha=0.2, color='yellow', label='Swing Zone (<5%)')
    ax.axvline(x=0, color='black', linestyle='--', linewidth=2)
    
    ax.set_xlabel('Vote Margin % (Negative = AIADMK, Positive = DMK)', fontsize=12)
    ax.set_ylabel('Number of Booths', fontsize=12)
    ax.set_title('Distribution of Vote Margins Across Booths - Uthiramerur', 
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {output_path}")


def create_booth_grid(data, output_path):
    """Create a grid visualization of all booths."""
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Sort booths by margin
    sorted_data = sorted(data, key=lambda x: float(x['margin_pct']))
    
    # Create grid (20 columns)
    cols = 20
    rows = (len(sorted_data) + cols - 1) // cols
    
    for idx, row in enumerate(sorted_data):
        x = idx % cols
        y = rows - 1 - (idx // cols)
        
        # Determine color based on category
        category = row['category']
        color = CATEGORY_COLORS.get(category, '#999999')
        
        rect = plt.Rectangle((x, y), 0.9, 0.9, facecolor=color, edgecolor='white', linewidth=0.5)
        ax.add_patch(rect)
        
        # Add booth number for swing booths
        if 'SWING' in category:
            ax.text(x + 0.45, y + 0.45, row['booth'][:3], ha='center', va='center', 
                   fontsize=5, color='white', fontweight='bold')
    
    ax.set_xlim(-0.5, cols + 0.5)
    ax.set_ylim(-0.5, rows + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='#FF6B6B', label='Swing DMK'),
        mpatches.Patch(facecolor='#69DB7C', label='Swing AIADMK'),
        mpatches.Patch(facecolor='#E03131', label='Lean DMK'),
        mpatches.Patch(facecolor='#2F9E44', label='Lean AIADMK'),
        mpatches.Patch(facecolor='#A61E1E', label='Strong DMK'),
        mpatches.Patch(facecolor='#1B6D2D', label='Strong AIADMK'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    
    ax.set_title('All 359 Booths - Sorted by Competitiveness\n(Most competitive at bottom-left)', 
                fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {output_path}")


def create_swing_focus_chart(data, output_path):
    """Create focused chart on swing booths."""
    swing_booths = [r for r in data if 'SWING' in r['category']]
    swing_booths = sorted(swing_booths, key=lambda x: float(x['margin_pct']))[:30]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    booths = [r['booth'][:8] for r in swing_booths]
    margins = [float(r['margin_pct']) for r in swing_booths]
    colors = [COLORS['DMK'] if r['winner'] == 'DMK' else COLORS['AIADMK'] for r in swing_booths]
    
    bars = ax.barh(booths, margins, color=colors, edgecolor='black')
    
    ax.axvline(x=0, color='black', linewidth=2)
    ax.axvline(x=5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Vote Margin %', fontsize=12)
    ax.set_ylabel('Booth Number', fontsize=12)
    ax.set_title('Top 30 Most Competitive (Swing) Booths - Uthiramerur\nThese booths decide elections!', 
                fontsize=14, fontweight='bold')
    
    # Add margin labels
    for bar, margin, row in zip(bars, margins, swing_booths):
        label = f"{margin:.1f}% ({row['margin']} votes)"
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
               label, va='center', fontsize=8)
    
    # Legend
    dmk_patch = mpatches.Patch(color=COLORS['DMK'], label='DMK Won')
    aiadmk_patch = mpatches.Patch(color=COLORS['AIADMK'], label='AIADMK Won')
    ax.legend(handles=[dmk_patch, aiadmk_patch], loc='lower right')
    
    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {output_path}")


def main():
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    
    # Load data
    csv_path = output_dir / "booth_classification_uthiramerur.csv"
    if not csv_path.exists():
        print(f"❌ Classification data not found: {csv_path}")
        print("   Run booth_classification.py first")
        return
    
    data = load_classification_data(csv_path)
    print(f"📊 Loaded {len(data)} booth records\n")
    
    # Generate all charts
    print("🎨 Generating visualizations...\n")
    
    create_pie_chart(data, charts_dir / "1_category_distribution.png")
    create_margin_histogram(data, charts_dir / "2_margin_distribution.png")
    create_booth_grid(data, charts_dir / "3_booth_grid.png")
    create_swing_focus_chart(data, charts_dir / "4_swing_booths_focus.png")
    
    print(f"\n✨ All charts saved to: {charts_dir}")


if __name__ == "__main__":
    main()
