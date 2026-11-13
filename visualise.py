"""Makes results/chart.png (for the README) and results/dashboard.html (interactive, open in a browser)."""

import json

import matplotlib.pyplot as plt
import plotly.graph_objects as go

with open("results/summary.json", encoding="utf-8") as f:
    summary = json.load(f)
with open("results/per_note.json", encoding="utf-8") as f:
    per_note = json.load(f)

METHODS = ["rules", "llm_plain", "llm_guided"]
NAMES = {"rules": "Keyword rules", "llm_plain": "LLM, plain prompt", "llm_guided": "LLM, guided prompt"}
COLORS = {"rules": "#9aa5b1", "llm_plain": "#5b8def", "llm_guided": "#1f9d74"}
FIELDS = ["diagnoses", "medications", "allergies"]
TRAPS = ["negation", "family history", "stopped medicine"]

# ---------- static chart for the README ----------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
w = 0.26
for i, m in enumerate(METHODS):
    s = summary[f"clean|{m}"]
    axes[0].bar([x + (i - 1) * w for x in range(3)], [s[f]["f1"] for f in FIELDS], w, label=NAMES[m], color=COLORS[m])
    axes[1].bar([x + (i - 1) * w for x in range(3)], [100 * s[f"fooled: {t}"]["rate"] for t in TRAPS], w,
                label=NAMES[m], color=COLORS[m])
axes[0].set_xticks(range(3), [f.capitalize() for f in FIELDS])
axes[0].set_ylim(0, 1.05)
axes[0].set_title("Extraction F1 on 30 synthetic notes")
axes[1].set_xticks(range(3), ["Negated condition", "Family history", "Stopped medicine"])
axes[1].set_ylim(0, 105)
axes[1].set_ylabel("% of notes where the trap was extracted")
axes[1].set_title("How often each method fell for a trap")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(rect=(0, 0.08, 1, 1))
plt.savefig("results/chart.png", dpi=150)

# ---------- interactive dashboard ----------
figs = []

f1 = go.Figure()
for m in METHODS:
    s = summary[f"clean|{m}"]
    f1.add_bar(name=NAMES[m], x=[f.capitalize() for f in FIELDS], y=[s[f]["f1"] for f in FIELDS],
               marker_color=COLORS[m], hovertemplate="%{x}: F1 %{y:.2f}<extra>" + NAMES[m] + "</extra>")
f1.update_layout(title="1. Extraction quality (F1) on clean notes", barmode="group", yaxis_range=[0, 1.05])
figs.append(f1)

traps = go.Figure()
for m in METHODS:
    s = summary[f"clean|{m}"]
    traps.add_bar(name=NAMES[m], x=TRAPS, y=[100 * s[f"fooled: {t}"]["rate"] for t in TRAPS], marker_color=COLORS[m])
traps.update_layout(title="2. % of notes where a trap was wrongly extracted", barmode="group",
                    yaxis_range=[0, 105], yaxis_title="%")
figs.append(traps)

if "messy|rules" in summary:
    rob = go.Figure()
    for m in ["rules", "llm_guided"]:
        ys = [summary[f"{d}|{m}"]["medications"]["f1"] for d in ["clean", "messy"]]
        rob.add_bar(name=NAMES[m], x=["Clean notes", f"Messy rewrites (n={summary['messy|rules']['n_notes']})"],
                    y=ys, marker_color=COLORS[m])
    rob.update_layout(title="3. Robustness: medication F1 before and after LLM rewriting (augmentation)",
                      barmode="group", yaxis_range=[0, 1.05])
    figs.append(rob)

# per-note error heatmap with hover details
ids = sorted({r["id"] for r in per_note if r["dataset"] == "clean"})
z, hover = [], []
for m in METHODS:
    row_z, row_h = [], []
    for nid in ids:
        r = next(x for x in per_note if x["id"] == nid and x["method"] == m and x["dataset"] == "clean")
        sc = r["score"]
        errors = sum(sc[f]["fp"] + sc[f]["fn"] for f in FIELDS)
        errors += sum(not sc[f]["correct"] for f in ["age", "sex", "smoking"])
        details = []
        for f in FIELDS:
            if sc[f]["wrong_extra"]:
                details.append(f"{f} wrongly added: {', '.join(sc[f]['wrong_extra'])}")
            if sc[f]["missed"]:
                details.append(f"{f} missed: {', '.join(sc[f]['missed'])}")
        row_z.append(errors)
        row_h.append(f"{nid} - {NAMES[m]}<br>{errors} error(s)<br>" + ("<br>".join(details) or "all correct"))
    z.append(row_z)
    hover.append(row_h)
heat = go.Figure(go.Heatmap(z=z, x=ids, y=[NAMES[m] for m in METHODS], text=hover, hoverinfo="text",
                            colorscale=[[0, "#e8f5ee"], [0.3, "#f6c26b"], [1, "#c0392b"]], colorbar_title="errors"))
heat.update_layout(title="4. Errors per note (hover a cell to see what went wrong)", height=330)
figs.append(heat)

parts = [f.to_html(full_html=False, include_plotlyjs=("cdn" if i == 0 else False)) for i, f in enumerate(figs)]
html = ("<html><head><meta charset='utf-8'><title>LLM clinical extraction results</title></head>"
        "<body style='font-family:sans-serif;max-width:1000px;margin:auto'>"
        "<h1>LLM extraction from synthetic clinical notes</h1>"
        "<p>All notes are synthetic. Hover over the charts for details.</p>" + "".join(parts) + "</body></html>")
with open("results/dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved results/chart.png and results/dashboard.html")
