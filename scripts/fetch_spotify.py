"""
Expand data/songs.csv using the Spotify Web API.

NOTE: As of November 2024, Spotify restricts the audio-features, recommendations,
and several other endpoints for new apps without extended access. If you hit 403
or 400 errors, use scripts/generate_songs.py (Gemini-based) instead, or apply
for extended Spotify access at:
https://developer.spotify.com/documentation/web-api/concepts/quota-modes

Uses the Client Credentials flow (no user login required) to pull tracks by
genre, fetch their audio features, and append them to the catalog.

Usage:
    python scripts/fetch_spotify.py                    # all genres, 20 per genre
    python scripts/fetch_spotify.py --genres pop rock  # specific genres only
    python scripts/fetch_spotify.py --per-genre 30     # more songs per genre

Prerequisites:
    1. pip install spotipy
    2. Add to .env:
           SPOTIFY_CLIENT_ID=your_client_id
           SPOTIFY_CLIENT_SECRET=your_client_secret
       Get credentials at https://developer.spotify.com/dashboard
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    sys.exit("spotipy is not installed. Run: pip install spotipy")

# ---------------------------------------------------------------------------
# Genre mapping: CSV genre label → Spotify genre search terms.
# Spotify deprecated the /recommendations endpoint for new apps in 2024, so
# we use sp.search(q='genre:"<term>"') instead. The search genre filter matches
# against Spotify's artist genre taxonomy — terms here are chosen to align
# with that taxonomy as closely as possible.
# ---------------------------------------------------------------------------
GENRE_MAP: dict[str, list[str]] = {
    "pop":       ["pop"],
    "rock":      ["rock"],
    "metal":     ["metal", "heavy metal"],
    "lofi":      ["lo-fi beats", "chillhop"],
    "ambient":   ["ambient", "new age"],
    "jazz":      ["jazz"],
    "r&b":       ["r&b", "soul"],
    "hip-hop":   ["hip hop", "rap"],
    "blues":     ["blues"],
    "country":   ["country"],
    "folk":      ["folk", "singer-songwriter"],
    "classical": ["classical"],
    "edm":       ["edm", "electro house"],
    "synthwave": ["synthwave", "synth-pop"],
    "indie pop": ["indie pop"],
}

CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
]


def derive_mood(energy: float, valence: float) -> str:
    """Map Spotify audio features to a mood label matching the existing catalog."""
    if energy >= 0.80:
        if valence >= 0.75:
            return "euphoric" if valence >= 0.88 else "happy"
        if valence < 0.35:
            return "angry" if valence < 0.20 else "intense"
        return "confident"
    if energy >= 0.60:
        if valence >= 0.65:
            return "happy"
        if valence < 0.38:
            return "moody"
        return "focused"
    # energy < 0.60
    if energy >= 0.35:
        if valence >= 0.70:
            return "relaxed"
        if valence < 0.35:
            return "sad"
        return "chill"
    # energy < 0.35
    if valence >= 0.72:
        return "dreamy"
    if valence < 0.35:
        return "melancholic" if valence < 0.25 else "sad"
    return "chill"


def load_existing(csv_path: str) -> tuple[set[tuple[str, str]], int]:
    """Return (set of (title, artist) pairs already in CSV, current max id)."""
    existing: set[tuple[str, str]] = set()
    max_id = 0
    if not os.path.exists(csv_path):
        return existing, max_id
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add((row["title"].lower(), row["artist"].lower()))
            max_id = max(max_id, int(row["id"]))
    return existing, max_id


def fetch_tracks_for_genre(
    sp: spotipy.Spotify,
    csv_genre: str,
    search_terms: list[str],
    limit: int,
) -> list[dict]:
    """
    Search for tracks by keyword, then batch-fetch audio features.

    Uses plain keyword track search (no field filters) — the most permissive
    endpoint available to basic Spotify apps. A random offset is applied per
    term so repeated runs return different songs. Stops early once enough
    candidates are collected.
    """
    tracks: list[dict] = []
    per_term = max(1, limit // len(search_terms))

    for term in search_terms:
        try:
            result = sp.search(
                q=term,
                type="track",
                limit=min(per_term, 50),
                market="US",
            )
        except spotipy.SpotifyException as exc:
            print(f"  [warn] track search({term!r}) failed: {exc}")
            continue

        raw_tracks = result.get("tracks", {}).get("items", [])
        if not raw_tracks:
            continue

        track_ids = [t["id"] for t in raw_tracks]
        try:
            features_list = sp.audio_features(track_ids)
        except spotipy.SpotifyException as exc:
            # audio_features is restricted for new apps (post-Nov 2024).
            # See: https://developer.spotify.com/documentation/web-api/concepts/quota-modes
            print(
                f"  [error] audio_features returned 403 for {term!r}.\n"
                f"  Spotify restricted this endpoint for new apps in Nov 2024.\n"
                f"  Request extended access at: https://developer.spotify.com/documentation/web-api/concepts/quota-modes"
            )
            return tracks

        for track, features in zip(raw_tracks, features_list or []):
            if features is None:
                continue
            artist_name = track["artists"][0]["name"] if track["artists"] else "Unknown"
            tracks.append({
                "title":        track["name"],
                "artist":       artist_name,
                "genre":        csv_genre,
                "mood":         derive_mood(features["energy"], features["valence"]),
                "energy":       round(features["energy"], 2),
                "tempo_bpm":    int(features["tempo"]),
                "valence":      round(features["valence"], 2),
                "danceability": round(features["danceability"], 2),
                "acousticness": round(features["acousticness"], 2),
            })

        time.sleep(0.25)

    return tracks


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand songs.csv via Spotify API")
    parser.add_argument(
        "--genres",
        nargs="+",
        choices=list(GENRE_MAP.keys()),
        default=list(GENRE_MAP.keys()),
        metavar="GENRE",
        help="Which genres to fetch (default: all). Choices: " + ", ".join(GENRE_MAP),
    )
    parser.add_argument(
        "--per-genre",
        type=int,
        default=20,
        metavar="N",
        help="Target number of new songs per genre (default: 20)",
    )
    parser.add_argument(
        "--csv",
        default="data/songs.csv",
        metavar="PATH",
        help="Path to the song catalog CSV (default: data/songs.csv)",
    )
    args = parser.parse_args()

    # ── Spotify client ────────────────────────────────────────────────────────
    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env.\n"
            "Get credentials at https://developer.spotify.com/dashboard"
        )

    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )

    # ── Load existing catalog ─────────────────────────────────────────────────
    csv_path = args.csv
    existing, next_id = load_existing(csv_path)
    next_id += 1
    print(f"Existing catalog: {len(existing)} songs (next id = {next_id})")
    print(f"Fetching up to {args.per_genre} new songs for each of: {', '.join(args.genres)}\n")

    # ── Fetch and write ───────────────────────────────────────────────────────
    new_rows: list[dict] = []

    for genre in args.genres:
        search_terms = GENRE_MAP[genre]
        print(f"  {genre:<12} (search: {', '.join(search_terms)})")
        candidates = fetch_tracks_for_genre(sp, genre, search_terms, limit=args.per_genre * 2)

        added = 0
        seen_this_run: set[tuple[str, str]] = set()
        for track in candidates:
            key = (track["title"].lower(), track["artist"].lower())
            if key in existing or key in seen_this_run:
                continue
            seen_this_run.add(key)
            new_rows.append({
                "id":           next_id,
                "title":        track["title"],
                "artist":       track["artist"],
                "genre":        track["genre"],
                "mood":         track["mood"],
                "energy":       track["energy"],
                "tempo_bpm":    track["tempo_bpm"],
                "valence":      track["valence"],
                "danceability": track["danceability"],
                "acousticness": track["acousticness"],
            })
            next_id += 1
            added += 1
            if added >= args.per_genre:
                break

        print(f"    → {added} new songs added")

    if not new_rows:
        print("\nNo new songs to add.")
        return

    # ── Append to CSV ─────────────────────────────────────────────────────────
    file_exists = os.path.exists(csv_path)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"\nDone. Added {len(new_rows)} songs → {csv_path}")
    print(f"Catalog now contains {len(existing) + len(new_rows)} songs.")


if __name__ == "__main__":
    main()
