# Project Walkthrough: Hype or Hit?

This document explains the project step by step: **what each script does, why it exists, what we observed, and what we learned**, including the mistakes we caught along the way. The "Aha" boxes mark the moments that changed how we understood the problem.

**Research question:** Can YouTube comments posted *before* a game launches tell genuine excitement apart from hype that is headed for a letdown?

**The pipeline at a glance**

```
 YouTube trailers ──► pre-release comments ──► cleaning & sampling ──► text analysis ──► statistics
                                                                        │  (word lists,     (permutation
 Steam + Metacritic ──► launch outcomes ─────────────────────────────┐  │   VADER, topics,   tests)
                                                                     ▼  ▼   Claude LLM)         │
                                                                 flop vs hit comparison ◄────────┘
                                                                            │
                                                                human check of the LLM ──► charts ──► GTA VI prediction
```

**Games studied**

| Group | Games |
|---|---|
| Overhyped (flops) | Cyberpunk 2077, Concord, Suicide Squad: Kill the Justice League, Redfall |
| Delivered (hits) | Elden Ring, Baldur's Gate 3, Black Myth: Wukong, Hogwarts Legacy |
| Prediction target | Grand Theft Auto VI (release Nov 19, 2026) |

---

## Step 0: Project setup (`config/games.yaml`, `src/hype/config.py`)

**What it does.** `games.yaml` stores every game's name, release date, Steam ID, starting group and chosen trailers. `config.py` reads that file and the API keys so every script uses the same settings.

**Why.** Keeping the game list outside the code means adding a game is a one-line edit, not a code change. Keeping API keys in a `.env` file means they never end up on GitHub.

---

## Step 1: Find official trailers (`scripts/01_find_trailers.py`)

**What it does.** Searches YouTube for each game's trailers, **only among videos uploaded before the release date**, sorted by views, and reports view and comment counts.

**What we observed.**
- The first search for Cyberpunk returned **Red Dead Redemption 2** and **Blade Runner 2049** trailers, because YouTube matched the words "official trailer".
- The Suicide Squad search returned the **2016 and 2021 movies**, not the game.

**Fix.** Keep only videos whose **title contains the game's name** (or a chosen keyword such as "Kill the Justice League"), and prefer official publisher channels over fan uploads.

**Result.** 3 trailers per game (an early reveal, a gameplay trailer, and one close to launch), plus 3 for GTA VI including the August 2026 gameplay reveal.

> **Lesson:** search APIs are fuzzy. Always inspect what comes back before collecting data from it.

---

## Step 2: Download the comments (`scripts/02_collect_comments.py`, `src/hype/youtube.py`)

**What it does.** Downloads every top-level comment on each trailer through the YouTube Data API (100 per request), then labels each one:
- `pre_release`: posted before the launch date (True/False)
- `days_to_release`: how long before launch it was posted
- `edited_after_release`: posted before launch but edited after it

Usernames are deliberately **not** collected.

**What we collected.**

| Game | Pre-release comments | Total |
|---|---:|---:|
| Cyberpunk 2077 | 91,173 | 105,743 |
| Hogwarts Legacy | 44,408 | 45,389 |
| Black Myth: Wukong | 35,926 | 36,335 |
| Suicide Squad: KTJL | 16,772 | 17,042 |
| Elden Ring | 16,777 | 21,350 |
| Baldur's Gate 3 | 6,779 | 7,248 |
| Concord | 4,628 | 7,439 |
| Redfall | 2,253 | 2,777 |
| GTA VI (capped at 50,000 per trailer) | 150,000 | 150,000 |

> **Aha 1: edited comments leak the future.**
> A Redfall comment dated three months *before* launch read: *"Arkane is like a AAA developer with the heart of a AA developer. This comment aged like..."* The author edited it after the game flopped. YouTube gives the **original date** but the **latest text**, so "pre-release" comments can contain hindsight. We added `edited_after_release` and excluded those comments. This is a textbook case of **data leakage**: information from the future sneaking into the input.

> **Aha 2: how much people talk is a signal by itself.**
> Cyberpunk had over 100,000 comments; Redfall had under 3,000. Low buzz before launch is its own warning sign, separate from what people actually said.

