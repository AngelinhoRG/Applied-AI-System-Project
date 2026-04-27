# Profile Comparison Reflections

---

## Pair 1: High-Energy Pop vs. Chill Lofi

These two profiles are almost perfect opposites, and the results show it clearly.
The High-Energy Pop user got bouncy, fast, danceable songs — Sunrise City, Rooftop Lights,
Gym Hero. The Chill Lofi user got slow, atmospheric, low-key songs — Library Rain, Midnight
Coding, Spacewalk Thoughts. Almost zero overlap in the top 5.

This makes complete sense because the two profiles disagree on every single dimension:
energy (0.9 vs 0.35), genre (pop vs lofi), and mood (happy vs chill). The system had no
reason to suggest the same song to both users. This is actually the recommender working
exactly as intended — two different people, two genuinely different playlists.

---

## Pair 2: High-Energy Pop vs. Deep Intense Rock

Both users want high energy (0.9 and 0.95), but they diverge on mood and genre. The Pop
user wanted happy songs; the Rock user wanted intense ones. The result: they share zero
songs in their top 5, even though their energy levels are almost identical.

This shows that energy alone doesn't determine the playlist — mood and genre matter just
as much. Gym Hero (pop/intense) is a good example: it showed up at #3 for the Pop user
even without a mood match, purely because its genre and energy were close. For the Rock
user it appeared at #4 for the same energy reason, but it never climbed higher because
it's pop, not rock or metal. The same song floats up or down the list depending on what
else the user asked for.

---

## Pair 3: Chill Lofi vs. Deep Intense Rock

These profiles are completely different in every way — energy, genre, mood, and vibe.
The Lofi user's top song (Library Rain) scored 7.47/7.5, one of the highest scores in
any run. The Rock user's top song (Storm Runner) scored 6.65/7.5. The Lofi score is
higher not because the match is better, but because the Lofi user supplied an extra
preference (acousticness) that added up to 0.5 bonus points. The Rock user didn't
include that field, so their ceiling was lower from the start.

In plain terms: the Lofi user handed the system more information, so the system had
more ways to reward matching songs. This is a quirk worth noting — the score isn't
purely about fit, it's also about how many preferences you gave.

---

## Pair 4: High-Energy Pop vs. Adversarial Happy Mood / Dark Valence

This is the most instructive comparison. Both profiles asked for pop, happy, and high
energy — nearly identical on the surface. The only difference is valence: the normal
Pop user wanted bright-sounding songs (valence 0.85), while the adversarial user asked
for dark-sounding songs (valence 0.05) while still claiming to want "happy" music.

The top result was the same — Sunrise City — for both. But the scores tell the real
story: 6.82 with normal valence vs. 5.78 with dark valence. Sunrise City is a bright,
happy-sounding song, so it got penalized for not matching the low-valence request.
More interestingly, "Broken Signal" by Static Hymn (a metal/angry song) crept into
the bottom of the adversarial top 5, purely because its dark sound matched the
low-valence request. The system honored the valence number even though it contradicted
the mood. This exposes a real weakness: the recommender treats each feature
independently and can't recognize that "happy + dark-sounding" is a contradiction.

---

## Pair 5: High-Energy Pop vs. Adversarial High-Energy Sad

These two profiles share the same energy level (0.9) but want completely opposite moods
and genres. The Pop user got upbeat, danceable songs. The Sad user's top result was
Rainy Season (blues/sad) with a score of only 4.58 — much lower than the Pop user's
6.82 top score.

Why the big gap? The sad user's genre (blues) and mood (sad) are niche — there's only
one blues song and one sad song in the catalog. The system found the right song at #1,
but then had nothing else to fall back on. Songs 3–5 in the sad user's list were
high-energy pop and rock songs that had nothing to do with sadness — they ranked only
because they matched energy. This reveals a catalog bias: users with mainstream
preferences (pop, happy) are better served than users with niche or dark preferences.

---

## Pair 6: Deep Intense Rock vs. Adversarial Acoustic Metal Head

Both profiles want intense, high-energy music, but one wants it to sound raw and
electric (rock) while the other paradoxically wants heavy metal that also sounds
acoustic. The Rock user's top result was Storm Runner (6.65), a clean strong match.
The Acoustic Metal Head's top result was also Storm Runner — but for a strange reason:
the actual metal song (Broken Signal) was penalized because metal tracks have almost
no acoustic quality (acousticness ~0.04), which barely scored the 0.5 acousticness
bonus the user was hoping for.

In plain terms: asking for "acoustic metal" is like asking for a "quiet firework."
The system tried its best but the two preferences fundamentally cancel each other out.
The user got a rock song instead of a metal song, because rock was close enough on
energy and genre without being punished as hard on acousticness. The result is valid
in a narrow technical sense but would probably frustrate a real user.

---

## Why Does "Gym Hero" Keep Showing Up?

Gym Hero (pop/intense, energy 0.93) appears across multiple profiles that didn't
explicitly ask for it — the Happy Pop user, the Rock user, and the adversarial profiles.
Here's why in plain language:

The recommender scores every song for every user. Gym Hero has near-perfect energy
(0.93 is close to almost any high-energy request), it's in the popular "pop" genre
which has two adjacent genres (indie pop, r&b), and its valence is fairly neutral (0.77)
so it doesn't get punished hard for most valence requests.

