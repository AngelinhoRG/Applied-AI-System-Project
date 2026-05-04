"""
Interactive CLI for collecting a user's music preference profile.

All input is validated before being returned; callers receive a clean dict
that score_song() and recommend_songs() can consume without further checks.
"""

from typing import Optional

VALID_GENRES = {
    "lofi", "ambient", "jazz", "pop", "indie pop", "rock",
    "metal", "synthwave", "edm", "r&b", "hip-hop", "blues",
    "country", "folk", "classical",
}

VALID_MOODS = {
    "chill", "relaxed", "happy", "euphoric", "intense", "angry",
    "confident", "focused", "dreamy", "romantic", "nostalgic",
    "melancholic", "sad", "moody",
}


def _prompt_choice(prompt: str, valid: set[str]) -> str:
    """Re-prompt until the user enters a value from valid (case-insensitive)."""
    sorted_options = ", ".join(sorted(valid))
    print(f"  Options: {sorted_options}")
    while True:
        raw = input(f"  {prompt}: ").strip().lower()
        if raw in valid:
            return raw
        print(f"  Invalid input. Choose one of: {sorted_options}")


def _prompt_float(prompt: str, lo: float, hi: float) -> float:
    """Re-prompt until the user enters a float in [lo, hi]."""
    while True:
        raw = input(f"  {prompt} ({lo}–{hi}): ").strip()
        try:
            value = float(raw)
        except ValueError:
            print(f"  Please enter a number between {lo} and {hi}.")
            continue
        if lo <= value <= hi:
            return round(value, 2)
        print(f"  Out of range. Enter a value between {lo} and {hi}.")


def _prompt_optional_float(prompt: str, lo: float, hi: float) -> Optional[float]:
    """Return a validated float, or None if the user presses Enter to skip."""
    while True:
        raw = input(f"  {prompt} ({lo}–{hi}, or Enter to skip): ").strip()
        if raw == "":
            return None
        try:
            value = float(raw)
        except ValueError:
            print(f"  Please enter a number between {lo} and {hi}, or press Enter to skip.")
            continue
        if lo <= value <= hi:
            return round(value, 2)
        print(f"  Out of range. Enter a value between {lo} and {hi}, or press Enter to skip.")


def collect_user_profile() -> dict:
    """
    Interactively collect a user's music preferences.

    Returns a prefs dict with required keys (genre, mood, energy) and any
    optional keys the user chose to specify (valence, acousticness).
    """
    print("\n" + "=" * 64)
    print("  Build Your Music Profile")
    print("=" * 64)

    genre = _prompt_choice("Genre", VALID_GENRES)
    mood = _prompt_choice("Mood", VALID_MOODS)
    energy = _prompt_float("Energy level", 0.0, 1.0)

    print("\n  Optional preferences (press Enter to skip):")
    valence = _prompt_optional_float("Valence (brightness of sound)", 0.0, 1.0)
    acousticness = _prompt_optional_float("Acousticness", 0.0, 1.0)

    prefs: dict = {"genre": genre, "mood": mood, "energy": energy}
    if valence is not None:
        prefs["valence"] = valence
    if acousticness is not None:
        prefs["acousticness"] = acousticness

    _print_profile_summary(prefs)
    return prefs


def _print_profile_summary(prefs: dict) -> None:
    """Print the collected profile so the user can review it before the run."""
    print("\n  Your profile:")
    for key, value in prefs.items():
        print(f"    {key}: {value}")
