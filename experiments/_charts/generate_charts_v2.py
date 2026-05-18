"""Generate full chart set for ALL 11 experiments (replaces v1)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent  # code/
EXP_DIR = ROOT / "experiments"
OUT = EXP_DIR / "_charts"
OUT.mkdir(parents=True, exist_ok=True)


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(name: str) -> None:
    plt.tight_layout()
    plt.savefig(OUT / name, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  saved {OUT / name}")


# Map: experiment id → (folder, label_for_chart, family)
LLM_EXPERIMENTS = [
    ("exp01", "exp01_llamaguard7b_4900", "LlamaGuard 7B", "Guard 1"),
    ("exp04", "exp04_llamaguard3_1b_4900", "LG 3 1B", "Guard 3"),
    ("exp05", "exp05_llamaguard3_8b_4900", "LG 3 8B", "Guard 3"),
    ("exp06", "exp06_shieldgemma2b_4900", "ShieldGemma 2B", "ShieldGemma"),
    ("exp08", "exp08_qwen25_7b_4900", "Qwen 7B v1", "General LLM"),
    ("exp09", "exp09_qwen25_7b_4900_v2 - old", "Qwen 7B v2", "General LLM"),
    ("exp10", "exp10_qwen25_7b_4900_v3", "Qwen 7B v3", "General LLM"),
    ("exp11", "exp11_llama31_8b_instruct_4900", "Llama 3.1 8B", "General LLM"),
]

FAMILY_COLORS = {
    "Guard 1": "#8b5cf6",
    "Guard 3": "#3b82f6",
    "ShieldGemma": "#9ca3af",
    "General LLM": "#10b981",
}


def get_summary(folder: str) -> dict | None:
    """Get LLM-row summary from main summary.csv (or summary_llm.csv for exp03)."""
    p = EXP_DIR / folder
    for fn in ("summary.csv", "summary_llm.csv"):
        rows = _load_csv(p / fn)
        for r in rows:
            if r.get("method") == "llm":
                return r
    return None


def get_casetype(folder: str) -> list[dict]:
    p = EXP_DIR / folder
    for fn in ("casetype.csv", "casetype_llm.csv"):
        rows = _load_csv(p / fn)
        if rows:
            return [r for r in rows if r.get("method") == "llm"]
    return []


# =========== Chart 1: F1 comparison across all LLMs ===========
def chart_f1_comparison():
    fig, ax = plt.subplots(figsize=(11, 5.5))
    labels = []
    f1s = []
    colors = []
    for eid, folder, label, family in LLM_EXPERIMENTS:
        s = get_summary(folder)
        if not s:
            labels.append(f"{label}\n(no data)")
            f1s.append(0)
            colors.append("#e5e7eb")
            continue
        try:
            f1 = float(s.get("f1", 0))
        except ValueError:
            f1 = 0
        labels.append(label)
        f1s.append(f1)
        colors.append(FAMILY_COLORS.get(family, "#999"))

    x = np.arange(len(labels))
    bars = ax.bar(x, f1s, color=colors)
    for bar, v in zip(bars, f1s):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01, f"{v:.3f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("F1 score")
    ax.set_ylim(0, 1.0)
    ax.set_title("F1 salīdzinājums visiem LLM eksperimentiem (N=4900)")
    ax.grid(True, axis="y", alpha=0.3)
    # legend by family
    from matplotlib.patches import Patch
    leg = [Patch(facecolor=c, label=f) for f, c in FAMILY_COLORS.items()]
    ax.legend(handles=leg, loc="upper left", fontsize=9)
    _save("11_f1_all_llms.png")


# =========== Chart 2: Recall vs FPR scatter (the tradeoff) ===========
def chart_recall_fpr():
    fig, ax = plt.subplots(figsize=(9, 7))
    for eid, folder, label, family in LLM_EXPERIMENTS:
        s = get_summary(folder)
        if not s:
            continue
        try:
            recall = float(s.get("recall", 0))
            fpr = float(s.get("fpr", 0))
        except ValueError:
            continue
        if recall == 0 and fpr == 0:
            continue
        color = FAMILY_COLORS.get(family, "#999")
        ax.scatter(fpr, recall, s=180, c=color, edgecolors="black", linewidths=1.5, zorder=3)
        ax.annotate(label, (fpr, recall), xytext=(8, 8), textcoords="offset points",
                    fontsize=9, fontweight="bold")
    # diagonal "random" line
    ax.plot([0, 1], [0, 1], "--", color="#ccc", linewidth=1, label="Random baseline")
    ax.set_xlabel("FPR (False Positive Rate)")
    ax.set_ylabel("Recall (True Positive Rate)")
    ax.set_xlim(-0.02, 0.52)
    ax.set_ylim(-0.02, 0.9)
    ax.set_title("Recall vs FPR — augšējais kreisais stūris ir vēlamais")
    ax.grid(True, alpha=0.3)
    from matplotlib.patches import Patch
    leg = [Patch(facecolor=c, label=f) for f, c in FAMILY_COLORS.items()]
    ax.legend(handles=leg + [plt.Line2D([0], [0], color="#ccc", linestyle="--", label="Random")],
              loc="lower right", fontsize=9)
    _save("12_recall_vs_fpr_scatter.png")


# =========== Chart 3: Qwen prompt iteration arc ===========
def chart_qwen_arc():
    versions = ["v1 (aggressive)", "v2 (strict)", "v3 (balanced)"]
    folders = ["exp08_qwen25_7b_4900",
               "exp09_qwen25_7b_4900_v2 - old",
               "exp10_qwen25_7b_4900_v3"]
    metrics = {"recall": [], "fpr": [], "f1": []}
    for f in folders:
        s = get_summary(f)
        if s:
            metrics["recall"].append(float(s["recall"]))
            metrics["fpr"].append(float(s["fpr"]))
            metrics["f1"].append(float(s["f1"]))
        else:
            for k in metrics:
                metrics[k].append(0)

    x = np.arange(len(versions))
    width = 0.27
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#3b82f6", "#ef4444", "#10b981"]
    for i, (k, vals) in enumerate(metrics.items()):
        bars = ax.bar(x + (i - 1) * width, vals, width, label=k.upper(), color=colors[i])
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01,
                    f"{v:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(versions)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Vērtība")
    ax.set_title("Qwen 2.5 7B Instruct — prompt iterāciju arka (exp08 → exp09 → exp10)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    _save("13_qwen_prompt_arc.png")


# =========== Chart 4: Qwen v1 vs Llama 3.1 8B — same prompt, different model ===========
def chart_model_vs_model():
    metrics = ["F1", "Recall", "Precision", "FPR"]
    qwen = get_summary("exp08_qwen25_7b_4900")
    llama = get_summary("exp11_llama31_8b_instruct_4900")
    qwen_vals = [float(qwen["f1"]), float(qwen["recall"]),
                 float(qwen["precision"]), float(qwen["fpr"])]
    llama_vals = [float(llama["f1"]), float(llama["recall"]),
                  float(llama["precision"]), float(llama["fpr"])]
    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5.5))
    b1 = ax.bar(x - width / 2, qwen_vals, width, label="Qwen 2.5 7B (exp08)", color="#10b981")
    b2 = ax.bar(x + width / 2, llama_vals, width, label="Llama 3.1 8B (exp11)", color="#3b82f6")
    for b, v in zip(b1, qwen_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}",
                ha="center", va="bottom", fontsize=8)
    for b, v in zip(b2, llama_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel("Vērtība")
    ax.set_ylim(0, 1.05)
    ax.set_title("Tas pats prompt — divi modeļi (Qwen vs Llama 3.1)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    _save("14_qwen_vs_llama31.png")


# =========== Chart 5: Per-case-type recall heatmap (all LLMs) ===========
def chart_per_case_type_heatmap():
    case_types = ["threat", "obscene", "identity_attack",
                  "sexual_explicit", "insult", "clean"]
    data = []
    labels = []
    for eid, folder, label, family in LLM_EXPERIMENTS:
        rows = get_casetype(folder)
        if not rows:
            continue
        recall_map = {r["case_type"]: float(r.get("recall", 0)) for r in rows}
        data.append([recall_map.get(c, 0) for c in case_types])
        labels.append(label)

    arr = np.array(data)
    fig, ax = plt.subplots(figsize=(10, 0.6 * len(labels) + 1.5))
    im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=0.9, aspect="auto")
    ax.set_xticks(range(len(case_types)))
    ax.set_xticklabels(case_types, rotation=20, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(case_types)):
            v = arr[i, j]
            text_color = "white" if v < 0.3 or v > 0.7 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=9, color=text_color, fontweight="bold")
    cbar = plt.colorbar(im, ax=ax, fraction=0.025)
    cbar.set_label("Recall")
    ax.set_title("Recall pa kategorijām — visi LLM eksperimenti")
    _save("15_per_case_type_heatmap.png")


# =========== Chart 6: Category exact-match comparison (Qwen v1/v2/v3 + Llama 3.1) ===========
def chart_category_exact_match():
    labels = []
    rates = []
    colors = []
    for eid, folder, label, family in LLM_EXPERIMENTS:
        p = EXP_DIR / folder / "category_confusion.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        m = d.get("llm", {})
        labels.append(label)
        rates.append(m.get("exact_match_rate", 0))
        colors.append(FAMILY_COLORS.get(family, "#999"))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(x, rates, color=colors)
    for bar, v in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.003,
                f"{v*100:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15)
    ax.set_ylabel("Exact match rate")
    ax.set_ylim(0, max(rates) * 1.3 if rates else 1)
    ax.set_title("Kategorijas eksakta sakritība (primary_case_type)")
    ax.grid(True, axis="y", alpha=0.3)
    _save("16_category_exact_match.png")


# =========== Chart 7: Latency comparison (all LLMs) ===========
def chart_latency():
    labels = []
    latencies = []
    colors = []
    for eid, folder, label, family in LLM_EXPERIMENTS:
        s = get_summary(folder)
        if not s:
            continue
        try:
            l = float(s["avg_latency_sec"]) * 1000
        except (ValueError, KeyError):
            continue
        if l <= 0:
            continue
        labels.append(label)
        latencies.append(l)
        colors.append(FAMILY_COLORS.get(family, "#999"))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(x, latencies, color=colors)
    for bar, v in zip(bars, latencies):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.05,
                f"{v:.0f} ms", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Vidējā latence (ms, log skala)")
    ax.set_yscale("log")
    ax.set_title("Latence katram modelim (zemāks = ātrāks)")
    ax.grid(True, axis="y", alpha=0.3)
    _save("17_latency_all_llms.png")


def main():
    print("Generating updated chart set (v2)...")
    chart_f1_comparison()
    chart_recall_fpr()
    chart_qwen_arc()
    chart_model_vs_model()
    chart_per_case_type_heatmap()
    chart_category_exact_match()
    chart_latency()
    print("\nDone.")


if __name__ == "__main__":
    main()