It's basically a "safe" song — it never scores perfectly for anyone, but it never
scores terribly either. Because the system has no penalty for wrong songs (scores
floor at 0, never go negative), Gym Hero keeps quietly accumulating energy and
genre points and sneaking into the bottom of top-5 lists. A better system would
subtract points for a mood mismatch (intense ≠ happy) rather than simply giving
zero for that dimension. Until then, Gym Hero is essentially free-riding on its
high energy number into playlists it doesn't belong in.

---

## Critical Reflection

### Limitations and Biases in the System

The most significant limitation is that the scorer treats every feature independently.
It awards points for mood, adds points for energy, adds points for genre, and sums them
up — but it never recognizes when two preferences contradict each other. "Happy mood +
dark valence" is nonsensical to a human but perfectly legal to the scorer. As a result,
songs end up in playlists where they clearly don't belong, like Broken Signal (metal/angry)
sneaking into a happy pop profile because its low valence happened to match the user's
low-valence request.

A related bias is catalog depth. Users with mainstream tastes (pop, happy, high energy)
get five strong matches because many songs were written with those attributes. Users with
niche or edge-case preferences (blues, sad) hit a wall fast — the first match is solid,
and then the system starts filling slots with off-topic songs that scored points on energy
alone. The recommender doesn't fail loudly when it runs out of good matches; it silently
serves mediocre ones. That is a bias toward the majority of the catalog, which itself
was likely curated with mainstream tastes in mind.

There is also a scoring-ceiling bias. A user who provides more preferences (genre, mood,
energy, valence, and acousticness) raises the maximum possible score from 4.0 to 7.5,
which makes their confidence percentages look lower for the same quality of match.
The system inadvertently penalizes users for giving more information.

---

### Could the AI Be Misused, and How Would I Prevent It?

The Claude-powered generation layer is the part most exposed to misuse. A user could
craft a preference input designed to push unusual, offensive, or harmful content into
the system prompt — for example, embedding instructions in a fake "genre" or "mood"
field that tries to redirect Claude's behavior (prompt injection). The current system
trusts user-supplied preference strings directly into the context it sends to the model.

To prevent this I would:

1. **Validate and sanitize inputs** before they reach the prompt. Genre and mood values
   should be matched against a fixed allowlist; any string that doesn't match a known
   value gets rejected or stripped rather than passed through raw.
2. **Keep the system prompt strictly grounding.** The current prompt already tells Claude
   to reason only from retrieved songs and not to reference anything outside the list.
   That is a meaningful guardrail — it limits the blast radius if a bad input gets through.
3. **Rate-limit and log every API call.** The existing logging setup captures input and
   output token counts per request. Extending that to flag unusually long user-supplied
   strings or anomalous outputs would make abuse visible before it scales.

The music domain is low-stakes — the worst realistic misuse is producing off-topic or
nonsensical recommendations, not harm to a person. But the same injection patterns that
would work here would work in higher-stakes RAG systems, so treating this as a practice
ground for good hygiene matters.

---

### What Surprised Me While Testing the AI's Reliability

The biggest surprise was how gracefully the scorer failed. I expected the adversarial
profiles to produce errors or crashes. They didn't — they produced confidently wrong
answers. The Acoustic Metal Head profile returned a top recommendation with a confidence
score of 62.7%, which sounds passable until you realize the song is rock, not metal, and
has basically no acoustic quality. The system never flagged the contradiction. It just
found the least-bad option and reported it with mild confidence, as if everything had
gone fine.

The second surprise was how much the no-negative-scoring floor mattered in practice.
I knew theoretically that scores bottom out at zero rather than going negative, but
I didn't anticipate how badly that distorts results until I saw Gym Hero appearing in
playlists for Rock, Sad, and even adversarial profiles. Songs don't get penalized for
being wrong — they only fail to accumulate points. In a small 30-song catalog that
effect is visible in almost every run.

Finally, I was surprised that the confidence averages held up as well as they did.
Normal profiles averaged around 96% confidence — that's the system working as designed.
Adversarial profiles averaged around 68%, which is lower but not catastrophically so.
I expected the conflicting-preference profiles to expose deeper failures. They exposed
real weaknesses, but the scoring engine absorbed the contradictions without breaking.
That is either a sign of robustness or of a system that doesn't know what it doesn't know.

---

### Collaboration with AI During This Project

I used Claude Code as a collaborator throughout the build. The collaboration was genuinely
useful in most places, but not perfect.

**One instance where the AI gave a helpful suggestion:** When I described wanting the RAG
pipeline to "actively use retrieved data," the AI proposed a system prompt constraint that
explicitly forbids Claude from listing song titles alone — instead requiring it to cite
specific attribute values (energy, valence, acousticness, tempo) in its reasoning. That
was a design decision I would not have thought to formalize in a prompt rule. The result
is that every generated narrative is grounded in the actual numbers from the retrieval
layer, not just the song names. Without that prompt constraint, the AI narrative would
have looked convincing but proved nothing about whether the retrieval was actually used.

**One instance where the AI's suggestion was flawed:** Early in the project the AI
suggested running the main script as `python src/main.py` directly. That worked when
`src/` was not a package, but the moment I added `src/__init__.py` (required for the
tests to resolve `from src.recommender import ...`), direct execution broke with a
`ModuleNotFoundError` because the relative imports (`from .recommender import ...`)
require the module to be run as `python -m src.main`. The AI initially presented
the direct-file approach as the correct setup step and only corrected it after the
import error surfaced. The lesson: the AI gave advice that was locally correct in one
context (before `__init__.py` existed) but failed to anticipate how a later change
would invalidate it. I now verify every setup step myself in a clean environment rather
than trusting that an individually correct suggestion will compose well with other changes.