**Other observations.**
- **Concord's reveal trailer has more post-release comments than pre-release ones** (1,344 vs 888): people came back after the shutdown to comment.
- **Like counts are today's totals**, not launch-time totals. A pre-release comment like *"Lots of Elder Scrolls fans are gonna be pissed"* (1,365 likes) probably gained likes from people revisiting after the flop. We treat likes with caution.
- One duplicate comment appeared because new comments arrived while paging. Duplicates are now removed.

---

## Step 3: Launch outcomes from Steam (`scripts/03_collect_steam.py`, `src/hype/steam.py`)

**What it does.** Uses Steam's public review API to get, for each game:
- % positive reviews in **launch week** (starting 3 days before release, to include deluxe-edition early access)
- % positive in the **first 30 days** and **all time**
- **monthly** review history
- up to 2,000 launch-week **review texts**, sampled evenly day by day

**A bug we caught.** The first run saved only 100 Redfall reviews out of 1,705. A small diagnostic script showed that Steam's default sort ("most helpful") returns **the same page forever** when combined with a date filter. Switching to "most recent" and sampling **one day at a time** fixed it and gave a balanced spread across the week.

**Steam results.**

| Game | Group | Launch week % positive |
|---|---|---:|
| Redfall | flop | 28.2 |
| Concord | flop | 71.5 |
| Suicide Squad: KTJL | flop | 75.8 |
| Cyberpunk 2077 | flop | 84.3 |
| Elden Ring | hit | 89.6 |
| Black Myth: Wukong | hit | 94.1 |
| Hogwarts Legacy | hit | 94.6 |
| Baldur's Gate 3 | hit | 97.1 |

> **Aha 3: buyer reviews hide most flops.**
> The order is right, but only Redfall looks like a disaster. Steam reviews only come from **people who bought the game**, a self-selected group (**selection bias**). Each flop failed differently:
> - **Redfall:** quality (unfinished), which Steam captures
> - **Cyberpunk:** quality, but mainly on **PS4 and Xbox One**; the PC version (what Steam measures) was decent
> - **Concord:** **nobody showed up** (only 498 English reviews; servers shut down within weeks)
> - **Suicide Squad:** **players left** (76% at launch, falling to 62% all-time)

**Example launch reviews (Redfall).** *"Gameplay? Boring. Graphics? Ugly. Story? A joke."* (2,115 helpful votes), *"This game is about 25% finished"* (written after 0.4 hours of play). A top-voted *positive* review was a well-known sarcastic copypasta, an early hint that sarcasm would matter later.

---

## Step 3b: Manual outcomes (`data/raw/manual_outcomes.csv`)

Because Steam alone misses most flops, we added three more outcome measures for each game:
- **Metacritic critic score** (PC) and **user scores** (PC and console)
- **Peak Steam players** in the launch month (reach)
- **Retention:** average players two months later divided by the launch peak

| Game | Console user score | Launch peak players | Retention |
|---|---:|---:|---:|
| Concord | 1.7 | 697 | 0% (shut down) |
| Suicide Squad: KTJL | 3.5 | 13,459 | 2.7% |
| Redfall | 3.6 (Xbox) | 1,560 | 2.1% |
| Cyberpunk 2077 | **3.8 (PS4)** vs 7.3 on PC | 830,387 | 3.0% |
| Black Myth: Wukong | 7.9 | 2,406,967 | 3.8% |
| Hogwarts Legacy | 8.0 | 527,652 | 4.2% |
| Elden Ring | 8.4 | 952,523 | 22.2% |
| Baldur's Gate 3 | 8.7 | 875,343 | 16.9% |

> **Aha 4: console user scores split the groups cleanly.**
> Every flop scores 3.8 or lower; every hit 7.9 or higher. Cyberpunk's PC vs PS4 gap (7.3 vs 3.8) captures exactly what Steam missed.

![Launch outcomes](../figures/5_launch_outcomes.png)

**Caution.** Retention is confounded by game type: single-player games like Wukong and Hogwarts naturally lose players once people finish them, so low retention is not failure for them.

---

## Step 4: Clean and combine (`scripts/04_build_dataset.py`, `src/hype/text.py`)

**What it does.** Stacks all comment files into one table and keeps a comment as **usable hype** only if it:
1. was posted before release
2. was not edited after release
3. is mostly English (a fast heuristic: at least 80% Latin letters, and longer comments must contain a common English word)
4. has at least 3 words
5. is not a duplicate of another comment on the same game

