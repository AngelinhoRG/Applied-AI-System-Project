"""
One-time migration: backfill popularity into data/songs.csv.

- Songs matched in the Kaggle dataset: get real popularity values.
- Original 18 fictional songs (not in Kaggle): Gemini estimates popularity.
- Non-original songs without Kaggle match: removed from catalog.

Run once, then delete this script.
"""

import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
except ImportError:
    sys.exit("google-genai is not installed.")

SONGS_CSV = "data/songs.csv"
KAGGLE_CSV = "data/spotify-tracks-dataset.csv"

ORIGINAL_IDS = set(range(1, 19))  # ids 1–18 are the original fictional songs

CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness", "popularity",
]


def build_kaggle_lookup() -> dict[tuple[str, str], int]:
    """Return (title.lower(), artist.lower()) -> popularity from Kaggle CSV."""
    lookup: dict[tuple[str, str], int] = {}
    with open(KAGGLE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row.get("track_name", "").strip().lower()
            artist = row.get("artists", "").strip().lower()
            try:
                pop = int(float(row["popularity"]))
            except (ValueError, KeyError):
                continue
            if title and artist:
                key = (title, artist)
                # Keep the higher popularity if duplicated across genre buckets
                if key not in lookup or pop > lookup[key]:
                    lookup[key] = pop
    return lookup


def estimate_popularity_with_gemini(songs: list[dict]) -> dict[int, int]:
    """Ask Gemini to estimate Spotify popularity (0-100) for a list of songs.
    Returns a dict of {song_id: popularity_int}."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)

    numbered = "\n".join(
        f'{s["id"]}. "{s["title"]}" by {s["artist"]} (genre: {s["genre"]})'
        for s in songs
    )

    prompt = f"""Estimate the Spotify popularity score (integer 0–100) for each of these songs.
These are fictional/hypothetical songs, so base your estimate on how popular a real song
with this style, genre, and artist type might be. 70+ = mainstream, 40-69 = moderate, <40 = niche.

Songs:
{numbered}

Return ONLY a JSON object mapping the song number (as a string) to the popularity integer.
Example: {{"1": 72, "2": 45, "3": 88}}
No markdown, no explanation."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        raw = "\n".join(inner).strip()

    data = json.loads(raw)
    return {int(k): int(v) for k, v in data.items()}


def main() -> None:
    print("Building Kaggle popularity lookup...")
    kaggle_lookup = build_kaggle_lookup()
    print(f"  {len(kaggle_lookup):,} unique (title, artist) pairs in Kaggle")

    print("Reading songs.csv...")
    with open(SONGS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"  {len(rows):,} songs loaded")

    originals_for_gemini = []
    kept_rows = []
    dropped = 0

    for row in rows:
        song_id = int(row["id"])
        key = (row["title"].strip().lower(), row["artist"].strip().lower())

        if key in kaggle_lookup:
            row["popularity"] = str(kaggle_lookup[key])
            kept_rows.append(row)
        elif song_id in ORIGINAL_IDS:
            row["popularity"] = ""  # will be filled in after Gemini call
            kept_rows.append(row)
            originals_for_gemini.append(row)
        else:
            dropped += 1

    print(f"  Matched from Kaggle : {len(kept_rows) - len(originals_for_gemini):,}")
    print(f"  Originals for Gemini: {len(originals_for_gemini)}")
    print(f"  Dropped (no match)  : {dropped:,}")

    if originals_for_gemini:
        print("\nEstimating popularity for original songs via Gemini...")
        estimates = estimate_popularity_with_gemini(originals_for_gemini)
        print(f"  Got estimates for {len(estimates)} songs")

        for row in kept_rows:
            song_id = int(row["id"])
            if song_id in ORIGINAL_IDS and song_id in estimates:
                row["popularity"] = str(estimates[song_id])
                print(f"    [{song_id}] {row['title']} → {estimates[song_id]}")

    print(f"\nWriting {len(kept_rows):,} songs back to {SONGS_CSV}...")
    with open(SONGS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"Done. Catalog now has {len(kept_rows):,} songs with popularity values.")


if __name__ == "__main__":
    main()
