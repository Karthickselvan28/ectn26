#!/usr/bin/env python3
"""
Smart geocoding using Google Maps API with building name caching.
Groups similar buildings (same school, different sections) to share coordinates.
"""

import json
import re
import os
import time
import requests
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Stats tracking
api_calls_made = 0
MAX_API_CALLS = 1000


def normalize_building(building):
    """Normalize building name to core identity for caching."""
    text = building.upper()
    
    # Remove directional and structural suffixes
    remove_patterns = [
        r',?\s*(EAST|WEST|NORTH|SOUTH)\s*(FACING|BUILDING|SIDE|WING|PORTION)?\s*',
        r',?\s*(NEW|OLD)\s*(BUILDING|BLOCK)?\s*',
        r',?\s*ROOM\s*NO\.?\s*\d+\s*',
        r',?\s*HALL\s*NO\.?\s*\d+\s*',
        r',?\s*BLOCK\s*[A-Z0-9]+\s*',
        r',?\s*(LEFT|RIGHT|MIDDLE|CENTRE|CENTER)\s*(PORTION|SIDE|WING)?\s*',
        r',?\s*DOWN\s*STAIR[S]?\s*',
        r',?\s*UP\s*STAIR[S]?\s*',
        r',?\s*GROUND\s*FLOOR\s*',
        r',?\s*FIRST\s*FLOOR\s*',
        r'\s+JVVD\s+',
    ]
    for pattern in remove_patterns:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    
    # Clean up
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r',\s*$', '', text)
    
    return text


def geocode_google(address, retries=2):
    """Geocode using Google Maps API."""
    global api_calls_made
    
    if api_calls_made >= MAX_API_CALLS:
        print(f"\n⚠️  Max API calls ({MAX_API_CALLS}) reached!")
        return None
    
    params = {
        'address': address,
        'key': GOOGLE_API_KEY,
        'region': 'in'  # Bias towards India
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
            api_calls_made += 1
            
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
                print(f"\n⚠️  API quota exceeded!")
                return None
            else:
                if attempt < retries - 1:
                    time.sleep(0.5)
                    
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5)
    
    return None


def geocode_constituency(const_name, stations, output_path, fallback_center):
    """Geocode all stations for a constituency using caching."""
    global api_calls_made
    
    geocoded = []
    cache = {}  # Cache by normalized building name
    cached_hits = 0
    successful = 0
    
    print(f"\n🗺️  Geocoding {len(stations)} stations for {const_name}...")
    print(f"   API calls used so far: {api_calls_made}/{MAX_API_CALLS}\n")
    
    for i, station in enumerate(stations):
        building = station.get('building', '')
        station_no = station.get('station_no', station.get('sl_no', i+1))
        village = station.get('village', '')
        
        normalized = normalize_building(building)
        
        print(f"[{i+1}/{len(stations)}] Station {station_no}: {building[:40]}...", end=" ", flush=True)
        
        # Check cache first
        if normalized in cache:
            result = cache[normalized]
            cached_hits += 1
            print(f"(cached)", end=" ")
        else:
            # Build search address
            search_parts = [building]
            if village:
                search_parts.append(village)
            search_parts.extend([const_name, "Kanchipuram", "Tamil Nadu", "India"])
            search_address = ", ".join(filter(None, search_parts))
            
            result = geocode_google(search_address)
            
            # If failed, try with just village + constituency
            if not result and village:
                fallback_address = f"{village}, {const_name}, Kanchipuram, Tamil Nadu, India"
                result = geocode_google(fallback_address)
            
            # Cache the result (even if None)
            cache[normalized] = result
            
            # Small delay to be nice to the API
            time.sleep(0.1)
        
        if result:
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': result['lat'],
                'lng': result['lng'],
                'found': True
            })
            successful += 1
            print(f"✓ ({result['lat']:.4f}, {result['lng']:.4f})")
        else:
            geocoded.append({
                'station_no': station_no,
                'building': building,
                'village': village,
                'lat': fallback_center[0],
                'lng': fallback_center[1],
                'found': False
            })
            print("✗ (fallback)")
        
        # Check API limit
        if api_calls_made >= MAX_API_CALLS:
            print(f"\n⚠️  Stopping - API limit reached")
            break
    
    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geocoded, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ {const_name}: {successful}/{len(stations)} geocoded")
    print(f"   Cache hits: {cached_hits} | API calls: {api_calls_made}")
    print(f"📁 Saved: {output_path}")
    
    return geocoded


def main():
    global api_calls_made
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_MAPS_API_KEY not found in .env file")
        return
    
    print(f"🔑 Using Google Maps API Key: {GOOGLE_API_KEY[:10]}...")
    print(f"📊 Max API calls allowed: {MAX_API_CALLS}\n")
    
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    # Constituency configs: (name, ac_number, fallback_center)
    constituencies = [
        ("alandur", "028", (13.0024, 80.2065)),
        ("sriperumbudur", "029", (12.9707, 79.9447)),
        ("kancheepuram", "037", (12.8342, 79.7036)),
        ("uthiramerur", "036", (12.6149, 79.7594)),
    ]
    
    for const_name, ac_number, center in constituencies:
        input_path = data_dir / f"{const_name}_polling_stations.json"
        output_path = data_dir / f"{const_name}_booths_geocoded.json"
        
        if not input_path.exists():
            print(f"⏭️  Skipping {const_name} - input file not found")
            continue
        
        # Skip if already geocoded
        if output_path.exists():
            with open(output_path) as f:
                existing = json.load(f)
            # Check if using Google (not fallback)
            found_count = sum(1 for s in existing if s.get('found', False))
            if found_count > 0:
                print(f"⏭️  Skipping {const_name} - already geocoded ({found_count} found)")
                continue
        
        with open(input_path, 'r', encoding='utf-8') as f:
            stations = json.load(f)
        
        geocode_constituency(const_name, stations, output_path, center)
        
        if api_calls_made >= MAX_API_CALLS:
            print(f"\n🛑 Stopping - API limit reached ({api_calls_made}/{MAX_API_CALLS})")
            break
    
    print(f"\n✨ Done! Total API calls: {api_calls_made}/{MAX_API_CALLS}")


if __name__ == "__main__":
    main()
