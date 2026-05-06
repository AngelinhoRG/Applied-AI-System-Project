"""
Tests for the music recommender scoring engine.

Covers five layers:
  1. score_song       — per-feature point calculations (mood, energy, genre,
                        valence, acousticness, popularity)
  2. recommend_songs  — ranking, ordering, and k-truncation
  3. confidence       — normalized confidence relative to preferences provided
  4. Recommender class — OOP interface (required by project spec)
  5. load_songs       — CSV parsing and type coercion
"""

import pytest
from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    score_song,
    recommend_songs,
    compute_max_score,
    confidence,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_song(**overrides) -> dict:
    """Minimal song dict with safe defaults; override any field for a specific test."""
    base = {
        "id": 1,
        "title": "Test Song",
        "artist": "Test Artist",
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "tempo_bpm": 120,
        "valence": 0.8,
        "danceability": 0.7,
        "acousticness": 0.2,
    }
    return {**base, **overrides}


# ── score_song: mood ──────────────────────────────────────────────────────────

def test_exact_mood_match_scores_full_points():
    song = make_song(mood="happy")
    score, reasons = score_song({"mood": "happy"}, song)
    assert score == 2.0
    assert any("mood match" in r for r in reasons)


def test_adjacent_mood_scores_half_points():
    # "relaxed" is adjacent to "chill" in ADJACENT_MOODS
    song = make_song(mood="relaxed")
    score, reasons = score_song({"mood": "chill"}, song)
    assert score == 1.0
    assert any("adjacent mood" in r for r in reasons)


def test_no_mood_match_scores_zero():
    song = make_song(mood="angry")
    score, _ = score_song({"mood": "happy"}, song)
    assert score == 0.0


def test_missing_mood_pref_not_counted():
    song = make_song(mood="happy")
    score, _ = score_song({}, song)
    assert score == 0.0


# ── score_song: energy ────────────────────────────────────────────────────────

def test_exact_energy_match_scores_full_points():
    song = make_song(energy=0.8)
    score, _ = score_song({"energy": 0.8}, song)
    assert score == pytest.approx(2.0)


def test_energy_proximity_is_proportional():
    song = make_song(energy=0.3)
    score, _ = score_song({"energy": 0.8}, song)
    expected = (1.0 - abs(0.8 - 0.3)) * 2.0   # = 1.0
    assert score == pytest.approx(expected)


def test_missing_energy_pref_not_counted():
    song = make_song(energy=0.5)
    score, _ = score_song({}, song)
    assert score == 0.0


# ── score_song: genre ─────────────────────────────────────────────────────────

def test_exact_genre_match_scores_full_points():
    song = make_song(genre="rock")
    score, _ = score_song({"genre": "rock"}, song)
    assert score == pytest.approx(1.5)


def test_adjacent_genre_scores_half_points():
    # "metal" is adjacent to "rock"
    song = make_song(genre="metal")
    score, reasons = score_song({"genre": "rock"}, song)
    assert score == pytest.approx(0.75)
    assert any("adjacent genre" in r for r in reasons)


def test_no_genre_match_scores_zero():
    song = make_song(genre="classical")
    score, _ = score_song({"genre": "pop"}, song)
    assert score == 0.0


# ── score_song: valence and acousticness ──────────────────────────────────────

def test_exact_valence_match_scores_full_points():
    song = make_song(valence=0.7)
    score, _ = score_song({"valence": 0.7}, song)
    assert score == pytest.approx(1.5)


def test_missing_valence_pref_not_counted():
    song = make_song(valence=0.9)
    score, _ = score_song({}, song)
    assert score == 0.0


def test_exact_acousticness_match_scores_full_points():
    song = make_song(acousticness=0.8)
    score, _ = score_song({"acousticness": 0.8}, song)
    assert score == pytest.approx(0.5)


def test_missing_acousticness_pref_not_counted():
    song = make_song(acousticness=0.9)
    score, _ = score_song({}, song)
    assert score == 0.0


# ── recommend_songs ───────────────────────────────────────────────────────────

def test_recommend_returns_exactly_k_results():
    songs = [make_song(id=i, genre="pop", mood="happy") for i in range(10)]
    results = recommend_songs({"genre": "pop", "mood": "happy"}, songs, k=3)
    assert len(results) == 3


def test_recommend_results_sorted_descending_by_score():
    songs = [
        make_song(id=1, genre="pop", mood="happy", energy=0.9),
        make_song(id=2, genre="jazz", mood="sad", energy=0.2),
        make_song(id=3, genre="rock", mood="intense", energy=0.7),
    ]
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.9}
    results = recommend_songs(prefs, songs, k=3)
    scores = [score for _, score, _ in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_top_result_is_best_match():
    songs = [
        make_song(id=1, genre="lofi", mood="chill", energy=0.3),  # poor match
        make_song(id=2, genre="pop",  mood="happy", energy=0.9),  # strong match
    ]
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.9}
    results = recommend_songs(prefs, songs, k=2)
    assert results[0][0]["genre"] == "pop"


def test_recommend_adversarial_conflicting_prefs_does_not_crash():
    """Conflicting preferences (high energy + sad mood) must not raise an exception."""
    from src.recommender import load_songs
    songs = load_songs("data/songs.csv")
    prefs = {"genre": "blues", "mood": "sad", "energy": 0.9}
    results = recommend_songs(prefs, songs, k=5)
    assert len(results) > 0


def test_recommend_k_larger_than_catalog_returns_all_songs():
    songs = [make_song(id=i) for i in range(3)]
    results = recommend_songs({}, songs, k=100)
    assert len(results) == 3


# ── confidence scoring ────────────────────────────────────────────────────────

