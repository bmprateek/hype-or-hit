"""Step 12: presentation charts (PNG files in figures/).

Run:  python scripts/10_charts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib
matplotlib.use("Agg")                      # save files only, no pop-up windows
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from hype.config import ROOT, RAW_DIR

PROC_DIR = RAW_DIR.parent / "processed"
FIG_DIR = ROOT / "figures"

# Colorblind-safe palette (validated: the 3 colors stay distinguishable for colorblind viewers)
COLORS = {"overhyped": "#eb6834", "delivered": "#2a78d6", "predict": "#1baf7a"}
GROUP_NAMES = {"overhyped": "Overhyped (flop)", "delivered": "Delivered (hit)", "predict": "GTA VI (prediction)"}
NEUTRAL = "#898781"
INK, INK_2, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
# Label positions (x, y in chart units) for dots that sit too close together
LABEL_POS = {"gta-vi": (30, 25), "cyberpunk-2077": (55, 24), "hogwarts-legacy": (57, 18.5),
             "elden-ring": (57, 14.5), "black-myth-wukong": (57, 10.5), "baldurs-gate-3": (57, 6.5),
             "suicide-squad-ktjl": (22, 9)}
FLOP_TYPES = {"concord": "rejected", "redfall": "rejected",
              "suicide-squad-ktjl": "indifferent", "cyberpunk-2077": "betrayed"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def style(ax, grid_axis="x"):
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def header(fig, title, sub):
    """Title and subtitle, both left-aligned to the figure edge."""
    fig.subplots_adjust(top=0.83)
    fig.text(0.01, 0.97, title, color=INK, fontsize=15, fontweight="bold", ha="left", va="top")
    fig.text(0.01, 0.905, sub, color=INK_2, fontsize=11, ha="left", va="top")


def legend_groups(ax, groups, loc="lower right"):
    handles = [Patch(facecolor=COLORS[g], label=GROUP_NAMES[g]) for g in groups]
    ax.legend(handles=handles, frameon=False, loc=loc, labelcolor=INK)


def save(fig, name):
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved figures/{name}")


def load():
    llm = pd.read_csv(PROC_DIR / "llm_per_game.csv")
    games = pd.read_csv(PROC_DIR / "games.csv")
    llm = llm.merge(games[["game", "name"]], on="game", how="left")
    llm["label"] = llm["name"].replace({"Suicide Squad: Kill the Justice League": "Suicide Squad: KTJL",
                                        "Grand Theft Auto VI": "GTA VI (gameplay reveal)"})
    return llm, games


def chart_negativity(llm, tests):
    """1. Headline: % negative pre-release comments per game."""
    d = llm.sort_values("llm_negative")
    p = tests.set_index("metric").loc["llm_negative", "p_value"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.barh(d["label"], d["llm_negative"], color=d["group"].map(COLORS), height=0.62)
    for y, v in enumerate(d["llm_negative"]):
        ax.text(v + 0.8, y, f"{v:.0f}%", va="center", color=INK, fontsize=10)
    header(fig, "Flops drew more negative comments before launch", f"% of pre-release comments Claude labeled negative · flops avg "
                  f"{llm.loc[llm.group == 'overhyped', 'llm_negative'].mean():.0f}% vs hits avg "
                  f"{llm.loc[llm.group == 'delivered', 'llm_negative'].mean():.0f}% · permutation test p = {p:.3f}")
    ax.set_xlabel("% negative comments")
    ax.set_xlim(0, d["llm_negative"].max() * 1.12)
    style(ax)
    legend_groups(ax, ["overhyped", "delivered", "predict"])
    save(fig, "1_negativity_by_game.png")


def chart_flop_types(llm):
    """2. Positive vs negative: the three kinds of flop."""
    fig, ax = plt.subplots(figsize=(10, 6.2))
    for _, r in llm.iterrows():
        ax.scatter(r["llm_positive"], r["llm_negative"], s=140, color=COLORS[r["group"]],
                   edgecolor=SURFACE, linewidth=2, zorder=3)
        text = r["label"] + (f"  ({FLOP_TYPES[r['game']]})" if r["game"] in FLOP_TYPES else "")
        if r["game"] in LABEL_POS:
            ax.annotate(text, (r["llm_positive"], r["llm_negative"]), xytext=LABEL_POS[r["game"]],
                        textcoords="data", color=INK, fontsize=10, va="center",
                        arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.8, shrinkA=2, shrinkB=6))
        else:
            ax.annotate(text, (r["llm_positive"], r["llm_negative"]), xytext=(9, 5),
                        textcoords="offset points", color=INK, fontsize=10)
    header(fig, "Three kinds of flop: rejected, indifferent, betrayed", "Each dot is one game's pre-release comments (Claude labels). "
                  "Hits sit bottom-right: positive, rarely negative.")
    ax.set_xlabel("% positive comments")
    ax.set_ylabel("% negative comments")
    ax.set_xlim(0, 80)
    ax.set_ylim(0, llm["llm_negative"].max() + 8)
    style(ax, "both")
    handles = [Line2D([], [], marker="o", linestyle="", markersize=9, color=COLORS[g], label=GROUP_NAMES[g])
               for g in ["overhyped", "delivered", "predict"]]
    ax.legend(handles=handles, frameon=False, loc="upper right", labelcolor=INK)
    save(fig, "2_flop_types_scatter.png")


def chart_validation():
    """3. Agreement with a human: Claude vs simple tools."""
    res = pd.read_csv(PROC_DIR / "human_check_results.csv")
    rows = []
    for measure in ["Sentiment", "Skepticism", "Excitement"]:
        sub = res[res["comparison"].str.startswith(measure)]
        claude = sub[sub["comparison"].str.contains("Claude")]["kappa"].iloc[0]
        simple = sub[~sub["comparison"].str.contains("Claude")]["kappa"].iloc[0]
        tool = "VADER" if measure == "Sentiment" else "word list"
        rows.append((measure, claude, simple, tool))

    fig, ax = plt.subplots(figsize=(10, 5))
    y = range(len(rows))
    h = 0.34
    for i, (measure, claude, simple, tool) in enumerate(rows):
        ax.barh(i - h / 2 - 0.02, claude, height=h, color=COLORS["delivered"])
        ax.barh(i + h / 2 + 0.02, simple, height=h, color=NEUTRAL)
        ax.text(max(claude, 0) + 0.01, i - h / 2 - 0.02, f"Claude {claude:.2f}", va="center", color=INK, fontsize=10)
        ax.text(max(simple, 0) + 0.01, i + h / 2 + 0.02, f"{tool} {simple:.2f}", va="center", color=INK_2, fontsize=10)
    ax.set_yticks(list(y), [r[0] for r in rows])
    ax.set_ylim(len(rows) - 0.4, -0.8)
    ax.axvline(0.4, color=AXIS, linestyle="--", linewidth=1)
    ax.text(0.41, -0.62, "0.4 = moderate agreement", color=INK_2, fontsize=9, va="center")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Agreement with a human labeler (Cohen's kappa: 0 = chance, 1 = perfect)")
    header(fig, "Claude reads comments much more like a human does", "Agreement with hand-labeled comments. Simple tools miss sarcasm and indirect doubt.")
    style(ax)
    ax.legend(handles=[Patch(facecolor=COLORS["delivered"], label="Claude (LLM)"),
                       Patch(facecolor=NEUTRAL, label="Simple tool (VADER / word list)")],
              frameon=False, loc="lower right", labelcolor=INK)
    save(fig, "3_llm_vs_simple_tools.png")


def chart_gta(llm):
    """4. GTA VI compared with flop and hit averages."""
    metrics = {"llm_negative": "Negative", "llm_positive": "Positive",
               "llm_excitement": "Excited", "llm_skepticism": "Skeptical"}
    flop = llm[llm.group == "overhyped"][list(metrics)].mean()
    hit = llm[llm.group == "delivered"][list(metrics)].mean()
    gta = llm[llm.group == "predict"][list(metrics)].iloc[0]

    fig, ax = plt.subplots(figsize=(10, 4.8))
    for i, m in enumerate(metrics):
        ax.plot([flop[m], hit[m]], [i, i], color=GRID, linewidth=6, solid_capstyle="round", zorder=1)
        for val, g, dy in [(flop[m], "overhyped", -0.28), (hit[m], "delivered", -0.28), (gta[m], "predict", 0.32)]:
            ax.scatter(val, i, s=150, color=COLORS[g], edgecolor=SURFACE, linewidth=2, zorder=3)
            ax.text(val, i + dy, f"{val:.0f}%", ha="center", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(metrics)), [f"% {v.lower()}" for v in metrics.values()])
    ax.invert_yaxis()
    ax.set_ylim(len(metrics) - 0.4, -0.6)
    ax.set_xlim(0, 60)
    ax.set_xlabel("% of pre-release comments")
    header(fig, "GTA VI looks closer to the hits, with some caution", "GTA VI gameplay reveal vs average flop and average hit (Claude labels). "
                  "Like Cyberpunk, it can't reveal technical problems.")
    style(ax)
    ax.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=9, color=COLORS[g],
                              label=lab) for g, lab in [("overhyped", "Average flop"),
                                                        ("delivered", "Average hit"),
                                                        ("predict", "GTA VI")]],
              frameon=False, loc="lower right", labelcolor=INK)
    save(fig, "4_gta_vs_averages.png")


def chart_outcomes(games):
    """5. Did the 'overhyped' games really disappoint? Two outcome measures, two panels."""
    d = games[games["group"].isin(["overhyped", "delivered"])].copy()
    d["label"] = d["name"].replace({"Suicide Squad: Kill the Justice League": "Suicide Squad: KTJL"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), sharey=False)
    panels = [("week_pct_positive", "Steam: % positive reviews, launch week", 100, "{:.0f}%"),
              ("mc_user_console", "Metacritic: console user score (0 to 10)", 10, "{:.1f}")]
    for ax, (col, title, xmax, fmt) in zip(axes, panels):
        s = d.sort_values(col)
        ax.barh(s["label"], s[col], color=s["group"].map(COLORS), height=0.62)
        for y, v in enumerate(s[col]):
            ax.text(v + xmax * 0.01, y, fmt.format(v), va="center", color=INK, fontsize=10)
        ax.set_xlim(0, xmax * 1.1)
        ax.set_title(title, fontsize=12, pad=8)
        style(ax)
    fig.suptitle("The outcomes: how each game was actually received", x=0.01, ha="left",
                 fontsize=15, fontweight="bold", y=1.02)
    legend_groups(axes[1], ["overhyped", "delivered"])
    fig.tight_layout()
    save(fig, "5_launch_outcomes.png")


def main():
    llm, games = load()
    tests = pd.read_csv(PROC_DIR / "llm_permutation_tests.csv")
    print("Creating charts...")
    chart_negativity(llm, tests)
    chart_flop_types(llm)
    chart_validation()
    chart_gta(llm)
    chart_outcomes(games)
    print(f"Done. Open the {FIG_DIR.name}/ folder.")


if __name__ == "__main__":
    main()