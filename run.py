"""Runs the whole experiment. Saves every LLM output, so re-running continues where it stopped.

Methods compared on 30 synthetic notes:
  rules        keyword matching (no AI)
  llm_plain    Gemini, simple instruction
  llm_guided   Gemini, with rules about negation / family history / stopped medicines and fixed vocabularies

Augmentation test: Gemini rewrites 10 notes in a messy shorthand style (same facts),
then rules and llm_guided are run again on the messy versions.
"""

import json
import os

import extract_llm
import extract_rules
from scoring import compare, f1_table

CACHE = "results/llm_outputs.json"
N_AUGMENT = 10


def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def cached(cache, key, fn):
    if key not in cache:
        print(f"  {key}")
        cache[key] = fn()
        save_cache(cache)
    return cache[key]


def main():
    os.makedirs("results", exist_ok=True)
    with open("data/notes.json", encoding="utf-8") as f:
        notes = json.load(f)
    cache = load_cache()
    print(f"Model: {extract_llm.MODEL}")

    per_note = []  # one row per (note, dataset, method)
    for n in notes:
        for method in ["rules", "llm_plain", "llm_guided"]:
            if method == "rules":
                pred = extract_rules.extract(n["text"])
            else:
                mode = method.split("_")[1]
                pred = cached(cache, f"{n['id']}|clean|{method}", lambda: extract_llm.extract(n["text"], mode))
            per_note.append({"id": n["id"], "dataset": "clean", "method": method, "pred": pred,
                             "score": compare(pred, n["truth"], n["traps"])})

    augmented = []
    for n in notes[:N_AUGMENT]:
        messy = cached(cache, f"{n['id']}|augment", lambda: extract_llm.augment(n["text"]))
        problems = extract_llm.facts_preserved(n, messy)
        augmented.append({"id": n["id"], "text": messy, "problems": problems})
        if problems:
            continue  # the rewrite changed a fact, so its "truth" is no longer reliable
        for method in ["rules", "llm_guided"]:
            if method == "rules":
                pred = extract_rules.extract(messy)
            else:
                pred = cached(cache, f"{n['id']}|messy|{method}", lambda: extract_llm.extract(messy, "guided"))
            per_note.append({"id": n["id"], "dataset": "messy", "method": method, "pred": pred,
                             "score": compare(pred, n["truth"], n["traps"])})

    summary = {}
    for dataset in ["clean", "messy"]:
        for method in ["rules", "llm_plain", "llm_guided"]:
            rows = [r["score"] for r in per_note if r["dataset"] == dataset and r["method"] == method]
            if rows:
                summary[f"{dataset}|{method}"] = {"n_notes": len(rows), **f1_table(rows)}

    with open("results/per_note.json", "w", encoding="utf-8") as f:
        json.dump(per_note, f, indent=2)
    with open("results/augmented_notes.json", "w", encoding="utf-8") as f:
        json.dump(augmented, f, indent=2)
    with open("results/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nF1 (diagnoses / medications / allergies) and trap rates:")
    for key, s in summary.items():
        print(f"  {key:18s} n={s['n_notes']:2d}  dx {s['diagnoses']['f1']:.2f}  med {s['medications']['f1']:.2f}  "
              f"allergy {s['allergies']['f1']:.2f}  dose {s['dose']['accuracy']:.2f}  "
              f"fooled neg/fam/stop {s['fooled: negation']['rate']:.2f}/"
              f"{s['fooled: family history']['rate']:.2f}/{s['fooled: stopped medicine']['rate']:.2f}")
    bad = [a for a in augmented if a["problems"]]
    print(f"\nAugmentation: {len(bad)}/{len(augmented)} rewrites changed a fact and were excluded.")
    print("Now run: python visualise.py")


if __name__ == "__main__":
    main()
