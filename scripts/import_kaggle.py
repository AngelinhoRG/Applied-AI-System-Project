"""
Import songs from data/spotify-tracks-dataset.csv into data/songs.csv.

Maps the Kaggle dataset's ~114 genre buckets to the 15 genres used by this
project, derives mood from energy + valence, deduplicates against the existing
catalog, and appends the result.

Usage:
    python scripts/import_kaggle.py                       # 100 songs per genre
    python scripts/import_kaggle.py --per-genre 50        # fewer songs per genre
    python scripts/import_kaggle.py --genres pop rock     # specific genres only
    python scripts/import_kaggle.py --all                 # no per-genre cap

The Kaggle CSV is expected at data/spotify-tracks-dataset.csv (default), but
can be overridden with --source.
"""

import argparse
import csv
import os
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Kaggle genre → project genre mapping
# Genres not listed here are skipped (too niche / no clean mapping).
# ---------------------------------------------------------------------------
KAGGLE_TO_GENRE: dict[str, str] = {
    # pop
    "pop":              "pop",
    "pop-film":         "pop",
    "power-pop":        "pop",
    "k-pop":            "pop",
    "j-pop":            "pop",
    "party":            "pop",
    "happy":            "pop",
    "anime":            "pop",
    "disney":           "pop",
    "show-tunes":       "pop",
    "j-dance":          "pop",
    "j-idol":           "pop",
    "cantopop":         "pop",
    "mandopop":         "pop",
    "swedish":          "pop",
    "french":           "pop",
    # rock
    "rock":             "rock",
    "alt-rock":         "rock",
    "alternative":      "rock",
    "hard-rock":        "rock",
    "psych-rock":       "rock",
    "rock-n-roll":      "rock",
    "punk":             "rock",
    "punk-rock":        "rock",
    "grunge":           "rock",
    "british":          "rock",
    "goth":             "rock",
    "j-rock":           "rock",
    "rockabilly":       "rock",
    # metal
    "metal":            "metal",
    "heavy-metal":      "metal",
    "black-metal":      "metal",
    "death-metal":      "metal",
    "metalcore":        "metal",
    "grindcore":        "metal",
    "hardcore":         "metal",
    "industrial":       "metal",
    # lofi
    "study":            "lofi",
    "chill":            "lofi",
    # ambient
    "ambient":          "ambient",
    "new-age":          "ambient",
    "sleep":            "ambient",
    # jazz
    "jazz":             "jazz",
    # r&b
    "r-n-b":            "r&b",
    "soul":             "r&b",
    "funk":             "r&b",
    "disco":            "r&b",
    "groove":           "r&b",
    "gospel":           "r&b",
    "romance":          "r&b",
    # hip-hop
    "hip-hop":          "hip-hop",
    "trip-hop":         "hip-hop",
    # blues
    "blues":            "blues",
    "sad":              "blues",
    # country
    "country":          "country",
    "honky-tonk":       "country",
    "bluegrass":        "country",
    # folk
    "folk":             "folk",
    "singer-songwriter": "folk",
    "songwriter":       "folk",
    "acoustic":         "folk",
    # classical
    "classical":        "classical",
    "piano":            "classical",
    "opera":            "classical",
    "guitar":           "classical",
    # edm
    "edm":              "edm",
    "dance":            "edm",
    "house":            "edm",
    "deep-house":       "edm",
    "chicago-house":    "edm",
    "progressive-house": "edm",
    "techno":           "edm",
    "detroit-techno":   "edm",
    "drum-and-bass":    "edm",
    "dubstep":          "edm",
    "trance":           "edm",
    "hardstyle":        "edm",
    "breakbeat":        "edm",
    "club":             "edm",
    "garage":           "edm",
    "minimal-techno":   "edm",
    "idm":              "edm",
    "electro":          "edm",
    "electronic":       "edm",
    "dub":              "edm",
    # synthwave
    "synth-pop":        "synthwave",
    # indie pop
    "indie-pop":        "indie pop",
    "indie":            "indie pop",
    "emo":              "indie pop",
    # reggae  (new genre)
    "reggae":           "reggae",
    "dancehall":        "reggae",
    "ska":              "reggae",
    "reggaeton":        "reggae",
    # latin  (new genre)
    "latin":            "latin",
    "latino":           "latin",
    "salsa":            "latin",
    "samba":            "latin",
    "tango":            "latin",
    "brazil":           "latin",
    "forro":            "latin",
    "sertanejo":        "latin",
    "mpb":              "latin",
    "pagode":           "latin",
    "spanish":          "latin",
    # world  (new genre)
    "world-music":      "world",
    "afrobeat":         "world",
    "indian":           "world",
    "iranian":          "world",
    "turkish":          "world",
    "malay":            "world",
    # skipped: children, kids, comedy, german
}

CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
]


