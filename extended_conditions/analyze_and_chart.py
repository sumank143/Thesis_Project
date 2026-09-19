"""
Analysis and charting for extended NL2SQL conditions 1-3.
Mirrors the palette/style of the original generate_charts.py but writes
only into extended_conditions/ and extended_conditions/charts/ - it does
not read or write any file outside this folder except the result CSVs
this condition set itself produced.

Usage:
    python extended_conditions/analyze_and_chart.py
"""
import csv
import os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- palette (same validated categorical order as generate_charts.py) ---
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
MAGENTA = "#e87ba4"

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

MODEL_ORDER = ["gpt-4.1-mini", "gemini-3.5-flash-lite"]
MODEL_LABELS = {"gpt-4.1-mini": "GPT-4.1-mini", "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite"}

CONDITION_ORDER = [
    "condition1_unaware",
    "condition2_aware_no_hints",
    "condition3_fewshot",
]
CONDITION_LABELS = {
    "condition1_unaware": "C1: Unaware\n(zero-shot, no hints)",
    "condition2_aware_no_hints": "C2: Aware\n(zero-shot, no hints)",
    "condition3_fewshot": "C3: Few-shot\n(no hints)",
}

RESULT_FILES = {
    ("condition1_unaware", "gpt-4.1-mini"): "extended_conditions/results_condition1_unaware_gpt.csv",
    ("condition1_unaware", "gemini-3.5-flash-lite"): "extended_conditions/results_condition1_unaware_gemini.csv",
    ("condition2_aware_no_hints", "gpt-4.1-mini"): "extended_conditions/results_condition2_aware_no_hints_gpt.csv",
    ("condition2_aware_no_hints", "gemini-3.5-flash-lite"): "extended_conditions/results_condition2_aware_no_hints_gemini.csv",
    ("condition3_fewshot", "gpt-4.1-mini"): "extended_conditions/results_condition3_fewshot_gpt.csv",
    ("condition3_fewshot", "gemini-3.5-flash-lite"): "extended_conditions/results_condition3_fewshot_gemini.csv",
}

CHART_DIR = "extended_conditions/charts"

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

# ============================================================
# Load data
# ============================================================
all_data = {key: load_rows(path) for key, path in RESULT_FILES.items()}
print(f"Loaded {sum(len(v) for v in all_data.values())} result rows from {len(RESULT_FILES)} files")

# ============================================================
# Compute: overall per-condition, per-model stats
# ============================================================
overall = {}
for (cond, model), rows in all_data.items():
    total = len(rows)
    correct = sum(1 for r in rows if to_bool(r["correct"]))
    ran_ok = sum(1 for r in rows if to_bool(r["ran_ok"]))
    exec_fail_count = sum(1 for r in rows if not to_bool(r["ran_ok"]))
    ran_but_wrong_count = sum(1 for r in rows if to_bool(r["ran_ok"]) and not to_bool(r["correct"]))
    accuracy_pct = round(100 * correct / total, 1) if total else 0.0
    overall[(cond, model)] = {
        "total": total, "correct": correct, "accuracy_pct": accuracy_pct,
        "ran_ok": ran_ok, "exec_fail_count": exec_fail_count, "ran_but_wrong_count": ran_but_wrong_count,
    }

# ============================================================
# Compute: per-level accuracy breakdown per condition/model
# ============================================================
by_level = defaultdict(lambda: {"correct": 0, "total": 0})
for (cond, model), rows in all_data.items():
    for r in rows:
        key = (cond, model, r["level"])
        by_level[key]["total"] += 1
        by_level[key]["correct"] += int(to_bool(r["correct"]))

