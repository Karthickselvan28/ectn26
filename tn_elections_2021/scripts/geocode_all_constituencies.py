#!/usr/bin/env python3
"""
Geocode polling stations for multiple constituencies using Nominatim.
"""

import json
import time
import requests
from pathlib import Path


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    'User-Agent': 'TN-Elections-Analysis/1.0 (educational project)'
}

# Default centers for fallback
CONSTITUENCY_CENTERS = {
    'alandur': (13.0024, 80.2065),
    'sriperumbudur': (12.9707, 79.9447),
    'kancheepuram': (12.8342, 79.7036),
    'uthiramerur': (12.6149, 79.7594),
}


def geocode_address(address, retries=2):
    """Geocode a single address using Nominatim."""
    params = {
        'q': address,
        'format': 'json',
        'limit': 1,
        'countrycodes': 'in'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            if results:
                return {
                    'lat': float(results[0]['lat']),
                    'lng': float(results[0]['lon']),
                    'found': True
                }
            return None
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None


def geocode_constituency(const_name, stations, output_path, center):
    """Geocode all stations for a constituency."""
    geocoded = []
    success_count = 0
    village_cache = {}
    
    print(f"\n🗺️  Geocoding {len(stations)} stations for {const_name}...")
    print("   (Using Nominatim with 1s delay between requests)\n")
    
    for i, station in enumerate(stations):
        station_no = station.get('station_no', station.get('sl_no', i+1))
        building = station.get('building', '')
        village = station.get('village', '')
        search_address = station.get('search_address', f"{building}, {const_name}, Tamil Nadu, India")
        
        print(f"[{i+1}/{len(stations)}] Station {station_no}: {building[:35]}...", end=" ", flush=True)
        
        # Try full address first
        result = geocode_address(search_address)
        
        # If not found, try village-level
        if not result and village:
            if village in village_cache:
                result = village_cache[village]
            else:
                village_address = f"{village}, {const_name}, Kanchipuram, Tamil Nadu, India"
                result = geocode_address(village_address)
                if result:
                    village_cache[village] = result
        
        if result:
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': result['lat'],
                'lng': result['lng'],
                'found': True
            })
            success_count += 1
            print(f"✓ ({result['lat']:.4f}, {result['lng']:.4f})")
        else:
            # Use constituency center as fallback
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': center[0],
                'lng': center[1],
                'found': False
            })
            print("✗ (fallback)")
        
        # Rate limiting
        time.sleep(1.1)
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Geocoded {success_count}/{len(stations)} stations successfully")
    print(f"📁 Saved to: {output_path}")
    
    return geocoded


def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    constituencies = [
        ("alandur", "028"),
        ("sriperumbudur", "029"),
        ("kancheepuram", "037"),
    ]
    
    for const_name, ac_number in constituencies:
        input_path = data_dir / f"{const_name}_polling_stations.json"
        output_path = data_dir / f"{const_name}_booths_geocoded.json"
        
        if not input_path.exists():
            print(f"❌ Input not found: {input_path}")
            continue
        
        # Skip if already geocoded
        if output_path.exists():
            print(f"⏭️  Skipping {const_name} (already geocoded)")
            continue
        
        with open(input_path, 'r', encoding='utf-8') as f:
            stations = json.load(f)
        
        center = CONSTITUENCY_CENTERS.get(const_name, (12.8, 79.8))
        geocode_constituency(const_name, stations, output_path, center)


if __name__ == "__main__":
    main()
