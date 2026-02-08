#!/usr/bin/env python3
"""
Geocode polling station addresses using Nominatim (OpenStreetMap).
Free service with 1 request/second rate limit.
"""

import json
import time
import csv
import requests
from pathlib import Path
from urllib.parse import quote


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    'User-Agent': 'TN-Elections-Analysis/1.0 (educational project)'
}

# Default center of Uthiramerur for fallback
UTHIRAMERUR_CENTER = (12.4850, 79.8960)


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
                    'display_name': results[0].get('display_name', ''),
                    'found': True
                }
            return None
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  Error geocoding: {e}")
                return None
    
    return None


def geocode_village(village):
    """Try to geocode just the village name + Uthiramerur."""
    if not village:
        return None
    
    address = f"{village}, Uthiramerur, Kanchipuram, Tamil Nadu, India"
    return geocode_address(address)


def geocode_all_stations(stations, output_path):
    """Geocode all polling stations."""
    geocoded = []
    success_count = 0
    village_cache = {}  # Cache village-level geocoding
    
    print(f"\n🗺️  Geocoding {len(stations)} polling stations...")
    print("   (Using Nominatim with 1s delay between requests)\n")
    
    for i, station in enumerate(stations):
        station_no = station['station_no']
        building = station['building']
        village = station['village']
        search_address = station.get('search_address', '')
        
        print(f"[{i+1}/{len(stations)}] Station {station_no}: {building[:40]}...", end=" ")
        
        # Try full address first
        result = geocode_address(search_address)
        
        # If not found, try village-level
        if not result and village:
            if village in village_cache:
                result = village_cache[village]
                print("(cached village)", end=" ")
            else:
                result = geocode_village(village)
                if result:
                    village_cache[village] = result
                    print("(village)", end=" ")
        
        if result:
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': result['lat'],
                'lng': result['lng'],
                'geocode_source': 'nominatim',
                'found': True
            })
            success_count += 1
            print(f"✓ ({result['lat']:.4f}, {result['lng']:.4f})")
        else:
            # Use village center or constituency center as fallback
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': UTHIRAMERUR_CENTER[0],
                'lng': UTHIRAMERUR_CENTER[1],
                'geocode_source': 'fallback',
                'found': False
            })
            print("✗ (using fallback)")
        
        # Rate limiting - 1 request per second
        time.sleep(1.1)
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Geocoded {success_count}/{len(stations)} stations successfully")
    print(f"📁 Saved to: {output_path}")
    
    return geocoded


def main():
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "data" / "uthiramerur_polling_stations.json"
    output_path = base_dir / "data" / "uthiramerur_booths_geocoded.json"
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print("   Run extract_booth_locations.py first")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)
    
    print(f"📄 Loaded {len(stations)} stations from {input_path}")
    
    # Geocode all
    geocoded = geocode_all_stations(stations, output_path)
    
    # Show summary
    found = sum(1 for s in geocoded if s['found'])
    print(f"\n📊 Summary:")
    print(f"   Found: {found} ({found/len(geocoded)*100:.1f}%)")
    print(f"   Fallback: {len(geocoded) - found}")


if __name__ == "__main__":
    main()
