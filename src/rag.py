"""
RAG pipeline for the music recommender.

Retrieval  — already done by recommend_songs() in recommender.py, which scores
             every song and returns the top-K matches with reasons.
Augmented  — those top-K songs and their attributes are packed into a context
             block that becomes part of the prompt.
Generation — Claude reads that context and writes a narrative that actively
             reasons from the song data rather than just listing titles.
"""

import logging
from typing import Dict, List, Tuple

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 350


def _build_context(user_prefs: Dict, top_songs: List[Tuple[Dict, float, str]]) -> str:
    """Serialize user preferences and retrieved songs into a plain-text context block."""
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
            f" | score={score:.2f}/7.5 | matched because: {reasons}"
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
    client: anthropic.Anthropic,
) -> str:
    """
    Send the retrieved context to Claude and return the generated narrative.
    Raises anthropic.APIError subclasses on failure — callers decide how to handle.
    """
    context = _build_context(user_prefs, top_songs)
    logger.info(
        "RAG generate | prefs=%s | retrieved=%d songs | model=%s",
        user_prefs,
        len(top_songs),
        MODEL,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    output = response.content[0].text
    logger.info(
        "RAG generate | input_tokens=%d output_tokens=%d",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return output


def run_rag_pipeline(
    user_prefs: Dict,
    top_songs: List[Tuple[Dict, float, str]],
    client: anthropic.Anthropic,
) -> str:
    """
    Full RAG pipeline entry point.
    Returns the AI-generated narrative, or raises on unrecoverable API errors.
    """
    if not top_songs:
        logger.warning("RAG called with empty top_songs — returning empty string")
        return ""

    try:
        return generate_recommendation(user_prefs, top_songs, client)
    except anthropic.APIStatusError as exc:
        logger.error(
            "Claude API error | status=%s message=%s", exc.status_code, exc.message
        )
        raise
    except anthropic.APIConnectionError as exc:
        logger.error("Claude API connection error: %s", exc)
        raise