Then it samples **up to 3,000 usable comments per game**, so each game carries equal weight (Cyberpunk alone would otherwise be 42% of the data). It also merges all outcome data into `games.csv`.

**What we observed.**
- **GTA VI had 18% duplicate comments**, far more than any other game (Cyberpunk about 5%): copy-paste memes like "who's here after Trailer 2?". GTA hype is partly meme-driven.
- Redfall had only **1,917** usable comments, so it keeps all of them.

**A subtle bug we fixed.** The first sampling method shuffled all games together, so adding GTA's gameplay trailer **changed every other game's sample** (Cyberpunk's negative share moved from 21.9% to 20.6%). We switched to a fixed pseudo-random key per comment, so each game's sample is now **locked**.

> **Lesson:** results that move when unrelated data changes are a warning sign. Reproducibility has to be designed in.

---

## Step 5: Sentiment and word lists (`scripts/05_text_features.py`, `src/hype/features.py`)

**What it does.**
- **VADER sentiment** (Valence Aware Dictionary and sEntiment Reasoner): a score from -1 to +1 for each comment, built for social media text.
- **Word lists (lexicons)** for excitement ("can't wait", "day one", "GOTY"), skepticism ("downgrade", "live service", "red flag"), nostalgia, gameplay and visuals.
- **Lift analysis:** which words appear relatively more often before flops than before hits.

**Results (group averages).**

| Measure | Hits | Flops |
|---|---:|---:|
| % negative (VADER) | 18.3 | 26.5 |
| % excitement words | 11.3 | 6.6 |
| % skepticism words | 1.5 | 2.6 |
| % nostalgia words | 6.8 | 4.0 |

**Words used more before flops:** *awful, worst, terrible, marvel, fortnite, overwatch, dead, pass, tired, dislikes, cgi, generic*.
**Words used more before hits:** *lore, epic, dream, beautiful, boss, combat, childhood, soul*.

> **Aha 5: flops attract comparisons and business-model worries; hits attract their own world.**
> Before flops, people compared the game to *other* games ("another Overwatch", "Fortnite style") and worried about battle passes and live service. Before hits, they talked about the game's own world and how it made them feel.

**Three problems we caught and fixed.**
1. **Game-specific words dominated the first lift results.** "dark", "praise" and "george" came from Elden Ring (Dark Souls, "Praise the Sun", George R.R. Martin); "spells" and "hp" from Hogwarts. Fix: drop any word where a single game supplies more than half its uses.
2. **"doubt" counted as skepticism**, but people write "**no doubt** this is GOTY". Fix: use "I doubt" and "doubtful" instead.
3. **Genre is a confound.** 3 of 4 flops are live-service shooters; all 4 hits are single-player RPGs. Words like "gun" and "fps" may simply mean "this is a shooter". We can't fully separate this with 8 games, so we state it as a limitation. Tone-based findings (negativity) are less affected than topic-based ones.

**Hypothesis rejected:** we expected nostalgia-driven hype to predict disappointment. Hits actually had **more** nostalgia talk. Reporting a rejected hypothesis is part of honest analysis.

---

## Step 6: Topic modeling (`scripts/06_topics.py`)

**What it does.** LDA (Latent Dirichlet Allocation) groups words that tend to appear together into "topics" **without being told what to look for**. It is a check on whether our hand-picked word lists biased the results.

**Design choice.** Topics are learned **only from the 8 games with known outcomes**, then applied to GTA VI. Learn first, predict after.

**What held up across two different runs.**

| Topic (our name) | Top words | Flops | Hits |
|---|---|---:|---:|
| Live-service worries | sony, player, overwatch, single, live, service | 11.1% | 6.9% |
| "Generic" comparisons | generic, shooter, hero, guardians of the galaxy, boring | 10.2% | 6.3% |

**What did not hold up.** A "dream come true" topic (finally, imagine, believe, thank) appeared in the first run but disappeared in the second. We do not rely on it.

> **Lesson: don't tune until it looks right.** LDA is unstable on short comments. Changing settings until the output matches expectations would be cherry-picking. We report only themes that appeared in both runs.

---

## Step 7: Statistics (`scripts/07_stats.py`)

**What it does.**
- **Confidence intervals:** a ± range for each game's numbers.
- **Exact permutation test:** the key test. With only 8 games, it tries **all 70 ways** to split them into two groups of 4 and asks how often a random split gives a gap as large as the real one. If the real split is the most extreme possible, p = 2/70 = **0.029**, the best result 8 games can give.
- **GTA VI broken down by trailer.**

**Results (word lists and VADER).**

| Metric | p-value | Verdict |
|---|---:|---|
| % negative | 0.029 | strong |
| "Generic" comparisons topic | 0.057 | suggestive |
| Average sentiment | 0.057 | suggestive |
| % excitement | 0.086 | suggestive |
| % skepticism | 0.086 | suggestive |
| Live-service topic | 0.257 | could be chance |
| % nostalgia | 0.286 | could be chance |

> **Aha 6: "delay" talk was a real warning sign.**
> Removing delay words from the skepticism list weakened it from p = 0.086 to 0.171. Cyberpunk was delayed three times before its broken launch; delays often signal development trouble.

> **Aha 7: GTA VI's gameplay reveal changed the mood.**
>
> | | Trailer 1 | Trailer 2 | Gameplay reveal |
> |---|---:|---:|---:|
> | % positive | 31.8 | 32.7 | **46.0** |
> | % excitement | 4.0 | 3.8 | **8.2** |
> | Skepticism without delay words | 0.3 | 0.3 | 1.5 |
>
> Almost all skepticism on Trailers 1 and 2 was about **delays**, not quality. Showing gameplay raised positivity sharply.

**Caveat:** we tested several metrics, and testing many things raises the chance that one looks significant by luck. Negativity was one of our main expected signals from the start, which makes it more credible.

---

## Step 8: LLM validation (`scripts/08_llm_validate.py`, `src/hype/llm.py`)

**Why.** Dictionary tools have known weaknesses: they miss sarcasm, miss doubt expressed without keywords, and misread phrases like "no doubt". An LLM reads context.

**What it does.** Claude Haiku 4.5 labels each of ~24,000 comments for sentiment, excitement, skepticism, sarcasm, comparison and live-service talk.

**Design choices.**
- **Blind:** Claude never sees the game name or outcome, and each batch mixes games, so it judges the comment, not its knowledge of which games flopped.
- **Clear rules** in the prompt: "delayed again" is not skepticism, "no doubt GOTY" is not skepticism, judge sarcasm by its real meaning.
- **Resumable:** every batch is saved immediately, so an interruption never costs money twice.
- **Cost:** about $7 for all ~24,000 comments.

> **Aha 8: our simple tools were unreliable on individual comments.**
> VADER agreed with Claude on only 47% of comments (kappa 0.18). Claude flagged **2,414 sarcastic comments**, and VADER had scored **579 of them as positive** when they were negative. The skepticism word list found about 2% skeptical comments; Claude found 15% to 60%, because people express doubt indirectly ("this looks like a 2015 game").

**Results with Claude's labels.**

| Metric | Flops | Hits | p-value |
|---|---:|---:|---:|
| % negative | 37.0 | 12.7 | **0.029** |
| % positive | 30.2 | 50.2 | **0.029** |
| % excitement | 22.8 | 41.8 | 0.057 |
| % skepticism | 35.4 | 14.6 | 0.086 |
| % comparison | 33.3 | 28.6 | 0.371 |

> **Aha 9: the main finding got stronger, and one earlier conclusion was wrong.**
> Negativity holds across three methods, and with Claude the gap triples (24 points instead of 8). Earlier, VADER suggested flops "weren't less positive, just more divided". Claude showed that was wrong: **flops were less positive and more negative**. VADER's positive count had been inflated by sarcasm. This is exactly why we validate with a second method.

![Negativity by game](../figures/1_negativity_by_game.png)

> **Aha 10: comparisons are not a red flag by themselves.**
> Elden Ring had 39% comparison comments (mostly to Dark Souls) and was a hit. What matters is *how* people compare: "generic Overwatch clone" is a warning; "Dark Souls but open world" is excitement.

> **Aha 11: there are three kinds of flop.**
>
> | Type | Games | Pattern |
> |---|---|---|
> | **Rejected** | Concord (71.5% negative), Redfall (43.7%) | Audiences turned against it before launch |
> | **Indifferent** | Suicide Squad (17% negative, but only 34% positive) | Not hated, just no enthusiasm |
> | **Betrayed** | Cyberpunk (16% negative, 48.5% positive) | Chatter looked like a hit; it failed on technical quality |
>
> Two of three types are visible in pre-release chatter. The third is not.

![Three kinds of flop](../figures/2_flop_types_scatter.png)

---

## Step 9: Human check (`scripts/09_human_check.py`)

**Why.** If we base findings on Claude's labels, we need evidence that Claude reads comments correctly. A human is the "gold standard".

**What it does.** Picks random comments, hides all tool labels, and lets a person label them by hand with the same rules Claude was given. Then it measures agreement using **Cohen's kappa** (0 = no better than chance, 1 = perfect).

**Results (38 hand-labeled comments).**

| Measure | Claude vs human | Simple tool vs human |
|---|---:|---:|
| Sentiment | **0.52** (moderate) | VADER 0.18 (slight) |
| Skepticism | **0.61** (substantial) | word list 0.13 (slight) |
| Excitement | 0.17 | word list 0.10 |
| Sarcasm | 0.36 (92% raw agreement) | n/a |

![LLM vs simple tools](../figures/3_llm_vs_simple_tools.png)

**What it means.**
- Claude matches human judgment about **3× better on sentiment** and **5× better on skepticism**, which justifies using Claude's labels for the main results.
- **Excitement is subjective** ("looks cool": excited or just approving?). Neither tool matched well, so excitement is treated as supporting evidence only.
- Sarcasm's kappa is modest only because sarcasm is rare (about 10% of comments); raw agreement was 92%.

---

## Step 10: Charts (`scripts/10_charts.py`)

Five charts in `figures/`, using a colorblind-safe palette with direct labels on every mark. Each one appears above, next to the step whose finding it shows:

1. `1_negativity_by_game.png`: the headline finding
2. `2_flop_types_scatter.png`: positive vs negative, showing the three kinds of flop
3. `3_llm_vs_simple_tools.png`: why the LLM was worth using
4. `4_gta_vs_averages.png`: where GTA VI sits between the average flop and hit
5. `5_launch_outcomes.png`: proof the "overhyped" labels were real

---

## Final findings

| Finding | Evidence | Strength |
|---|---|---|
| Flops had more negative and fewer positive pre-release comments | Claude (human-validated), VADER; p = 0.029 | **Strong** |
| Flops had more skepticism | Claude (human-validated); p = 0.086 | Suggestive |
| Flops had less excitement | Claude and word lists; p = 0.057 | Suggestive (subjective measure) |
| Three kinds of flop: rejected, indifferent, betrayed | Claude per-game profiles | Descriptive |
| Live-service worries and "generic" comparisons before multiplayer flops | Word lists, topics, Claude | Descriptive |
| Simple tools miss sarcasm and indirect doubt | Human check | **Strong** |
| Nostalgia predicts disappointment | Not supported | Rejected |

### GTA VI prediction

On its gameplay reveal, GTA VI sits **much closer to the hits than to the flops**:

| | GTA VI | Average flop | Average hit |
|---|---:|---:|---:|
| % negative | 18.9 | 37.0 | 12.7 |
| % positive | 45.4 | 30.2 | 50.2 |
| % excitement | 33.6 | 22.8 | 41.8 |
| % skepticism | 18.8 | 35.4 | 14.6 |

![GTA VI vs averages](../figures/4_gta_vs_averages.png)

It is clearly **not** a "rejected" or "indifferent" profile. It is slightly less excited and slightly more skeptical than every hit, likely hype fatigue after a long wait. Its profile is **closest to Cyberpunk's**, which is the honest caveat: chatter cannot detect technical problems.

---

## Limitations

1. **Only 8 games.** p = 0.029 is the best possible result, but it is still 8 data points.
2. **Genre confound:** flops were mostly live-service shooters, hits were single-player RPGs.
3. **Current, not historical, values** for likes and Metacritic scores; Metacritic user scores are vulnerable to review bombing.
4. **One human labeler, 38 comments** in the validation.
5. **The LLM might recognize famous games** from content ("Harry Potter", "Batman") despite blinding.
6. **GTA VI's early trailers** were sampled from their most recent comments, so only the gameplay reveal is a fair comparison.
7. **English-only, YouTube-only:** results describe online English-language trailer audiences, not all players.

## What I would do next

- Add **successful shooters** (e.g. Helldivers 2) and **failed RPGs** (e.g. Forspoken) to separate genre from outcome.
- Add **Reddit** discussion threads as a second platform.
- Use **two or more human labelers** and measure their agreement with each other.
- Revisit the GTA VI prediction after its November 2026 launch.
