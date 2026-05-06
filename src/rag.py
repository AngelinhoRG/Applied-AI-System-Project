"""
RAG pipeline for the music recommender.

Retrieval  — already done by recommend_songs() in recommender.py, which scores
             every song and returns the top-K matches with reasons.
Augmented  — those top-K songs and their attributes are packed into a context
             block that becomes part of the prompt.
Generation — Gemini reads that context and writes a narrative that actively
             reasons from the song data rather than just listing titles.
"""

import logging
import time
from typing import Dict, List, Tuple

from google import genai
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"


def _build_context(user_prefs: Dict, top_songs: List[Tuple[Dict, float, str]]) -> str:
    """Serialize user preferences and retrieved songs into a plain-text context block."""
    from .recommender import compute_max_score
    max_score = compute_max_score(user_prefs)

    pref_lines = ["User preferences:"]
    for key, val in user_prefs.items():
        pref_lines.append(f"  {key}: {val}")

    song_lines = ["", "Retrieved songs (ranked by preference score):"]
    for rank, (song, score, reasons) in enumerate(top_songs, 1):
        song_lines.append(
            f"  #{rank} \"{song['title']}\" by {song['artist']}"
            f" | genre={song['genre']}, mood={song['mood']}"
            f", energy={song['energy']}, valence={song['valence']}"
            f", acousticness={song['acousticness']}, tempo={song['tempo_bpm']} BPM"
            f" | score={score:.2f}/{max_score:.1f} | matched because: {reasons}"
        )

    return "\n".join(pref_lines + song_lines)


_SYSTEM_PROMPT = """\
You are a music recommendation assistant. You will receive a listener's preferences \
and a list of songs that were retrieved and scored for that listener. Your job is to \
write a short, personalized recommendation narrative (under 160 words).

Rules:
- Use the actual attribute values from the retrieved data (energy, valence, \
  acousticness, tempo, mood) to explain WHY each top pick fits this listener.
- Do NOT just list song titles — reason from the numbers and attributes.
- If the listener's preferences conflict (e.g., high energy but sad mood), \
  acknowledge the trade-off and explain how the top songs navigate it.
- Only reference songs that appear in the retrieved list.
- Write in second person ("you", "your").\
"""


def generate_recommendation(
    user_prefs: Dict,
    top_songs: List[Tuple[Dict, float, str]],
    client: genai.Client,
) -> str:
    """
    Send the retrieved context to Gemini and return the generated narrative.
    Raises on failure — callers decide how to handle.
    """
    context = _build_context(user_prefs, top_songs)
    logger.info(
        "RAG generate | prefs=%s | retrieved=%d songs | model=%s",
        user_prefs,
        len(top_songs),
        MODEL,
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=_SYSTEM_PROMPT + "\n\n" + context,
    )
    output = response.text
    logger.info("RAG generate | output_length=%d chars", len(output))
    return output


_RETRY_DELAYS = [5, 15, 30]  # seconds between attempts (3 retries after the first try)


def run_rag_pipeline(
    user_prefs: Dict,
    top_songs: List[Tuple[Dict, float, str]],
    client: genai.Client,
) -> str:
    """
    Full RAG pipeline entry point.
    Retries on transient 503 overload errors before giving up.
    Returns the AI-generated narrative, or raises on unrecoverable API errors.
    """
    if not top_songs:
        logger.warning("RAG called with empty top_songs — returning empty string")
        return ""

    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            logger.info("Gemini 503 — retrying in %ds (attempt %d)...", delay, attempt)
            print(f"\n  [Gemini busy — retrying in {delay}s (attempt {attempt}/{len(_RETRY_DELAYS) + 1})...]")
            time.sleep(delay)
        try:
            return generate_recommendation(user_prefs, top_songs, client)
        except genai_errors.ServerError as exc:
            logger.warning("Gemini ServerError on attempt %d: %s", attempt, exc)
            last_exc = exc
        except Exception as exc:
            logger.error("Gemini API error (non-retryable): %s", exc)
            raise

    logger.error("Gemini unavailable after %d attempts: %s", len(_RETRY_DELAYS) + 1, last_exc)
    raise last_exc  # type: ignore[misc]
