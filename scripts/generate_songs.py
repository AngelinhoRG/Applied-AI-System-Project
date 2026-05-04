"""
Expand data/songs.csv using the Gemini API.

Gemini generates real songs per genre with estimated audio attributes
(energy, valence, tempo, etc.) based on its knowledge of the song catalog.
This is the recommended catalog expansion method for apps without Spotify
extended API access.

Usage:
    python scripts/generate_songs.py                    # all genres, 20 per genre
    python scripts/generate_songs.py --genres pop rock  # specific genres only
    python scripts/generate_songs.py --per-genre 30     # more songs per genre

Prerequisites:
    GEMINI_API_KEY must be set in .env (already required for the main app).
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
except ImportError:
    sys.exit("google-genai is not installed. Run: pip install google-genai")

GENRES = [
    "pop", "rock", "metal", "lofi", "ambient", "jazz", "r&b",
    "hip-hop", "blues", "country", "folk", "classical", "edm",
    "synthwave", "indie pop", "reggae", "latin", "world",
]

MOOD_LABELS = [
    "happy", "chill", "intense", "focused", "relaxed", "moody",
    "nostalgic", "romantic", "melancholic", "angry", "euphoric",
    "sad", "dreamy", "confident",
]

CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
]

SYSTEM_PROMPT = """\
You are a music data expert who generates structured song catalog data.
When asked for songs in a genre, return ONLY a valid JSON array — no markdown,
no explanation, no code fences. Every field must be present and correctly typed.
Songs must be real, existing recordings."""


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


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Gemini wraps its output in them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence line and closing fence line
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


def generate_songs_for_genre(
    client: genai.Client,
    genre: str,
    n: int,
) -> list[dict]:
    """Ask Gemini for n real songs in the given genre with estimated audio features."""
    prompt = f"""\
Generate a JSON array of {n} real, well-known songs in the "{genre}" genre.

For each song provide:
- "title"       : string  — actual song title
- "artist"      : string  — actual artist or band name
- "mood"        : string  — one of: {", ".join(MOOD_LABELS)}
- "energy"      : float 0.0–1.0  (high = driving/loud/intense, low = calm/quiet)
- "tempo_bpm"   : integer        (typical beats per minute for this song)
- "valence"     : float 0.0–1.0  (high = happy/bright/positive, low = sad/dark)
- "danceability": float 0.0–1.0  (how suitable for dancing)
- "acousticness": float 0.0–1.0  (1.0 = fully acoustic, 0.0 = fully electronic)

Rules:
- Every song must be a real, existing recording.
- Vary the mood and energy across the {n} songs — do not return {n} identical moods.
- Return ONLY the JSON array, nothing else.

Example of one entry:
{{"title": "Blinding Lights", "artist": "The Weeknd", "mood": "confident", \
"energy": 0.80, "tempo_bpm": 171, "valence": 0.33, "danceability": 0.51, "acousticness": 0.00}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.4,
        ),
        contents=prompt,
    )

    raw = _strip_fences(response.text)
    songs = json.loads(raw)

    if not isinstance(songs, list):
        raise ValueError(f"Expected a JSON array, got: {type(songs)}")

    return songs


def validate_row(song: dict, genre: str) -> dict | None:
    """Return a cleaned row dict, or None if required fields are missing/invalid."""
    required = {"title", "artist", "mood", "energy", "tempo_bpm", "valence",
                "danceability", "acousticness"}
    if not required.issubset(song.keys()):
        return None
    try:
        return {
            "title":        str(song["title"]).strip(),
            "artist":       str(song["artist"]).strip(),
            "genre":        genre,
            "mood":         str(song["mood"]).strip().lower(),
            "energy":       round(float(song["energy"]), 2),
            "tempo_bpm":    int(song["tempo_bpm"]),
            "valence":      round(float(song["valence"]), 2),
            "danceability": round(float(song["danceability"]), 2),
            "acousticness": round(float(song["acousticness"]), 2),
        }
    except (ValueError, TypeError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Expand songs.csv using Gemini-generated song data"
    )
    parser.add_argument(
        "--genres",
        nargs="+",
        choices=GENRES,
        default=GENRES,
        metavar="GENRE",
        help="Which genres to generate (default: all). Choices: " + ", ".join(GENRES),
    )
    parser.add_argument(
        "--per-genre",
        type=int,
        default=20,
        metavar="N",
        help="Number of new songs to add per genre (default: 20)",
    )
    parser.add_argument(
        "--csv",
        default="data/songs.csv",
        metavar="PATH",
        help="Path to the song catalog CSV (default: data/songs.csv)",
    )
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "GEMINI_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    client = genai.Client(api_key=api_key)

    csv_path = args.csv
    existing, next_id = load_existing(csv_path)
    next_id += 1
    print(f"Existing catalog: {len(existing)} songs (next id = {next_id})")
    print(f"Generating {args.per_genre} new songs for each of: {', '.join(args.genres)}\n")

    new_rows: list[dict] = []

    for genre in args.genres:
        print(f"  {genre:<12}", end=" ", flush=True)
        try:
            raw_songs = generate_songs_for_genre(client, genre, n=args.per_genre + 5)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"[error] bad response from Gemini: {exc}")
            continue
        except Exception as exc:
            print(f"[error] {exc}")
            continue

        added = 0
        seen_this_run: set[tuple[str, str]] = set()
        for song in raw_songs:
            if added >= args.per_genre:
                break
            row = validate_row(song, genre)
            if row is None:
                continue
            key = (row["title"].lower(), row["artist"].lower())
            if key in existing or key in seen_this_run:
                continue
            seen_this_run.add(key)
            new_rows.append({"id": next_id, **row})
            next_id += 1
            added += 1

        print(f"→ {added} songs added")
        time.sleep(4)  # stay within free-tier rate limit

    if not new_rows:
        print("\nNo new songs to add.")
        return

    file_exists = os.path.exists(csv_path)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    # Ensure the existing file ends with a newline before appending.
    if file_exists:
        with open(csv_path, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"\nDone. Added {len(new_rows)} songs → {csv_path}")
    print(f"Catalog now contains {len(existing) + len(new_rows)} songs.")


if __name__ == "__main__":
    main()
