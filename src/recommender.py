from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    import csv

    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    int(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs

ADJACENT_GENRES: Dict[str, set] = {
    "lofi":      {"ambient", "jazz"},
    "ambient":   {"lofi", "classical"},
    "jazz":      {"r&b", "blues", "lofi"},
    "pop":       {"indie pop", "r&b"},
    "indie pop": {"pop", "r&b"},
    "rock":      {"metal", "synthwave"},
    "metal":     {"rock"},
    "synthwave": {"rock", "edm"},
    "edm":       {"synthwave", "pop"},
    "r&b":       {"jazz", "hip-hop", "pop"},
    "hip-hop":   {"r&b", "pop"},
    "blues":     {"jazz", "country"},
    "country":   {"folk", "blues"},
    "folk":      {"country", "blues"},
    "classical": {"ambient"},
}

ADJACENT_MOODS: Dict[str, set] = {
    "chill":       {"relaxed", "dreamy", "focused"},
    "relaxed":     {"chill", "dreamy"},
    "happy":       {"euphoric", "relaxed"},
    "euphoric":    {"happy", "confident"},
    "intense":     {"angry", "confident"},
    "angry":       {"intense"},
    "confident":   {"intense", "euphoric", "happy"},
    "focused":     {"chill", "relaxed"},
    "dreamy":      {"chill", "relaxed", "romantic"},
    "romantic":    {"dreamy", "relaxed"},
    "nostalgic":   {"melancholic", "sad"},
    "melancholic": {"nostalgic", "sad", "moody"},
    "sad":         {"melancholic", "nostalgic", "moody"},
    "moody":       {"melancholic", "sad"},
}


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Returns a (score, reasons) tuple where reasons is a list of human-readable
    strings explaining what contributed to the score.

    Scoring weights (max 7.5 total):
      mood exact match   +2.0  | adjacent  +1.0
      energy proximity   up to +2.0
      genre exact match  +1.5  | adjacent  +0.75
      valence proximity  up to +1.5
      acousticness prox. up to +0.5
    """
    score = 0.0
    reasons = []

    # --- Mood (max +2.0) ---
    user_mood = user_prefs.get("mood", "").lower()
    song_mood = song["mood"].lower()
    if user_mood and user_mood == song_mood:
        score += 2.0
        reasons.append("mood match (+2.0)")
    elif user_mood and song_mood in ADJACENT_MOODS.get(user_mood, set()):
        score += 1.0
        reasons.append(f"adjacent mood '{song_mood}' (+1.0)")

    # --- Energy proximity (max +2.0) ---
    if "energy" in user_prefs:
        energy_pts = (1.0 - abs(user_prefs["energy"] - song["energy"])) * 2.0
        score += energy_pts
        reasons.append(f"energy proximity ({energy_pts:.2f}/2.0)")

    # --- Genre (max +1.5) ---
    user_genre = user_prefs.get("genre", "").lower()
    song_genre = song["genre"].lower()
    if user_genre and user_genre == song_genre:
        score += 1.5
        reasons.append("genre match (+1.5)")
    elif user_genre and song_genre in ADJACENT_GENRES.get(user_genre, set()):
        score += 0.75
        reasons.append(f"adjacent genre '{song_genre}' (+0.75)")

    # --- Valence proximity (max +1.5) ---
    if "valence" in user_prefs:
        valence_pts = (1.0 - abs(user_prefs["valence"] - song["valence"])) * 1.5
        score += valence_pts
        reasons.append(f"valence proximity ({valence_pts:.2f}/1.5)")

    # --- Acousticness proximity (max +0.5) ---
    if "acousticness" in user_prefs:
        acoustic_pts = (1.0 - abs(user_prefs["acousticness"] - song["acousticness"])) * 0.5
        score += acoustic_pts
        reasons.append(f"acousticness proximity ({acoustic_pts:.2f}/0.5)")

    return score, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    scored = sorted(
        ((song, score, reasons) for song, (score, reasons) in
         ((song, score_song(user_prefs, song)) for song in songs)),
        key=lambda x: x[1],
        reverse=True,
    )
    return [(song, score, ", ".join(reasons)) for song, score, reasons in scored[:k]]
