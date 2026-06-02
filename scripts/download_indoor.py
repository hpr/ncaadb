#!/usr/bin/env python3
"""
Download NCAA Indoor Championships history pages from USTFCCCA.
"""

import requests
import time
import os
from pathlib import Path

BASE_URL = "https://www.ustfccca.org/records-lists/meet-history-by-event"
SERIES_INDOOR = "3368"  # NCAA Indoor Championships
SERIES_OUTDOOR = "3369"  # NCAA Outdoor Championships

EVENTS = {
    "55 Meters": "34",
    "55 Meter Hurdles": "51",
    "60 Meters": "1",
    "60 Meter Hurdles": "13",
    "100 Meters": "2",
    "100 Meter Hurdles": "14",
    "110 Meter Hurdles": "15",
    "200 Meters": "3",
    "300 Meters": "39",
    "300 Meter Hurdles": "59",
    "400 Meters": "4",
    "400 Meter Hurdles": "16",
    "500 Meters": "42",
    "600 Yards": "5",
    "600 Meters": "43",
    "800 Meters": "6",
    "1000 Meters": "7",
    "1500 Meters": "8",
    "1600 Meters": "46",
    "Mile": "9",
    "2000m Steeplechase": "94",
    "3000 Meters": "10",
    "Steeplechase": "17",
    "3200 Meters": "48",
    "Two Miles": "49",
    "5000 Meters": "11",
    "10,000 Meters": "12",
    "3000m Race Walk": "102",
    "5000m Race Walk": "103",
    "4x100 Relay": "18",
    "4x200 Relay": "62",
    "4x400 Relay": "19",
    "4x440 Yard Relay (Mile Relay)": "68",
    "4x800 Relay": "63",
    "4x880 Yard Relay": "69",
    "4x1500 Relay": "64",
    "4x1600 Relay": "65",
    "4xMile Relay": "70",
    "Sprint Medley Relay": "72",
    "Sprint Medley Relay, 800 Meters": "114",
    "Distance Medley Relay": "20",
    "Shuttle Hurdle Relay, Indoor 60m": "147",
    "Shuttle Hurdle Relay (w100H)": "71",
    "Shuttle Hurdle Relay (m110H)": "111",
    "High Jump": "21",
    "Pole Vault": "22",
    "Long Jump": "23",
    "Triple Jump": "24",
    "Shot Put": "25",
    "Discus": "26",
    "Hammer": "27",
    "Javelin": "28",
    "Weight Throw": "29",
    "Pentathlon": "30",
    "Heptathlon": "31",
    "Decathlon": "32"
}

GENDERS = {
    "men": "1",
    "women": "2"
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "html"
MAX_RETRIES = 5
RETRY_DELAY = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def download_page(event_name: str, event_id: str, gender: str, gender_id: str,
                  series: str = SERIES_INDOOR, prefix: str = "") -> bool:
    """Download a single page, return True if successful."""
    params = {
        "gender": gender_id,
        "series": series,
        "event": event_id
    }
    
    fname = f"{prefix}{gender}_{event_id}.html" if prefix else f"{gender}_{event_id}.html"
    output_file = OUTPUT_DIR / fname
    
    if output_file.exists():
        print(f"  Skipping {event_name} ({gender}) - already exists")
        return True
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: {event_name} ({gender})...", end=" ", flush=True)
            response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
            response.raise_for_status()
            
            content = response.text
            
            if "No results found" in content or len(content) < 5000:
                print("BLANK (no data)")
                return False
            
            output_file.write_text(content, encoding="utf-8")
            print(f"OK ({len(content):,} bytes)")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                print(f"500 error, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"HTTP error: {e}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return False
    
    print("Max retries exceeded")
    return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("Downloading NCAA Indoor Championships data from USTFCCCA...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    success_count = 0
    blank_count = 0
    
    for event_name, event_id in EVENTS.items():
        for gender, gender_id in GENDERS.items():
            result = download_page(event_name, event_id, gender, gender_id)
            if result:
                success_count += 1
            else:
                blank_count += 1
            time.sleep(0.1)
    
    print("\nDownloading NCAA Outdoor Championships women's 10000m...")
    result = download_page("10,000 Meters", "12", "women", "2",
                           series=SERIES_OUTDOOR, prefix="outdoor_")
    if result:
        success_count += 1
    else:
        blank_count += 1

    print()
    print(f"Done! Downloaded: {success_count}, Blank/Skipped: {blank_count}")
    print(f"Files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