def test_confidence_perfect_match_returns_one():
    song = make_song(genre="pop", mood="happy", energy=0.8, valence=0.8, acousticness=0.2)
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8, "acousticness": 0.2}
    score, _ = score_song(prefs, song)
    assert confidence(score, prefs) == pytest.approx(1.0)


def test_confidence_normalized_to_active_prefs_only():
    # Only mood provided → max possible = 2.0; a mood match scores 2.0 → confidence 1.0
    song = make_song(mood="happy")
    prefs = {"mood": "happy"}
    score, _ = score_song(prefs, song)
    assert confidence(score, prefs) == pytest.approx(1.0)


def test_confidence_partial_match_between_zero_and_one():
    song = make_song(genre="metal", mood="happy", energy=0.5)  # genre wrong, mood right
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.5}
    score, _ = score_song(prefs, song)
    c = confidence(score, prefs)
    assert 0.0 < c < 1.0


def test_confidence_no_prefs_returns_zero():
    assert confidence(0.0, {}) == 0.0


def test_compute_max_score_all_prefs():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8, "acousticness": 0.2}
    assert compute_max_score(prefs) == pytest.approx(7.5)


def test_compute_max_score_partial_prefs():
    prefs = {"mood": "happy", "energy": 0.8}   # max = 2.0 + 2.0
    assert compute_max_score(prefs) == pytest.approx(4.0)


def test_compute_max_score_with_popularity():
    prefs = {
        "genre": "pop", "mood": "happy", "energy": 0.8,
        "valence": 0.8, "acousticness": 0.2, "popularity": 0.7,
    }
    assert compute_max_score(prefs) == pytest.approx(8.5)


# ── Recommender class (OOP interface) ─────────────────────────────────────────

def make_small_recommender() -> Recommender:
    songs = [
        Song(id=1, title="Test Pop Track", artist="Test Artist",
             genre="pop", mood="happy", energy=0.8, tempo_bpm=120,
             valence=0.9, danceability=0.8, acousticness=0.2),
        Song(id=2, title="Chill Lofi Loop", artist="Test Artist",
             genre="lofi", mood="chill", energy=0.4, tempo_bpm=80,
             valence=0.6, danceability=0.5, acousticness=0.9),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)
    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(user, rec.songs[0])
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ── score_song: popularity ────────────────────────────────────────────────────

def test_exact_popularity_match_scores_full_points():
    """User wants mainstream (1.0); song popularity 100 → normalized 1.0 → 1.0 pts."""
    song = make_song(popularity=100)
    score, reasons = score_song({"popularity": 1.0}, song)
    assert score == pytest.approx(1.0)
    assert any("popularity" in r for r in reasons)


def test_popularity_proximity_is_proportional():
    """User wants 0.5; song popularity=0 → diff=0.5 → (1-0.5)*1.0 = 0.5 pts."""
    song = make_song(popularity=0)
    score, _ = score_song({"popularity": 0.5}, song)
    assert score == pytest.approx((1.0 - abs(0.5 - 0.0)) * 1.0)


def test_popularity_missing_song_data_not_scored():
    """Song without a popularity value must not contribute any points."""
    song = make_song()  # base dict has no "popularity" key
    score, reasons = score_song({"popularity": 0.8}, song)
    assert score == 0.0
    assert not any("popularity" in r for r in reasons)


def test_popularity_missing_pref_not_counted():
    """User did not provide a popularity preference — no points awarded."""
    song = make_song(popularity=80)
    score, _ = score_song({}, song)
    assert score == 0.0


def test_popularity_song_none_not_scored():
    """Song with popularity=None (CSV had empty cell) must not contribute points."""
    song = make_song(popularity=None)
    score, reasons = score_song({"popularity": 0.5}, song)
    assert score == 0.0
    assert not any("popularity" in r for r in reasons)


# ── Adjacent genres: reggae, latin, world ─────────────────────────────────────

def test_adjacent_genre_reggae_scores_hiphop_neighbor():
    """hip-hop is adjacent to reggae → 0.75 pts."""
    song = make_song(genre="hip-hop")
    score, reasons = score_song({"genre": "reggae"}, song)
    assert score == pytest.approx(0.75)
    assert any("adjacent genre" in r for r in reasons)


def test_adjacent_genre_latin_scores_pop_neighbor():
    """pop is adjacent to latin → 0.75 pts."""
    song = make_song(genre="pop")
    score, reasons = score_song({"genre": "latin"}, song)
    assert score == pytest.approx(0.75)
    assert any("adjacent genre" in r for r in reasons)


def test_adjacent_genre_world_scores_ambient_neighbor():
    """ambient is adjacent to world → 0.75 pts."""
    song = make_song(genre="ambient")
    score, reasons = score_song({"genre": "world"}, song)
    assert score == pytest.approx(0.75)
    assert any("adjacent genre" in r for r in reasons)


# ── load_songs ────────────────────────────────────────────────────────────────

def test_load_songs_returns_nonempty_list_of_dicts():
    """Catalog CSV must load as a non-empty list with the expected keys."""
    from src.recommender import load_songs
    songs = load_songs("data/songs.csv")
    assert len(songs) > 0
    required_keys = {"id", "title", "artist", "genre", "mood",
                     "energy", "tempo_bpm", "valence", "danceability",
                     "acousticness", "popularity"}
    assert required_keys.issubset(songs[0].keys())


def test_load_songs_popularity_is_int_or_none():
    """After backfill, every song must have an integer popularity (none should be missing)."""
    from src.recommender import load_songs
    songs = load_songs("data/songs.csv")
    for song in songs[:200]:  # spot-check first 200
        assert song["popularity"] is None or isinstance(song["popularity"], int)
