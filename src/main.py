"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


PROFILES = [
    # ── Normal profiles ────────────────────────────────────────────────────────
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
    # ── Adversarial / edge-case profiles ──────────────────────────────────────
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


def print_results(label: str, recommendations, k: int) -> None:
    print("\n" + "=" * 60)
    print(f"  Profile : {label}")
    print(f"  Top {k} Recommendations")
    print("=" * 60)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Genre: {song['genre']}  |  Mood: {song['mood']}")
        print(f"       Score: {score:.2f} / 7.5")
        for reason in explanation.split(", "):
            print(f"       + {reason}")
    print("=" * 60)


def main() -> None:
    songs = load_songs("data/songs.csv")
    k = 5

    for profile in PROFILES:
        recommendations = recommend_songs(profile["prefs"], songs, k=k)
        print_results(profile["label"], recommendations, k)


if __name__ == "__main__":
    main()
