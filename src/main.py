"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv") 

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    k = 5
    recommendations = recommend_songs(user_prefs, songs, k=k)

    print("\n" + "=" * 50)
    print(f"  Top {k} Recommendations for you")
    print("=" * 50)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']}  —  {song['artist']}")
        print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}")
        print(f"    Score: {score:.2f} / 7.5")
        for reason in explanation.split(", "):
            print(f"    + {reason}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