# ============================================================
# Save final_summary.csv (multi-section, same convention as rq2_failure_summary.csv)
# ============================================================
with open("extended_conditions/final_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)

    w.writerow(["# SECTION: overall_summary"])
    w.writerow(["condition", "model", "total", "correct", "accuracy_pct", "ran_ok", "exec_fail_count", "ran_but_wrong_count"])
    for cond in CONDITION_ORDER:
        for model in MODEL_ORDER:
            s = overall[(cond, model)]
            w.writerow([cond, model, s["total"], s["correct"], s["accuracy_pct"], s["ran_ok"], s["exec_fail_count"], s["ran_but_wrong_count"]])
    w.writerow([])

    w.writerow(["# SECTION: by_level"])
    w.writerow(["condition", "model", "level", "correct", "total", "accuracy_pct"])
    for cond in CONDITION_ORDER:
        for model in MODEL_ORDER:
            levels = sorted({lvl for (c, m, lvl) in by_level if c == cond and m == model})
            for lvl in levels:
                s = by_level[(cond, model, lvl)]
                acc = round(100 * s["correct"] / s["total"], 1) if s["total"] else 0.0
                w.writerow([cond, model, lvl, s["correct"], s["total"], acc])

print("\nDone. Summary saved to extended_conditions/final_summary.csv")

# ============================================================
# Chart 1: Grouped bar - accuracy % across conditions 1-3 x 2 models
# ============================================================
def chart1():
    fig, ax = plt.subplots(figsize=(9.5, 5))
    x = range(len(CONDITION_ORDER))
    width = 0.32
    gpt_vals = [overall[(c, "gpt-4.1-mini")]["accuracy_pct"] for c in CONDITION_ORDER]
    gem_vals = [overall[(c, "gemini-3.5-flash-lite")]["accuracy_pct"] for c in CONDITION_ORDER]

    b1 = ax.bar([i - width/2 for i in x], gpt_vals, width, label=MODEL_LABELS["gpt-4.1-mini"], color=BLUE, zorder=3)
    b2 = ax.bar([i + width/2 for i in x], gem_vals, width, label=MODEL_LABELS["gemini-3.5-flash-lite"], color=ORANGE, zorder=3)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h}%", (bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=9.5, color=PRIMARY_INK)

    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], fontsize=9)
    ax.set_title("Accuracy Across Extended Conditions (C1-C3)", loc="left", fontsize=13, color=PRIMARY_INK, pad=14)
    ax.legend(frameon=False, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(f"{CHART_DIR}/01_accuracy_all_conditions.png", dpi=200)
    plt.close(fig)
    print(f"Saved {CHART_DIR}/01_accuracy_all_conditions.png")

# ============================================================
# Chart 2: Stacked bar - exec_fail vs ran_but_wrong vs correct, C1 vs C2
# ============================================================
def chart2():
    groups = [
        ("condition1_unaware", "gpt-4.1-mini"),
        ("condition1_unaware", "gemini-3.5-flash-lite"),
        ("condition2_aware_no_hints", "gpt-4.1-mini"),
        ("condition2_aware_no_hints", "gemini-3.5-flash-lite"),
    ]
    labels = ["C1\nGPT-4.1-mini", "C1\nGemini", "C2\nGPT-4.1-mini", "C2\nGemini"]
    cats = ["exec_fail_count", "ran_but_wrong_count", "correct"]
    cat_labels = ["Execution failed", "Ran, wrong result", "Correct"]
    colors = [ORANGE, YELLOW, AQUA]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(groups))
    bottom = [0] * len(groups)
    for cat, label, color in zip(cats, cat_labels, colors):
        vals = [overall[g][cat] for g in groups]
        bars = ax.bar(x, vals, bottom=bottom, color=color, label=label, zorder=3, width=0.55)
        for i, bar in enumerate(bars):
            if vals[i] > 0:
                ax.annotate(str(vals[i]), (bar.get_x() + bar.get_width()/2, bottom[i] + vals[i]/2),
                            ha="center", va="center", fontsize=9.5,
                            color="white" if color != YELLOW else PRIMARY_INK)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("Number of queries (out of 50)")
    ax.set_title("Execution Outcome: Schema-Unaware (C1) vs Schema-Aware (C2), No Column Hints",
                 loc="left", fontsize=12, color=PRIMARY_INK, pad=45)
    ax.set_ylim(0, max(bottom) * 1.2)
    ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, 1.08))
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(f"{CHART_DIR}/02_execution_outcome_c1_vs_c2.png", dpi=200)
    plt.close(fig)
    print(f"Saved {CHART_DIR}/02_execution_outcome_c1_vs_c2.png")

if __name__ == "__main__":
    os.makedirs(CHART_DIR, exist_ok=True)
    chart1()
    chart2()
