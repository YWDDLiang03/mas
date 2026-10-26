"""Build the English result figure from the published final study.

Run from any directory with Python and matplotlib installed:
    python docs/figures/current/draw_results.py
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path as MPath

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
CASE = ROOT / "examples/oral-multitarget/latest"
BLUE = "#316B9B"
BLUE_LIGHT = "#EAF2F8"
TEAL = "#6A9FA5"
AMBER = "#C89D5A"
INK = "#202A33"
MUTED = "#65717C"
LINE = "#B9C3CC"
PALE = "#F4F6F8"
GRAY = "#C7D0D7"
RED = "#AE5260"

FONT = "Arial" if any(f.name == "Arial" for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({
    "font.family": FONT, "font.size": 7.5, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK,
    "axes.edgecolor": LINE, "axes.linewidth": 0.65,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "svg.hashsalt": "mas-nature-inspired-2026-10-21",
    "savefig.facecolor": "white", "figure.facecolor": "white",
})
TEXT = []


def canvas(height):
    fig = plt.figure(figsize=(180 / 25.4, height / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 180), ylim=(0, height))
    ax.set_axis_off()
    return fig, ax


def text(ax, x, y, label, *, size=7.5, weight="normal", color=INK, ha="left",
         va="center", **kwargs):
    t = ax.text(x, y, label, fontsize=size, weight=weight, color=color, ha=ha,
                va=va, linespacing=1.4, **kwargs)
    TEXT.append(t)
    return t


def panel(ax, x, y, letter, title):
    text(ax, x, y, letter, size=10, weight="bold")
    text(ax, x + 5, y, title, size=8.1, weight="bold")


def box(ax, x, y, w, h, *, fill="white", edge=LINE, radius=1.0, lw=0.75):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor=fill, edgecolor=edge, linewidth=lw)
    ax.add_patch(p)
    return p


def line(ax, points, *, color=LINE, lw=0.8, dashed=False):
    ax.plot(*zip(*points), color=color, linewidth=lw,
            linestyle=(0, (2.4, 2.4)) if dashed else "-", solid_capstyle="round")


def arrow(ax, points, *, color=MUTED, lw=0.85, dashed=False):
    if len(points) == 2:
        p = FancyArrowPatch(points[0], points[1], arrowstyle="-|>",
                            mutation_scale=7, linewidth=lw, color=color,
                            shrinkA=0, shrinkB=0)
    else:
        path = MPath(points, [MPath.MOVETO] + [MPath.LINETO] * (len(points) - 1))
        p = FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=7,
                            linewidth=lw, color=color)
    if dashed:
        p.set_linestyle((0, (2.4, 2.4)))
    ax.add_patch(p)


def circle(ax, x, y, radius, fill=BLUE, edge=None, lw=0.6):
    ax.add_patch(Circle((x, y), radius, facecolor=fill,
                        edgecolor=edge or fill, linewidth=lw))


def save(fig, stem):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    outside = []
    for item in TEXT:
        if item.figure is not fig or not item.get_visible():
            continue
        b = item.get_window_extent(renderer)
        if b.x0 < bounds.x0 - 1 or b.y0 < bounds.y0 - 1 or b.x1 > bounds.x1 + 1 or b.y1 > bounds.y1 + 1:
            outside.append(item.get_text())
    if outside:
        raise ValueError(f"Text outside {stem}: {outside}")
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    fig.savefig(OUT / f"{stem}.pdf", metadata={"Title": stem.replace("_", " "), "Creator": "MAS figure script"})
    fig.savefig(OUT / f"{stem}.svg")
    svg = OUT / f"{stem}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    from editable_plot import export_pptx
    captions=json.loads((OUT/'captions.json').read_text(encoding='utf-8'))
    export_pptx(fig, OUT/'Surufatinib_results_editable.pptx', captions['figure_2_surufatinib_results'])
    plt.close(fig)


def read_data():
    with (CASE / "results/candidates.csv").open(encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle))
    with (CASE / "score-details.csv").open(encoding="utf-8-sig", newline="") as handle:
        details = list(csv.DictReader(handle))
    summary = json.loads((CASE / "score-details.json").read_text(encoding="utf-8"))
    reference = json.loads((CASE / "results/surufatinib.json").read_text(encoding="utf-8"))["matches"][0]
    counts = Counter(row["qualification"] for row in candidates)
    ranked = sorted((row for row in candidates if row["position"]), key=lambda r: int(r["position"]))
    assert len(candidates) == 3177 and counts == {"qualified": 10, "pending": 3167}
    assert ranked[0]["label"] == "Surufatinib" and len(ranked) == 10
    assert reference["qualification_record"]["hard_passed"] == 1
    assert reference["qualification_record"]["required_direct_answered"] == 5
    assert len(details) == 17
    kinds = Counter(row["证据类型"] for row in details)
    assert kinds == {"实测或整理测量": 5, "确定性结构计算": 5, "训练模型预测": 5, "缺证": 2}
    assert summary["score_denominator"] == 15 and summary["direct_coverage_numerator"] == 10
    targets = {}
    for target in ("CSF1R", "VEGFR1", "VEGFR2", "VEGFR3", "FGFR1"):
        row = next(r for r in details if r["偏好原名"] == target + " curated potency")
        assert row["单位"] == "pChEMBL"
        targets[target] = float(row["实际汇总值"])
    return candidates, ranked, targets, summary, reference, details


def result_figure(ranked, targets, summary):
    fig, ax = canvas(136)
    text(ax, 6, 129.5, "Surufatinib ranks first among eligible candidates", size=11.7, weight="bold")
    text(ax, 6, 123.5, "Oral multi-target prioritization  |  Recorded final evaluation", size=7.5, color=MUTED)
    line(ax, [(6, 119), (174, 119)], lw=0.65)
    panel(ax, 6, 113.5, "a", "Candidate selection")
    text(ax, 174, 113.5, "18 enabled decision rules: 1 condition + 17 prioritization criteria",
         size=6.1, color=MUTED, ha="right")

    box(ax, 6, 90, 36, 17, fill=PALE)
    text(ax, 24, 101.6, "3,177", size=15, weight="bold", ha="center")
    text(ax, 24, 94, "Candidates assessed", size=7.1, ha="center", color=MUTED)
    arrow(ax, [(42, 98.5), (53, 98.5)])
    box(ax, 53, 90, 62, 17)
    text(ax, 84, 101.6, "Eligibility requirements (6)", size=6.9, weight="bold", ha="center")
    text(ax, 84, 95.4, "All required: 1 oral condition + 5 target observations", size=6.0, color=MUTED, ha="center")
    arrow(ax, [(115, 98.5), (126, 98.5)], color=BLUE)
    box(ax, 126, 90, 48, 17, fill=BLUE_LIGHT, edge="#90B2CC")
    text(ax, 150, 101.6, "10", size=15, weight="bold", ha="center", color=BLUE)
    text(ax, 150, 94, "Eligible for prioritization", size=7.1, ha="center", color=BLUE)
    line(ax, [(84,90),(84,88),(31,88)],lw=.7)
    line(ax, [(84,88),(90,88)],lw=.7)
    arrow(ax, [(31,88),(31,86)],lw=.7,color=AMBER)
    arrow(ax, [(90,88),(90,86)],lw=.7,color=RED)
    box(ax,6,75.5,50,10.5,fill="#FCF5E8",edge="#C7A86B",radius=1)
    text(ax,31,82.7,"Evidence incomplete (1,305)",size=6.7,weight='bold',ha='center',color="#956C29")
    text(ax,31,78.4,"Partial support; no condition failed",size=5.8,ha='center',color=MUTED)
    box(ax,65,75.5,50,10.5,fill="#FBEFF0",edge=RED,radius=1)
    text(ax,90,82.7,"Excluded (1,862)",size=6.7,weight='bold',ha='center',color=RED)
    text(ax,90,78.4,"No admission support",size=6.1,ha='center',color=MUTED)
    text(ax, 126, 81, "5 target criteria serve\nadmission and ranking", size=6.6, color=MUTED)

    panel(ax, 6, 68.5, "b", "Eligible-candidate ranking")
    panel(ax, 111, 68.5, "c", "Surufatinib evidence")
    # The score scale starts at zero and is not a probability or an uncertainty interval.
    plot = fig.add_axes([41 / 180, 15 / 136, 61 / 180, 47 / 136])
    values = [float(row["score"]) for row in ranked]
    y = list(range(len(ranked)))
    plot.barh(y, values, height=0.62, color=[BLUE] + [GRAY] * 9, linewidth=0, zorder=2)
    plot.set(xlim=(0, 1.04), ylim=(9.7, -0.8))
    plot.set_xticks([0, .25, .5, .75, 1], ["0", "0.25", "0.50", "0.75", "1.00"])
    plot.set_yticks(y, [r["label"] for r in ranked], fontsize=7.3)
    plot.tick_params(axis="y", length=0, pad=6)
    plot.tick_params(axis="x", length=2.4, labelsize=6.4, pad=3)
    plot.grid(axis="x", color="#E7EBEF", lw=0.55, zorder=0)
    for side in ("top", "right", "left"):
        plot.spines[side].set_visible(False)
    plot.spines["bottom"].set_color(LINE)
    for idx, label in enumerate(plot.get_yticklabels()):
        if idx == 0:
            label.set_color(BLUE)
            label.set_weight("bold")
    for i, value in enumerate(values):
        plot.text(value + .02, i, f"{value:.3f}", fontsize=6.8,
                  va="center", color=BLUE if i == 0 else MUTED,
                  weight="bold" if i == 0 else "normal")
    plot.set_xlabel("Prioritization score", fontsize=7.1, labelpad=5)

    text(ax, 111, 60.5, "Required condition: oral", size=7.2)
    text(ax, 174, 60.5, "Met  1/1", size=7.3, color=BLUE, weight="bold", ha="right")
    line(ax, [(111, 56.7), (174, 56.7)], color="#DEE5EB", lw=0.6)
    text(ax, 111, 52.5, "Required target evidence", size=7.0)
    text(ax, 174, 52.5, "Available 5/5", size=6.8, color=BLUE, weight="bold", ha="right")
    for i, (target, value) in enumerate(targets.items()):
        x = 116.5 + 13 * i
        circle(ax, x, 44.6, 2.3, fill=BLUE_LIGHT, edge="#90B2CC")
        circle(ax, x, 44.6, .7, fill=BLUE)
        text(ax, x, 38.7, target, size=6.5, ha="center", weight="bold")
        text(ax, x, 34.3, f"{value:.2f}", size=7, ha="center", color=BLUE)
    text(ax, 111, 29, "Recorded potency aggregates (pChEMBL)", size=6.4, color=MUTED)
    line(ax, [(111, 25.5), (174, 25.5)], color="#DEE5EB", lw=0.6)
    text(ax, 111, 21.5, "Scoring evidence", size=7.2, weight="bold")
    text(ax, 174, 21.5, "10/17 direct coverage", size=6.8, ha="right", color=BLUE)
    for i, color in enumerate([BLUE] * 5 + [TEAL] * 5 + [AMBER] * 5 + ["white"] * 2):
        ax.add_patch(Rectangle((111 + i * 3.72, 14.8), 3.18, 3.7,
                               facecolor=color, edgecolor=MUTED if color == "white" else color,
                               linewidth=0.55))
    legends = [(111, 11.0, BLUE, "Measured / curated (5)"), (145, 11.0, TEAL, "Derived (5)"),
               (111, 6.5, AMBER, "Predicted (5)"), (145, 6.5, "white", "Missing (2)")]
    for x, y, color, label in legends:
        ax.add_patch(Rectangle((x, y - .9), 2, 1.8, facecolor=color,
                               edgecolor=MUTED if color == "white" else color, lw=.55))
        text(ax, x + 3.2, y, label, size=6.3, color=MUTED)
    text(ax, 6, 3.6, "Equal weights; 15 usable scores. Direct coverage: 58.8%; ranking minimum: 50%.", size=6.2, color=MUTED)
    save(fig, "figure_2_surufatinib_results")


def source_data(candidates, ranked, targets, summary, reference, details):
    files = ["results/candidates.csv", "results/surufatinib.json", "score-details.csv", "score-details.json"]
    value = {
        "study_task_id": summary["task_id"], "run_id": summary["run_id"],
        "snapshot_id": summary["snapshot_id"], "rule_set": summary["rule_set_ref"],
        "candidate_count": len(candidates),
        "recorded_qualification": dict(Counter(row["qualification"] for row in candidates)),
        "selection_reporting_v3": json.loads((CASE/'selection/selection-audit.json').read_text(encoding='utf-8'))['selection_counts'],
        "ranked_candidates": [{"name": r["label"], "rank": int(r["position"]), "score": float(r["score"])} for r in ranked],
        "surufatinib": {"qualification": reference["qualification_record"],
                       "target_potency_pchembl": targets,
                       "score": summary["source_score"], "scored_preference_count": 15,
                       "direct_coverage_numerator": 10, "direct_coverage_denominator": 17,
                       "preference_basis_counts": {"measured": 5, "structure_derived": 5, "predicted": 5, "missing": 2}},
        "source_files": {str((CASE / name).relative_to(ROOT)).replace("\\", "/"):
                         hashlib.sha256((CASE / name).read_bytes()).hexdigest() for name in files},
        "figure_1_is_schematic": True, "new_model_calls": 0, "new_research_run": False,
        "font": FONT, "png_dpi": 600,
    }
    (OUT / "figure_data.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    data = read_data()
    result_figure(data[1], data[2], data[3])
    source_data(*data)
    print(json.dumps({"output": str(OUT), "figures": 1, "formats": ["png", "pdf", "svg"], "font": FONT, "dpi": 600}))
