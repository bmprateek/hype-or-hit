# Hype or Hit: Interview Prep Notes

Oct 5, 2026 · @Chiru

## Level 1: The basics

The project asks whether YouTube comments posted before a game launches can warn that a hyped game will disappoint. The short answer: partly. Flops drew far more negative chatter, but chatter cannot see technical failures.

**30-second pitch (memorize this)**

> I collected about 24,000 YouTube comments posted before the launch of 8 big games, 4 that flopped and 4 that succeeded. I labeled every comment with an LLM, checked those labels against my own hand labels, and compared the two groups. Flops had 37% negative pre-release comments versus 13% for hits, the strongest result possible with 8 games. I also found three kinds of flop: rejected, indifferent and betrayed. Chatter catches the first two, not the third. Finally I used the patterns to predict GTA VI, which looks like a hit with mild caution signs.

**Why it matters (the business angle)**

- A AAA game costs hundreds of millions of dollars. An early warning months before launch gives publishers time to change marketing, delay, or fix issues.
- Investors watch big launches (Take-Two's stock moves with GTA news).
- Marketing teams already monitor trailer reactions; this project shows *what* to measure and which tools to trust.

**The games and why they were chosen**

| Group | Games | Why chosen |
| --- | --- | --- |
| Overhyped (flops) | Cyberpunk 2077, Concord, Suicide Squad: KTJL, Redfall | Huge pre-launch attention, then widely seen as disappointments |
| Delivered (hits) | Elden Ring, Baldur's Gate 3, Black Myth: Wukong, Hogwarts Legacy | Huge pre-launch attention, then widely praised |
| Prediction | GTA VI (Nov 19, 2026) | The biggest upcoming launch; outcome unknown |

All 8 training games are on Steam, which gave a common outcome measure.

**Key vocabulary at this level**

- **Pre-release comment:** posted before the game's launch date. Only these are used to predict.
- **Outcome:** how the game was actually received (Steam reviews, Metacritic scores, player counts).
- **Unstructured data:** text, images, audio. Here: free-text comments, as opposed to tidy numeric tables.

## Level 2: The data pipeline

About 393,000 comments were downloaded and cut to \~24,000 clean pre-release comments, labeled three ways, then compared against launch outcomes.

&#91;embedded content: project pipeline · 8 steps\]

The top row collects and cleans, the middle row labels (Claude validated by a human), the bottom row compares flops with hits and predicts GTA VI.

**Sources and tools**

| Source | How | Gotcha |
| --- | --- | --- |
| YouTube trailers and comments | YouTube Data API v3, free key, 10,000 quota units a day | Search returned unrelated trailers (Red Dead 2, the Suicide Squad movies), so titles had to contain the game's name |
| Steam reviews | Public store API, no key | The default "most helpful" sort repeated the same page with a date filter; fixed by sorting "most recent" and sampling day by day |
| Metacritic and player counts | Read from Metacritic and Steamcharts | Concord's player page was broken after delisting; its peak of 697 came from news reports |

**Cleaning rules (a comment counts only if all are true)**

1. Posted before release
2. Not edited after release (hindsight leak)
3. Mostly English
4. At least 3 words
5. Not a duplicate on the same game

Then up to 3,000 comments per game are sampled, so Cyberpunk (105,000 comments) doesn't drown out Redfall (under 3,000). Each comment gets a fixed pseudo-random key, so a game's sample never changes when another game's data does.

**Numbers worth remembering:** \~393,000 downloaded (243,000 for the 8 games plus 150,000 for GTA VI, capped at 50,000 per trailer), 25,917 in the analysis sample, GTA VI had 18% duplicate comments (meme spam) versus about 5% for Cyberpunk.

## Level 3: Text analysis methods

Four text methods were used, from simplest to smartest. Each was checked against the others, so a finding only counts as strong if several methods agree (triangulation).

| Method | What it is, in one line | What we found | Weakness |
| --- | --- | --- | --- |
| VADER sentiment | A dictionary of words with positive or negative scores, tuned for social media (handles caps, emojis, "!!!"). Gives each comment a score from -1 to +1. | Flops 26.5% negative vs hits 18.3% | Fooled by sarcasm: "wow, can't wait for another battle pass" scores positive |
| Word lists (lexicons) | Our own lists of excitement, skepticism, nostalgia, gameplay and visuals phrases | Flops: less excitement (6.6% vs 11.3%), more skepticism (2.6% vs 1.5%) | Only finds the exact words we chose; "no doubt GOTY" counted as doubt until fixed |
| Lift (distinctive words) | Lift = % of flop comments with a word ÷ % of hit comments with it. Lift 3 = three times more common before flops | Before flops: marvel, fortnite, overwatch, dead, pass, generic, cgi. Before hits: lore, epic, dream, boss, combat | Rare words give huge, unstable lifts; game names leak in |
| LDA topic modeling | Latent Dirichlet Allocation: finds groups of words that appear together, without being told what to look for | Two robust topics before flops: live-service worries and "generic" comparisons | Unstable on short comments; topics change with settings |

**How VADER works (if asked)**

Each word has a pre-scored polarity. VADER adds them up, adjusts for boosters ("very"), negation ("not good"), capitals and punctuation, then squashes the total into -1 to +1. We used the standard cut-offs: ≥ 0.05 positive, ≤ -0.05 negative, otherwise neutral.

**How LDA works (if asked)**

1. Turn each comment into word counts (bag of words), dropping stopwords, game names and very rare or very common words.
2. Assume each comment is a mix of K topics, and each topic is a mix of words.
3. LDA finds the topics and mixes that best explain which words appear together.
4. We name topics ourselves by reading their top words and example comments.

We used K = 12, learned topics on the 8 known games only, then applied them to GTA VI (learn first, predict after).

**Three fixes worth mentioning in an interview**

- **Game-specific words** ("dark" and "praise" from Elden Ring's Dark Souls roots, "spells" from Hogwarts) dominated lift. Fix: drop words where one game supplies over 50% of uses.
- **"doubt"** matched "no doubt". Fix: use "I doubt" and "doubtful".
- **Topic instability:** we ran LDA twice and reported only themes that appeared both times, instead of tuning until results looked good (that would be cherry-picking).

## Level 4: Statistics

The real sample size is 8 games, not 24,000 comments, so the key test compares games. With 8 games the best possible p-value is 0.029, and negativity reached it.

**1. Confidence interval (how precise is each game's number?)**

For a percentage p from n comments, the 95% margin is:

```latex
\pm 1.96 \sqrt{\frac{p(1-p)}{n}}
```

Example: 20% negative from 3,000 comments gives about ± 1.4 points. With 200 comments it would be ± 5.5 points, which is why we labeled all \~24,000 with the LLM instead of a small sample.

**2. Exact permutation test (could the flop vs hit gap be luck?)**

1. Compute the real gap: average of the 4 flops minus average of the 4 hits.
2. Try every possible way to split the 8 games into two groups of 4. There are 70.
3. p-value = share of splits whose gap is at least as big as the real one.
4. If the real split is the most extreme possible, only it and its mirror qualify: p = 2 ÷ 70 = 0.029.

Why this test and not a t-test: it makes no assumptions about the data's distribution, it is exact rather than approximate, and it is honest about having only 8 data points.

| Metric (Claude labels) | Flops | Hits | p-value | Verdict |
| --- | --- | --- | --- | --- |
| % negative | 37.0 | 12.7 | 0.029 | Strong |
| % positive | 30.2 | 50.2 | 0.029 | Strong |
| % excitement | 22.8 | 41.8 | 0.057 | Suggestive |
| % skepticism | 35.4 | 14.6 | 0.086 | Suggestive |
| % live-service talk | 4.4 | 1.4 | 0.229 | Could be chance |
| % comparison | 33.3 | 28.6 | 0.371 | Could be chance |

**3. Cohen's kappa (do two labelers agree beyond luck?)**

Raw agreement can look high just by chance (if 90% of comments are "not sarcastic", two lazy labelers agree 90% of the time). Kappa corrects for that.

```latex
\kappa = \frac{p_o - p_e}{1 - p_e}
```

p\_o = observed agreement, p\_e = agreement expected by chance. Scale: below 0.2 slight, 0.2 to 0.4 fair, 0.4 to 0.6 moderate, 0.6 to 0.8 substantial, above 0.8 almost perfect.

**4. Multiple testing (a likely follow-up question)**

We tested several metrics. The more tests you run, the more likely one looks significant by luck. Our defense: negativity was a main expected signal from the start, it held across three methods (VADER, word lists, Claude), and both negative and positive share hit the best possible p-value. We still describe results as strong patterns, not proof.

## Level 5: LLM labeling and human validation

Claude Haiku 4.5 labeled every comment, and a human check showed it reads comments about 3× more like a person than VADER does. That is why the final results use Claude's labels.

**Why an LLM at all**

Dictionary tools read words, not meaning. They miss sarcasm, miss doubt phrased without keywords ("this looks like a 2015 game"), and misread phrases like "no doubt". An LLM (Large Language Model) reads context.

**What Claude labeled for each comment**

Sentiment (positive, negative, neutral, mixed), excitement, skepticism, sarcasm, comparison to another game, and live-service or monetization talk.

**Design choices to explain**

- **Blinding:** Claude never saw the game name or outcome, and each batch mixed games. Otherwise it might use what it already knows ("Cyberpunk flopped") instead of reading the comment.
- **Explicit rules in the prompt:** "delayed again" is not skepticism; "no doubt GOTY" is not skepticism; judge sarcasm by its real meaning. These are the exact mistakes the word lists made.
- **Batching:** 50 comments per request, about 480 requests. Each batch is saved immediately, so a crash never means paying twice.
- **Cost:** about $7 for \~24,000 comments (Haiku 4.5 is $1 per million input tokens and $5 per million output tokens).
- **Reproducibility:** labels were generated once and saved to `llm_labels.csv`; all analysis reads that file.

**What Claude revealed**

- Claude flagged 2,414 comments (10%) as sarcastic; VADER had scored 579 of them as positive when they were negative.
- The skepticism word list found about 2% skeptical comments; Claude found 15% to 60%, because doubt is usually indirect.
- VADER and Claude agreed on sentiment only 47% of the time (kappa 0.18).

**The human check (gold standard)**

I hand-labeled 38 random comments blind, using the same rules Claude got, then compared.

| Measure | Claude vs me (kappa) | Simple tool vs me (kappa) |
| --- | --- | --- |
| Sentiment | 0.52 (moderate) | VADER 0.18 (slight) |
| Skepticism | 0.61 (substantial) | Word list 0.13 (slight) |
| Excitement | 0.17 (slight) | Word list 0.10 (slight) |
| Sarcasm | 0.36 (fair, 92% raw agreement) | n/a |

**How to read it:** Claude is clearly better for sentiment and skepticism, so those findings are trustworthy. Excitement is subjective (is "looks cool" excitement or just approval?), so it is treated as supporting evidence only. Sarcasm's kappa is modest because sarcasm is rare, which pulls kappa down even at 92% agreement.

## Findings, aha moments and the GTA VI prediction

The headline: flops had 37% negative and 30% positive pre-release comments, versus 13% and 50% for hits. Every flop was more negative than every hit.

**The three kinds of flop (your most memorable insight)**

| Type | Games | What the chatter looked like | Detectable before launch? |
| --- | --- | --- | --- |
| Rejected | Concord (71.5% negative), Redfall (43.7%) | Audiences turned against it | Yes |
| Indifferent | Suicide Squad (17% negative, only 34% positive) | Not hated, just no enthusiasm | Yes |
| Betrayed | Cyberpunk 2077 (16% negative, 48.5% positive) | Looked like a hit | No: it failed on console bugs, invisible in trailers |

**Aha moments to tell as stories**

1. **Edited comments leak the future.** A comment dated three months before Redfall's launch ended with "this comment aged like...". YouTube shows the original date but the latest text. We flagged and removed comments edited after launch (data leakage).
2. **Buyer reviews hide flops.** On Steam, Concord looked fine (71.5% positive) because only 498 people bothered to review it. Steam measures buyers, not everyone (selection bias). Metacritic console user scores split the groups cleanly: flops 3.8 or lower, hits 7.9 or higher.
3. **Cyberpunk's platform split.** PC users scored it 7.3; PS4 users 3.8. The flop was on old consoles, which Steam (PC only) could not see.
4. **Delays were a real warning sign.** Removing "delay" words from the skepticism list weakened its signal. Cyberpunk was delayed three times before its broken launch.
5. **Comparisons are not a red flag by themselves.** Elden Ring had 39% comparison comments (to Dark Souls) and was a hit. "Generic Overwatch clone" is a warning; "Dark Souls but open world" is excitement.
6. **The LLM corrected an earlier conclusion.** VADER suggested flops were "not less positive, just more divided". Claude showed flops were less positive too. VADER's positives were inflated by sarcasm.
7. **Nostalgia hypothesis rejected.** We expected nostalgia-driven hype to predict disappointment; hits actually had more nostalgia talk. Reporting a rejected hypothesis shows honest analysis.

**GTA VI prediction (gameplay reveal, 1,014 comments)**

| Measure | GTA VI | Average flop | Average hit |
| --- | --- | --- | --- |
| % negative | 18.9 | 37.0 | 12.7 |
| % positive | 45.4 | 30.2 | 50.2 |
| % excitement | 33.6 | 22.8 | 41.8 |
| % skepticism | 18.8 | 35.4 | 14.6 |

GTA VI looks like a hit, clearly not rejected or indifferent. It is slightly less excited and more skeptical than every hit, likely hype fatigue after a long wait. Its profile is closest to Cyberpunk's, so the honest caveat is that chatter cannot rule out a technical letdown.

**Why only the gameplay reveal counts:** comments on Trailers 1 and 2 were the most recent 50,000, posted years later and full of delay jokes (skepticism without delay words was only 0.3%). The gameplay reveal is a fair near-launch comparison, like the late trailers of the other games.

## Limitations and how to defend them

Name the limitation before the interviewer does, then say what you did about it. That turns a weakness into evidence of good judgment.

| Limitation | What to say | What I did or would do |
| --- | --- | --- |
| Only 8 games | The unit of analysis is the game, so this is a small study. | Used an exact permutation test built for small samples; called results "strong patterns, not proof". Next: add more games. |
| Genre confound | 3 of 4 flops are live-service shooters; all hits are single-player RPGs. Words like "gun" or "fps" may just mean "shooter". | Negativity is about tone, not topic, so it is less affected. Next: add successful shooters (Helldivers 2) and failed RPGs (Forspoken). |
| Selection of games | I picked famous flops and hits after the fact. | Confirmed labels with outcome data (Steam, Metacritic, players), not my opinion. |
| Current values, not historical | Like counts and Metacritic scores are today's, not launch-day values; Metacritic user scores can be review-bombed. | Treated likes cautiously; used several outcome measures instead of one. |
| LLM might recognize games | Claude could identify "Harry Potter" or "Batman" comments and recall outcomes. | Blinded game names and mixed batches; validated against human labels. |
| Small human check | 38 comments, one labeler (me). | The gaps (0.52 vs 0.18, 0.61 vs 0.13) are large enough to hold. Next: two labelers, 100+ comments. |
| Platform and language | English YouTube comments only. | Results describe online English-speaking trailer audiences. Next: add Reddit. |
| Can't see technical quality | Chatter missed Cyberpunk. | Reported it as a finding (the "betrayed" flop type), not hidden. |

## Likely interview questions

Keep each answer to three parts: the answer, the evidence, the caveat.

**Basic**

1. **Walk me through your project.** Use the 30-second pitch in Level 1.
2. **Why YouTube and not Twitter or Reddit?** YouTube has a free official API with exact timestamps, and every big game has official trailers with thousands of comments. X's API is paid; Reddit's API can't filter by date. Reddit is my next step.
3. **How did you decide which games flopped?** Not by opinion. I checked Steam launch reviews, Metacritic critic and user scores, and player counts. Console user scores split the groups cleanly: flops 3.8 or lower, hits 7.9 or higher.
4. **What was your most surprising finding?** The three kinds of flop. Cyberpunk's pre-launch chatter looked like a hit's; the failure was technical, so no amount of comment analysis would have caught it.

**Technical**

5. **How did you avoid data leakage?** Only comments posted before release were used, and I excluded comments edited after launch, because YouTube keeps the original date but shows the edited text. Topic models were learned on the 8 known games, then applied to GTA VI.
6. **Why didn't you just use VADER?** I did first. On hand-labeled comments it agreed with me at kappa 0.18; Claude reached 0.52. VADER missed 579 sarcastic comments that were actually negative.
7. **How did you validate the LLM?** Blind human labels on random comments, compared with Cohen's kappa. Claude beat dictionary tools by about 3× on sentiment and 5× on skepticism.
8. **Isn't 24,000 comments a big sample? Why is your p-value only 0.029?** The question is about games, not comments, so the sample is 8. With 8 games split 4 and 4, there are 70 possible splits, so the smallest possible p is 2/70 = 0.029. We reached it.
9. **Why a permutation test instead of a t-test?** It assumes nothing about the data's shape and is exact, which matters with only 8 points.
10. **How did you handle imbalance between games?** Cyberpunk had 105,000 comments, Redfall under 3,000. I sampled up to 3,000 per game with a fixed per-comment random key, so each game weighs equally and samples are reproducible.
11. **How did you choose the number of topics?** K = 12 as a starting point. LDA is unstable on short text, so I ran it under two settings and kept only themes that appeared in both, instead of tuning until the result looked good.

**Judgment and business**

12. **What's the biggest weakness?** Eight games and a genre confound: my flops are mostly live-service shooters, my hits single-player RPGs. Negativity is about tone, so it's less affected, but I'd add successful shooters and failed RPGs next.
13. **How would a publisher use this?** Track the share of negative and positive comments on each trailer. A rising negative share or a collapse in positive share is an early warning to rethink marketing, the business model, or the release date.
14. **What would you do with more time?** More games, Reddit as a second platform, two human labelers, and check the GTA VI prediction after its November 2026 launch.
15. **Why did you spend $7 on the LLM instead of sampling?** With 200 comments per game, the margin of error (± 5.5 points) was close to the gap I was measuring. Labeling everything cut it to ± 1.4 and made every method judge the same comments.

## Glossary

| Term | Meaning in plain words |
| --- | --- |
| API (Application Programming Interface) | A way for code to request data from a service, like YouTube or Steam |
| Quota | YouTube's daily limit of 10,000 units; 100 comments cost 1 unit, a search costs 100 |
| Data leakage | Future information sneaking into the input, making results look better than they are |
| Selection bias | A sample that isn't representative, like Steam reviews coming only from buyers |
| Confound | A hidden factor that explains a pattern instead of the one you think (here: genre) |
| VADER | Valence Aware Dictionary and sEntiment Reasoner; a rule-based sentiment scorer for social media |
| Lexicon | A hand-made word list used to detect a theme |
| Lift | How many times more common a word is in one group than another |
| Stopwords | Very common words ("the", "is") removed before analysis |
| Bag of words | Representing text as word counts, ignoring order |
| LDA | Latent Dirichlet Allocation; an unsupervised topic model |
| LLM | Large Language Model, such as Claude |
| Blinding | Hiding information (game names, outcomes) from a labeler so it can't bias the labels |
| Token | A chunk of text (about ¾ of a word) used to measure LLM input and cost |
| Triangulation | Confirming a finding with several independent methods |
| Confidence interval | The range where the true value most likely sits (95% here) |
| Permutation test | A test that tries every possible regrouping to see if a gap could be luck |
| p-value | The chance of a gap this big if there were no real difference |
| Cohen's kappa | Agreement between two labelers, corrected for agreeing by chance |
| Gold standard | The trusted reference, here human labels |
| Retention | Players still active months later divided by launch peak |
| Live service | Games built around ongoing online content and monetization (battle passes, seasons) |
