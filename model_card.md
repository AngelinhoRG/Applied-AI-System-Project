# Model Card: Music Recommender Simulation

## 1. Model Name

Give your model a short, descriptive name.  
**Music-Mender 1.0**  

---

## 2. Intended Use

MoodMatch 1.0 is designed to suggest songs that fit how a person feels right now.
You tell it your preferred genre, mood, and energy level, and it picks the five
best-fitting songs from a small catalog.

It assumes you can describe your taste with a few simple labels (like "rock" or
"chill") and a number for how energetic you want the music to feel. It is not
designed for real users on a real platform — it is a classroom simulation built
to explore how scoring-based recommenders work and where they break down.

---

## 3. How the Model Works

The recommender reads every song in the catalog and gives each one a score based
on how closely it matches what you asked for. The final score can go up to 7.5 points.
Here is how the points are handed out:

- **Mood** is worth the most — up to 2 points. An exact mood match gets the full 2.
  A nearby mood (e.g., you want "chill" and the song is "relaxed") gets 1 point.
- **Energy** is also worth up to 2 points. The closer the song's energy level is to
  yours, the more points it gets. A perfect match gets 2; a complete mismatch gets 0.
- **Genre** is worth up to 1.5 points. An exact match gets 1.5; a related genre
  (e.g., you want "pop" and the song is "indie pop") gets 0.75.
- **Valence** — how bright or dark the song sounds — is worth up to 1.5 points,
  scored the same way as energy.
- **Acousticness** is worth up to 0.5 points, only counted if you provide it.

Every song gets scored, then the top 5 are returned in order. No feature ever
subtracts points — the lowest any feature can contribute is 0.

---

## 4. Data

The catalog has 18 songs. Each song has a title, artist, genre, mood, energy level,
tempo, valence, danceability, and acousticness score.

The genres covered are: pop, lofi, rock, ambient, jazz, synthwave, indie pop,
country, metal, r&b, EDM, blues, folk, classical, and hip-hop.

The moods covered are: happy, chill, intense, focused, relaxed, moody, nostalgic,
romantic, melancholic, angry, euphoric, sad, dreamy, and confident.

The catalog is small and uneven. Pop, rock, and lofi each have multiple songs, but
genres like classical, folk, blues, and metal each have only one song. There are no
songs that cover tempo preferences directly, and danceability is stored but never
used in scoring. The dataset also has no concept of artist familiarity, release year,
or listener history.

---

## 5. Strengths

The system works well for users who like mainstream, well-represented genres.
A "Happy Pop" user or a "Chill Lofi" user gets a top result that closely matches
what they asked for — the right genre, the right mood, and similar energy. The
explanations are also transparent: every score shows exactly which features
contributed and by how much, so it is easy to understand why a song ranked where it did.

The adjacent genre and mood maps also do a reasonable job of catching near-misses.
A jazz fan gets credit for a lofi song; a "relaxed" user gets partial credit for a
"chill" song. That logic keeps the results from being too rigid.

---

## 6. Limitations and Bias

**Unequal score ceilings based on how much information you give.**
A user who provides all five preferences can score up to 7.5 points, while a user
who only provides genre and mood is capped at 3.5. Both users' scores are compared
in the same ranked list with no adjustment. The system quietly rewards data
completeness over actual compatibility.

**No song is ever penalized.** Energy, valence, and acousticness all floor at 0,
never go negative. A completely wrong song scores 0 for that feature instead of
losing points. This compresses the bottom of every ranking — it is hard to tell
a mediocre match from a terrible one.

**Niche genre users get stuck in small bubbles.** Classical has only one adjacent
genre (ambient). Metal has only one (rock). Folk's adjacency map is not symmetric
with blues. Users who prefer these genres get fewer fallback options and
consistently lower scores.

**Tempo and danceability are invisible.** Both fields are loaded from the CSV but
never used in scoring. A runner who needs 160+ BPM has no way to express that,
and the system will not consider it.

**Conflicting preferences are not detected.** Asking for "happy mood + dark valence"
or "metal genre + high acousticness" does not trigger any warning. The system just
scores each feature independently and returns a result that satisfies neither request
well.

---

## 7. Evaluation

I tested six user profiles — three normal and three adversarial.

The normal profiles were: High-Energy Pop (genre: pop, mood: happy, energy: 0.9),
Chill Lofi (genre: lofi, mood: chill, energy: 0.35, acousticness: 0.8), and
Deep Intense Rock (genre: rock, mood: intense, energy: 0.95).

The adversarial profiles were designed to expose edge cases: High-Energy Sad
(energy: 0.9 but mood: sad), Acoustic Metal Head (genre: metal but acousticness: 0.95),
and Happy Mood / Dark Valence (mood: happy but valence: 0.05).

I looked at whether the top-ranked songs matched the stated preference, whether
conflicting signals caused the scorer to pick a side or produce a strange result,
and whether scores were spread out or clumped together.

The most important test I ran was a feature-removal experiment: I commented out the
entire mood scoring block and re-ran all six profiles. Mood is worth up to 2 points —
the single largest feature — but removing it left the #1 result unchanged for most
profiles. That told me mood was often redundant with genre in this small catalog.
The one case where removal changed the top result was the Acoustic Metal Head: without
mood, the actual metal song finally ranked #1 because the genre match (+1.5) wasn't
being undercut by the mood mismatch between "angry" and "intense."

---

## 8. Future Work

**Add negative scoring.** Right now a mismatched song scores 0, never below 0.
Subtracting points for a mood or genre mismatch would spread scores further apart
and make it easier to distinguish good matches from bad ones.

**Normalize scores by the number of preferences provided.** A user who supplies
two preferences and a user who supplies five are competing unfairly. Dividing the
final score by the number of active features would put everyone on the same scale.

**Use tempo and danceability.** Both are already in the dataset but ignored entirely.
Letting users specify a target BPM or danceability level would make the recommender
meaningfully more useful, especially for workout or study playlists.

---

## 9. Personal Reflection

Building this made me realize how much invisible math sits behind a "simple"
recommendation. Every decision — which features to include, how many points to assign,
whether to allow negative scores — directly shapes which users get good results and
which ones get stuck in a bubble.

The most surprising thing was discovering that mood, which carries the highest point
value, was often not the deciding factor. Genre and energy were doing most of the
heavy lifting. That made me think about how real apps like Spotify probably weight
dozens of features and still get it wrong for niche tastes.

It also changed how I think about recommender systems in general. When an app suggests
something that feels slightly off, it is probably not random — there is a specific
scoring rule somewhere that is rewarding the wrong thing or ignoring the right one.
Now I look at those suggestions differently.
