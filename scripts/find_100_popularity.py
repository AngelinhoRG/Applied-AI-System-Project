import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

THRESHOLD_LOW = 92
THRESHOLD_HIGH = 100


def find_high_popularity(path, name_col, artist_col, popularity_col):
    df = pd.read_csv(path)
    mask = df[popularity_col].between(THRESHOLD_LOW, THRESHOLD_HIGH)
    results = df.loc[mask, [name_col, artist_col, popularity_col]].copy()
    results = results.sort_values(popularity_col, ascending=False).reset_index(drop=True)
    return results


def print_table(title, df, name_col, artist_col, popularity_col):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"  Songs with popularity {THRESHOLD_LOW}–{THRESHOLD_HIGH}")
    print(f"{'=' * 60}")

    if df.empty:
        print("  No songs found in this range.")
        return

    col_w_name = max(df[name_col].str.len().max(), len("Song")) + 2
    col_w_artist = max(df[artist_col].str.len().max(), len("Artist")) + 2

    header = f"  {'Song':<{col_w_name}} {'Artist':<{col_w_artist}} {'Popularity':>10}"
    print(header)
    print(f"  {'-' * (col_w_name + col_w_artist + 12)}")

    for _, row in df.iterrows():
        score = int(row[popularity_col])
        bar = "█" * (score - THRESHOLD_LOW + 1)
        print(f"  {row[name_col]:<{col_w_name}} {row[artist_col]:<{col_w_artist}} {score:>6}  {bar}")

    print(f"\n  {len(df)} song(s) found.")


if __name__ == "__main__":
    songs_path = DATA_DIR / "songs.csv"
    spotify_path = DATA_DIR / "spotify-tracks-dataset.csv"

    songs_results = find_high_popularity(songs_path, "title", "artist", "popularity")
    print_table("songs.csv", songs_results, "title", "artist", "popularity")

    spotify_results = find_high_popularity(spotify_path, "track_name", "artists", "popularity")
    print_table("spotify-tracks-dataset.csv", spotify_results, "track_name", "artists", "popularity")

    print()
