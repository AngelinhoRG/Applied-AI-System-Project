"""
Music Recommender — RAG pipeline runner.

Flow:
  1. Load song catalog from data/songs.csv
  2. For each profile, retrieve the top-K songs using the scoring engine (recommender.py)
  3. Pass the retrieved songs to Claude as grounded context (rag.py)
  4. Claude generates a narrative that actively reasons from the song attributes
"""

import logging
import os
import sys

import anthropic
from dotenv import load_dotenv

# Load .env before anything else so ANTHROPIC_API_KEY is available
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("recommender.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from .recommender import load_songs, recommend_songs  # noqa: E402
from .rag import run_rag_pipeline  # noqa: E402


PROFILES = [
    # ── Normal profiles ───────────────────────────────────────────────────────
    {
        "label": "High-Energy Pop",
        "prefs": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.9,
            "valence": 0.85,
        },
    },
    {
        "label": "Chill Lofi",
        "prefs": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.35,
            "valence": 0.60,
            "acousticness": 0.80,
        },
    },
    {
        "label": "Deep Intense Rock",
        "prefs": {
            "genre": "rock",
            "mood": "intense",
            "energy": 0.95,
            "valence": 0.30,
        },
    },
    # ── Adversarial / edge-case profiles ─────────────────────────────────────
    # Energy=0.9 screams hype, but mood=sad should pull toward low-energy sad
    # tracks. Watch whether energy or mood wins the tug-of-war.
    {
        "label": "ADVERSARIAL — High-Energy Sad (conflicting energy vs mood)",
        "prefs": {
            "genre": "blues",
            "mood": "sad",
            "energy": 0.9,
        },
    },
    # Wants the metal genre (+1.5 for genre match) but also prefers highly
    # acoustic sound (+0.5 at best). Metal tracks have acousticness ~0.04,
    # so the acousticness penalty should mostly cancel the genre bonus.
    {
        "label": "ADVERSARIAL — Acoustic Metal Head (genre vs acousticness)",
        "prefs": {
            "genre": "metal",
            "mood": "intense",
            "energy": 0.97,
            "acousticness": 0.95,
        },
    },
    # Asks for happy mood (+2.0 for match) but sets valence=0.05, the
    # opposite of what happy songs actually carry. Only one happy song has
    # low valence; the scorer rewards mood but penalises valence.
    {
        "label": "ADVERSARIAL — Happy Mood, Dark Valence (mood vs valence)",
        "prefs": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "valence": 0.05,
        },
    },
]


def get_client() -> anthropic.Anthropic:
    """Return an Anthropic client, or exit with a clear message if the key is missing."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error(
            "ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and add your key, then try again."
        )
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def print_retrieved(label: str, recommendations, k: int) -> None:
    """Print the retrieval layer results (scored songs)."""
    print("\n" + "=" * 64)
    print(f"  Profile : {label}")
    print(f"  Top {k} Retrieved Songs (scored by preference match)")
    print("=" * 64)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Genre: {song['genre']}  |  Mood: {song['mood']}")
        print(f"       Score: {score:.2f} / 7.5")
        for reason in explanation.split(", "):
            print(f"       + {reason}")


def print_ai_narrative(narrative: str) -> None:
    """Print the AI-generated recommendation narrative."""
    print("\n  --- AI Recommendation ---")
    for line in narrative.strip().splitlines():
        print(f"  {line}")
    print("=" * 64)


def main() -> None:
    logger.info("Starting music recommender RAG pipeline")

    # Guardrail: verify API key before doing any other work
    client = get_client()

    csv_path = "data/songs.csv"
    if not os.path.exists(csv_path):
        logger.error(
            "Song catalog not found at '%s'. Run this script from the project root.",
            csv_path,
        )
        sys.exit(1)

    songs = load_songs(csv_path)
    logger.info("Loaded %d songs from %s", len(songs), csv_path)

    k = 5

    for profile in PROFILES:
        label = profile["label"]
        prefs = profile["prefs"]

        logger.info("Processing profile: %s", label)

        # Retrieval — score every song and keep top-K
        top_songs = recommend_songs(prefs, songs, k=k)
        logger.info("Retrieved %d songs for profile '%s'", len(top_songs), label)

        print_retrieved(label, top_songs, k)

        # Generation — Claude reasons from the retrieved context
        try:
            narrative = run_rag_pipeline(prefs, top_songs, client)
            print_ai_narrative(narrative)
        except anthropic.APIError as exc:
            logger.error(
                "Skipping AI narrative for '%s' due to API error: %s", label, exc
            )
            print("\n  [AI narrative unavailable — see recommender.log for details]")
            print("=" * 64)

    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
