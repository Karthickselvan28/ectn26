#!/usr/bin/env python3
"""
Download Form20 PDFs for Tamil Nadu Election constituencies.
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError


def download_pdf(url, output_path, max_retries=3):
    """Download a PDF with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"  Downloading: {url}")
            urlretrieve(url, output_path)
            file_size = os.path.getsize(output_path)
            print(f"  ✓ Downloaded: {file_size:,} bytes")
            return True
        except (URLError, HTTPError) as e:
            print(f"  ✗ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"  ✗ Failed after {max_retries} attempts")
                return False
    return False


def main():
    # Setup paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    raw_data_dir = base_dir / "raw_data"
    
    # Load constituency metadata
    constituencies_file = data_dir / "constituencies.json"
    if not constituencies_file.exists():
        print(f"Error: {constituencies_file} not found")
        sys.exit(1)
    
    with open(constituencies_file, 'r') as f:
        data = json.load(f)
    
    constituencies = data.get("kanchipuram_area", [])
    print(f"Found {len(constituencies)} constituencies to download\n")
    
    # Download each PDF
    success_count = 0
    failed = []
    
    for const in constituencies:
        ac_num = const["ac_number"]
        name = const["name"]
        url = const["pdf_url"]
        
        # Create filename
        filename = f"AC{ac_num}_{name.lower().replace(' ', '_')}.pdf"
        output_path = raw_data_dir / filename
        
        print(f"[{ac_num}] {name}")
        
        # Skip if already exists
        if output_path.exists():
            print(f"  ⊙ Already exists: {output_path.name}")
            success_count += 1
        else:
            if download_pdf(url, output_path):
                success_count += 1
            else:
                failed.append((ac_num, name))
        
        print()  # Blank line between downloads
    
    # Summary
    print("=" * 60)
    print(f"Download Summary:")
    print(f"  Success: {success_count}/{len(constituencies)}")
    if failed:
        print(f"  Failed: {len(failed)}")
        for ac_num, name in failed:
            print(f"    - AC{ac_num}: {name}")
    print("=" * 60)


if __name__ == "__main__":
    main()
