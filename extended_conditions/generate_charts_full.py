"""
Figure 7 and Figure 8 for the thesis's extended-conditions section
(Sections 3.5 / 4.5), covering all FOUR conditions (C1-C4), matching the
palette/style of the main-study generate_charts.py and this folder's own
analyze_and_chart.py.

Figure 7: grouped bar, accuracy % across the four conditions x two models.
Figure 8: horizontal bar, seven-category failure distribution (Table 9).

Labels use the corrected terminology throughout (generic prompt / precise
prompting / explicit column specification - never "hint" or "plain/precise
wording").

Run from the thesis-nl2sql/ folder root:
    python extended_conditions/generate_charts_full.py

Figure 8 reads extended_conditions/table9_classification_final.csv. That
file does not exist until you (1) run classify_failures_extended.py to
produce table9_classification.csv, then (2) manually review its
"unclear"/"actually_correct_after_normalization" rows and save the
reviewed copy as table9_classification_final.csv with a category_final
column (defaulting unreviewed rows' category_final to their category).
"""
import csv
import os
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
MAGENTA = "#e87ba4"
PURPLE = "#8a63d2"
TEAL = "#2596a1"

PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "font.family": "sans-serif",
    "text.color": PRIMARY_INK,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": SECONDARY_INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "grid.color": GRID,
    "font.size": 11,
})

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(BASE, "extended_conditions")
CHART_DIR = os.path.join(EXT, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

MODEL_ORDER = ["gpt-4.1-mini", "gemini-3.5-flash-lite"]
MODEL_LABELS = {"gpt-4.1-mini": "GPT-4.1-mini", "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite"}

CONDITION_ORDER = [
    "condition1_unaware",
    "condition2_aware_no_hints",
    "condition3_fewshot",
    "condition4_precise_wording",
]
CONDITION_LABELS = {
    "condition1_unaware": "C1: Schema-unaware,\nno column spec.",
    "condition2_aware_no_hints": "C2: Schema-aware,\nno column spec.",
    "condition3_fewshot": "C3: Generic prompt,\nno column spec.",
    "condition4_precise_wording": "C4: Precise prompting,\nno column spec.",
}

RESULT_FILES = {
    ("condition1_unaware", "gpt-4.1-mini"): os.path.join(EXT, "results_condition1_unaware_gpt.csv"),
    ("condition1_unaware", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition1_unaware_gemini.csv"),
    ("condition2_aware_no_hints", "gpt-4.1-mini"): os.path.join(EXT, "results_condition2_aware_no_hints_gpt.csv"),
    ("condition2_aware_no_hints", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition2_aware_no_hints_gemini.csv"),
    ("condition3_fewshot", "gpt-4.1-mini"): os.path.join(EXT, "results_condition3_fewshot_gpt.csv"),
    ("condition3_fewshot", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition3_fewshot_gemini.csv"),
    ("condition4_precise_wording", "gpt-4.1-mini"): os.path.join(EXT, "results_condition4_precise_wording_gpt.csv"),
    ("condition4_precise_wording", "gemini-3.5-flash-lite"): os.path.join(EXT, "results_condition4_precise_wording_gemini.csv"),
}

def to_bool(s):
    return str(s).strip().lower() == "true"

def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis="y", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def figure7_accuracy():
    all_data = {key: load_rows(path) for key, path in RESULT_FILES.items()}
    overall = {}
    for (cond, model), rows in all_data.items():
        total = len(rows)
        correct = sum(1 for r in rows if to_bool(r["correct"]))
        accuracy_pct = round(100 * correct / total, 1) if total else 0.0
        overall[(cond, model)] = accuracy_pct

    fig, ax = plt.subplots(figsize=(9.5, 5))
    x = range(len(CONDITION_ORDER))
    width = 0.32
    gpt_vals = [overall[(c, "gpt-4.1-mini")] for c in CONDITION_ORDER]
    gem_vals = [overall[(c, "gemini-3.5-flash-lite")] for c in CONDITION_ORDER]

    b1 = ax.bar([i - width / 2 for i in x], gpt_vals, width, label=MODEL_LABELS["gpt-4.1-mini"], color=BLUE, zorder=3)
    b2 = ax.bar([i + width / 2 for i in x], gem_vals, width, label=MODEL_LABELS["gemini-3.5-flash-lite"], color=ORANGE, zorder=3)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h}%", (bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=9.5, color=PRIMARY_INK)

    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], fontsize=9)
    ax.set_title("Accuracy Across Extended Conditions (C1–C4)", loc="left", fontsize=13, color=PRIMARY_INK, pad=14)
    ax.legend(frameon=False, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    out = os.path.join(CHART_DIR, "07_accuracy_all_four_conditions.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("Saved", out)


def figure8_failure_categories():
    path = os.path.join(EXT, "table9_classification_final.csv")
    if not os.path.exists(path):
        print("SKIPPED Figure 8:", path, "not found - run "
              "classify_failures_extended.py, then manually review its output "
              "and save the reviewed copy (with a category_final column) as "
              "table9_classification_final.csv")
        return

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    counts = Counter(r["category_final"] for r in rows)

    # Map raw classifier category names to the thesis's seven official
    # category labels (corrected terminology, no "hint").
    LABELS = {
        "column_shape_mismatch": "Column-shape mismatch",
        "hallucinated_schema": "Hallucinated schema",
        "output_formatting_mismatch": "Output formatting mismatch",
        "wrong_join_path": "Wrong join path",
        "wrong_aggregation": "Wrong aggregation",
        "syntax_error": "SQL syntax error",
        "wrong_filter": "Wrong filter / other",
    }
    ORDER = [
        "column_shape_mismatch", "hallucinated_schema",
        "output_formatting_mismatch", "wrong_join_path",
        "wrong_aggregation", "syntax_error", "wrong_filter",
    ]
    COLORS = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, PURPLE, TEAL]

    present = sorted([c for c in ORDER if counts.get(c, 0) > 0], key=lambda c: -counts[c])
    values = [counts[c] for c in present]
    labels = [LABELS[c] for c in present]
    colors = [COLORS[ORDER.index(c)] for c in present]
    total = sum(counts.values())

    fig, ax = plt.subplots(figsize=(9, 5))
    y = range(len(present))
    bars = ax.barh(list(y), values, color=colors, zorder=3)
    for i, bar in enumerate(bars):
        w = bar.get_width()
        pct = 100.0 * w / total
        ax.annotate(f"{int(w)} ({pct:.1f}%)", (w, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points", va="center", fontsize=9.5, color=PRIMARY_INK)

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Count of failing queries")
    ax.set_title(f"Failure Category Distribution Across All Four Conditions (n={total})",
                 loc="left", fontsize=12.5, color=PRIMARY_INK, pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis="x", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    out = os.path.join(CHART_DIR, "08_failure_categories_all_conditions.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("Saved", out)


if __name__ == "__main__":
    figure7_accuracy()
    figure8_failure_categories()
