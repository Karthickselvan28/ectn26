#!/usr/bin/env python3
"""
Geocode polling station addresses using Google Maps Geocoding API.
API key is loaded from .env file for security.
"""

import json
import time
import os
from pathlib import Path

# Load environment variables from .env file
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

import requests

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Default center of Uthiramerur for fallback
UTHIRAMERUR_CENTER = (12.4850, 79.8960)


def get_api_key():
    """Get API key from environment."""
    key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not key or key == 'YOUR_API_KEY_HERE':
        print("❌ Google Maps API key not found!")
        print("\n📝 To set up your API key:")
        print("   1. Open: /Users/karthikselvan/Desktop/eeze/tn_elections_2021/.env")
        print("   2. Replace YOUR_API_KEY_HERE with your actual API key")
        print("\n🔑 Get an API key from: https://console.cloud.google.com/apis/credentials")
        print("   Make sure to enable 'Geocoding API' for your project")
        return None
    return key


def geocode_address(address, api_key, retries=2):
    """Geocode a single address using Google Maps."""
    params = {
        'address': address,
        'key': api_key,
        'region': 'in'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return {
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'formatted_address': data['results'][0].get('formatted_address', ''),
                    'found': True
                }
            elif data['status'] == 'ZERO_RESULTS':
                return None
            elif data['status'] == 'OVER_QUERY_LIMIT':
                print("  ⚠️ Rate limited, waiting...")
                time.sleep(2)
            else:
                print(f"  Error: {data['status']}")
                return None
                
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  Request error: {e}")
                return None
    
    return None


def geocode_all_stations(stations, api_key, output_path):
    """Geocode all polling stations."""
    geocoded = []
    success_count = 0
    village_cache = {}
    
    print(f"\n🗺️  Geocoding {len(stations)} polling stations with Google Maps...")
    print("   (Results are cached per village to reduce API calls)\n")
    
    for i, station in enumerate(stations):
        station_no = station['station_no']
        building = station['building']
        village = station['village']
        
        print(f"[{i+1}/{len(stations)}] Station {station_no}: {village}...", end=" ")
        
        # Try village-level first (more reliable, uses cache)
        if village in village_cache:
            result = village_cache[village]
            print("(cached)", end=" ")
        else:
            # Geocode village + Uthiramerur
            search_address = f"{village}, Uthiramerur, Kanchipuram, Tamil Nadu, India"
            result = geocode_address(search_address, api_key)
            if result:
                village_cache[village] = result
        
        if result:
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': result['lat'],
                'lng': result['lng'],
                'geocode_source': 'google',
                'found': True
            })
            success_count += 1
            print(f"✓ ({result['lat']:.4f}, {result['lng']:.4f})")
        else:
            # Fallback to constituency center
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': UTHIRAMERUR_CENTER[0],
                'lng': UTHIRAMERUR_CENTER[1],
                'geocode_source': 'fallback',
                'found': False
            })
            print("✗ (fallback)")
        
        # Small delay to be nice to API
        time.sleep(0.1)
    
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
    
    # Check API key
    api_key = get_api_key()
    if not api_key:
        return
    
    print(f"✅ API key loaded successfully")
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print("   Run extract_booth_locations.py first")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        stations = json.load(f)
    
    print(f"📄 Loaded {len(stations)} stations from {input_path}")
    
    # Get unique villages for efficient geocoding
    unique_villages = set(s['village'] for s in stations if s['village'])
    print(f"🏘️  Found {len(unique_villages)} unique villages to geocode")
    
    # Geocode all
    geocoded = geocode_all_stations(stations, api_key, output_path)
    
    # Summary
    found = sum(1 for s in geocoded if s['found'])
    print(f"\n📊 Summary:")
    print(f"   Found: {found} ({found/len(geocoded)*100:.1f}%)")
    print(f"   Unique villages geocoded: {len(set(s['village'] for s in geocoded if s['found']))}")


if __name__ == "__main__":
    main()
