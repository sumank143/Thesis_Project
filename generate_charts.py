"""
Step 2 of Results generation: build the 5 charts for the Results chapter
from data already aggregated (accuracy_summary.csv, accuracy_by_level.csv,
rq2_failure_summary.csv, consistency_*.csv, efficiency_*.csv).

Colors follow the dataviz skill's validated categorical palette (fixed hue
order, colorblind-safe) rather than matplotlib defaults.

Usage:
    python generate_charts.py
"""
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- palette (validated categorical order, light mode) ---
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GRAY_MIXED = "#9aa0a8"
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

MODEL_ORDER = ["gpt-4.1-mini", "claude-haiku-4.5", "gemini-3.5-flash-lite"]
MODEL_LABELS = {"gpt-4.1-mini": "GPT-4.1-mini", "claude-haiku-4.5": "Claude Haiku 4.5", "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite"}

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.grid(axis="y", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

# ============================================================
# Chart 1: Overall accuracy, schema-aware vs zero-shot, by model
# ============================================================
def chart1():
    with open("accuracy_summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = {m: {} for m in MODEL_ORDER}
    for r in rows:
        data[r["model"]][r["condition"]] = int(r["correct"])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(MODEL_ORDER))
    width = 0.32
    sa = [data[m]["schema-aware"] for m in MODEL_ORDER]
    zs = [data[m]["zero-shot"] for m in MODEL_ORDER]

    b1 = ax.bar([i - width/2 for i in x], sa, width, label="Schema-aware", color=BLUE, zorder=3)
    b2 = ax.bar([i + width/2 for i in x], zs, width, label="Zero-shot", color=ORANGE, zorder=3)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h}", (bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=9.5, color=PRIMARY_INK)

    ax.set_ylim(0, 55)
    ax.set_ylabel("Correct (out of 50)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    ax.set_title("Semantic Accuracy by Model and Prompting Condition", loc="left", fontsize=13, color=PRIMARY_INK, pad=14)
    ax.legend(frameon=False, loc="upper right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig("charts/01_accuracy_overall.png", dpi=200)
    plt.close(fig)
    print("Saved charts/01_accuracy_overall.png")

# ============================================================
# Chart 2: Accuracy by complexity level, small multiples per model
# ============================================================
def chart2():
    with open("accuracy_by_level.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = {m: {} for m in MODEL_ORDER}
    for r in rows:
        data[r["model"]].setdefault(r["condition"], {})[r["level"]] = (int(r["correct"]), int(r["total"]))

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    levels = ["1", "2", "3", "4"]
    width = 0.32
    for ax, m in zip(axes, MODEL_ORDER):
        x = range(len(levels))
        sa = [data[m]["schema-aware"][l][0] / data[m]["schema-aware"][l][1] * 100 for l in levels]
        zs = [data[m]["zero-shot"][l][0] / data[m]["zero-shot"][l][1] * 100 for l in levels]
        ax.bar([i - width/2 for i in x], sa, width, color=BLUE, zorder=3, label="Schema-aware")
        ax.bar([i + width/2 for i in x], zs, width, color=ORANGE, zorder=3, label="Zero-shot")
        ax.set_xticks(list(x))
        ax.set_xticklabels([f"L{l}" for l in levels])
        ax.set_title(MODEL_LABELS[m], fontsize=11.5, color=PRIMARY_INK)
        ax.set_ylim(0, 105)
        style_axes(ax)
    axes[0].set_ylabel("Accuracy (%)")
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.06))
    fig.suptitle("Accuracy by Complexity Level", x=0.02, ha="left", fontsize=13, color=PRIMARY_INK, y=1.14)
    fig.tight_layout()
    fig.savefig("charts/02_accuracy_by_level.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved charts/02_accuracy_by_level.png")

# ============================================================
# Chart 3: Failure category breakdown, stacked bar by model+condition
# ============================================================
def chart3():
    with open("rq2_failure_summary.csv", newline="", encoding="utf-8") as f:
        content = f.read()
    section = content.split("\n\n")[0]
    reader = csv.DictReader(section.splitlines())
    rows = list(reader)

    cats = ["hallucinated_schema", "wrong_join_path", "column_shape_mismatch", "wrong_aggregation", "wrong_filter"]
    cat_labels = ["Hallucinated schema", "Wrong join path", "Column-shape mismatch", "Wrong aggregation", "Wrong filter"]
    colors = [BLUE, ORANGE, GRAY_MIXED, AQUA, YELLOW]

    labels = []
    values = {c: [] for c in cats}
    for m in MODEL_ORDER:
        for cond, condlabel in [("schema-aware", "SA"), ("zero-shot", "ZS")]:
            row = next(r for r in rows if r["model"] == m and r["condition"] == cond)
            labels.append(f"{MODEL_LABELS[m].split()[0]}\n{condlabel}")
            for c in cats:
                values[c].append(int(row[c]))

    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = range(len(labels))
    bottom = [0] * len(labels)
    for c, label, color in zip(cats, cat_labels, colors):
        bars = ax.bar(x, values[c], bottom=bottom, color=color, label=label, zorder=3, width=0.6)
        for i, bar in enumerate(bars):
            h = values[c][i]
            if h > 0:
                ax.annotate(str(h), (bar.get_x() + bar.get_width()/2, bottom[i] + h/2),
                            ha="center", va="center", fontsize=9, color="white" if color != YELLOW else PRIMARY_INK)
        bottom = [b + v for b, v in zip(bottom, values[c])]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("Number of failures")
    ax.set_title("Failure Category by Model and Prompting Condition", loc="left", fontsize=13, color=PRIMARY_INK, pad=45)
    ax.set_ylim(0, max(bottom) * 1.22)
    ax.legend(frameon=False, loc="upper center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, 1.06))
    style_axes(ax)
    fig.tight_layout()
    fig.savefig("charts/03_failure_categories.png", dpi=200)
    plt.close(fig)
    print("Saved charts/03_failure_categories.png")

# ============================================================
# Chart 4: Output consistency (out of 10) by model
# ============================================================
def chart4():
    # numbers already confirmed in methodology notes: GPT 10/10, Claude 9/10, Gemini 8/10
    consistency = {"gpt-4.1-mini": 10, "claude-haiku-4.5": 9, "gemini-3.5-flash-lite": 8}
    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(MODEL_ORDER))
    vals = [consistency[m] for m in MODEL_ORDER]
    bars = ax.bar(x, vals, color=BLUE, zorder=3, width=0.5)
    for bar, v in zip(bars, vals):
        ax.annotate(f"{v}/10", (bar.get_x() + bar.get_width()/2, v), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=10, color=PRIMARY_INK)
    ax.set_ylim(0, 11)
    ax.set_xticks(list(x))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    ax.set_ylabel("Consistent queries (out of 10)")
    ax.set_title("Output Consistency (schema-aware, 5 repeats per query)", loc="left", fontsize=12.5, color=PRIMARY_INK, pad=14)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig("charts/04_consistency.png", dpi=200)
    plt.close(fig)
    print("Saved charts/04_consistency.png")

# ============================================================
# Chart 5: Query efficiency, stacked bar by model
# ============================================================
def chart5():
    files = {"gpt-4.1-mini": "efficiency_gpt.csv", "claude-haiku-4.5": "efficiency_claude.csv", "gemini-3.5-flash-lite": "efficiency_gemini.csv"}
    counts = {}
    for m, fn in files.items():
        with open(fn, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        c = {"same": 0, "model_less_efficient": 0, "model_more_efficient": 0, "mixed": 0}
        classification_col = None
        for candidate in ["classification", "result", "comparison"]:
            if rows and candidate in rows[0]:
                classification_col = candidate
                break
        if classification_col is None:
            classification_col = list(rows[0].keys())[-1] if rows else None
        for r in rows:
            val = r.get(classification_col, "")
            if val in c:
                c[val] += 1
        counts[m] = c

    cats = ["same", "model_less_efficient", "model_more_efficient", "mixed"]
    cat_labels = ["Same efficiency", "Model less efficient", "Model more efficient", "Mixed (scans vs. rows disagree)"]
    colors = [BLUE, ORANGE, AQUA, GRAY_MIXED]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(MODEL_ORDER))
    bottom = [0] * len(MODEL_ORDER)
    for c, label, color in zip(cats, cat_labels, colors):
        vals = [counts[m][c] for m in MODEL_ORDER]
        bars = ax.bar(x, vals, bottom=bottom, color=color, label=label, zorder=3, width=0.5)
        for i, bar in enumerate(bars):
            if vals[i] > 0:
                ax.annotate(str(vals[i]), (bar.get_x() + bar.get_width()/2, bottom[i] + vals[i]/2),
                            ha="center", va="center", fontsize=9.5, color="white")
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xticks(list(x))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    ax.set_ylabel("Number of correct queries")
    ax.set_title("Query Efficiency vs. Ground Truth (schema-aware, correct queries only)", loc="left", fontsize=12, color=PRIMARY_INK, pad=45)
    ax.set_ylim(0, max(bottom) * 1.22)
    ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, 1.06))
    style_axes(ax)
    fig.tight_layout()
    fig.savefig("charts/05_efficiency.png", dpi=200)
    plt.close(fig)
    print("Saved charts/05_efficiency.png")
    print("(debug) efficiency column used:", classification_col, "| sample row:", rows[0] if rows else None)

if __name__ == "__main__":
    chart1()
    chart2()
    chart3()
    chart4()
    chart5()