def derive_mood(energy: float, valence: float) -> str:
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
    if energy >= 0.35:
        if valence >= 0.70:
            return "relaxed"
        if valence < 0.35:
            return "sad"
        return "chill"
    if valence >= 0.72:
        return "dreamy"
    if valence < 0.35:
        return "melancholic" if valence < 0.25 else "sad"
    return "chill"


def load_existing(csv_path: str) -> tuple[set[tuple[str, str]], int]:
    existing: set[tuple[str, str]] = set()
    max_id = 0
    if not os.path.exists(csv_path):
        return existing, max_id
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add((row["title"].strip().lower(), row["artist"].strip().lower()))
            max_id = max(max_id, int(row["id"]))
    return existing, max_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import Kaggle Spotify dataset into songs.csv"
    )
    parser.add_argument(
        "--source",
        default="data/spotify-tracks-dataset.csv",
        metavar="PATH",
        help="Path to the Kaggle CSV (default: data/spotify-tracks-dataset.csv)",
    )
    parser.add_argument(
        "--csv",
        default="data/songs.csv",
        metavar="PATH",
        help="Path to the output catalog (default: data/songs.csv)",
    )
    parser.add_argument(
        "--genres",
        nargs="+",
        choices=sorted(set(KAGGLE_TO_GENRE.values())),
        default=sorted(set(KAGGLE_TO_GENRE.values())),
        metavar="GENRE",
        help="Which project genres to import (default: all mapped genres)",
    )
    parser.add_argument(
        "--per-genre",
        type=int,
        default=100,
        metavar="N",
        help="Max new songs per project genre (default: 100). Use --all to disable.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Import all matching songs with no per-genre cap",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        metavar="N",
        help="Random seed for sampling (default: 42)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.source):
        sys.exit(f"Source file not found: {args.source}")

    target_genres = set(args.genres)
    per_genre_cap = None if args.all else args.per_genre

    # ── Load existing catalog ─────────────────────────────────────────────────
    existing, next_id = load_existing(args.csv)
    next_id += 1
    print(f"Existing catalog : {len(existing)} songs (next id = {next_id})")
    print(f"Source           : {args.source}")
    print(f"Per-genre cap    : {'none' if per_genre_cap is None else per_genre_cap}")
    print(f"Target genres    : {', '.join(sorted(target_genres))}\n")

    # ── Read and bucket Kaggle rows ───────────────────────────────────────────
    # Bucket rows by project genre first so we can sample evenly.
    buckets: dict[str, list[dict]] = {g: [] for g in target_genres}
    skipped_no_map = 0
    skipped_bad_data = 0

    with open(args.source, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kaggle_genre = row.get("track_genre", "").strip().lower()
            project_genre = KAGGLE_TO_GENRE.get(kaggle_genre)
            if project_genre not in target_genres:
                skipped_no_map += 1
                continue

            try:
                energy       = float(row["energy"])
                valence      = float(row["valence"])
                tempo        = float(row["tempo"])
                danceability = float(row["danceability"])
                acousticness = float(row["acousticness"])
            except (ValueError, KeyError):
                skipped_bad_data += 1
                continue

            title  = row["track_name"].strip()
            artist = row["artists"].strip()
            if not title or not artist:
                skipped_bad_data += 1
                continue

            buckets[project_genre].append({
                "title":        title,
                "artist":       artist,
                "genre":        project_genre,
                "mood":         derive_mood(energy, valence),
                "energy":       round(energy, 2),
                "tempo_bpm":    int(tempo),
                "valence":      round(valence, 2),
                "danceability": round(danceability, 2),
                "acousticness": round(acousticness, 2),
            })

    # ── Sample, deduplicate, assign IDs ──────────────────────────────────────
    rng = random.Random(args.seed)
    new_rows: list[dict] = []
    seen_this_run: set[tuple[str, str]] = set()

    for genre in sorted(target_genres):
        candidates = buckets[genre]
        rng.shuffle(candidates)

        added = 0
        for song in candidates:
            if per_genre_cap is not None and added >= per_genre_cap:
                break
            key = (song["title"].lower(), song["artist"].lower())
            if key in existing or key in seen_this_run:
                continue
            seen_this_run.add(key)
            new_rows.append({"id": next_id, **song})
            next_id += 1
            added += 1

        print(f"  {genre:<12}  {added:>4} added  ({len(candidates):>5} candidates)")

    print(f"\n  Skipped (no genre mapping) : {skipped_no_map:,}")
    print(f"  Skipped (bad/missing data) : {skipped_bad_data:,}")

    if not new_rows:
        print("\nNo new songs to add.")
        return

    # ── Append to CSV ─────────────────────────────────────────────────────────
    file_exists = os.path.exists(args.csv)
    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)

    if file_exists:
        with open(args.csv, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")

    with open(args.csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    total = len(existing) + len(new_rows)
    print(f"\nDone. Added {len(new_rows):,} songs → {args.csv}")
    print(f"Catalog now contains {total:,} songs.")


if __name__ == "__main__":
    main()
