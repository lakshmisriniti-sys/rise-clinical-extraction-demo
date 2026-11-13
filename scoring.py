"""Compares an extraction with the ground truth and counts what was right and wrong."""

LIST_FIELDS = ["diagnoses", "medications", "allergies"]
SINGLE_FIELDS = ["age", "sex", "smoking"]


def _norm_dose(d):
    return (d or "").lower().replace(" ", "")


def compare(pred: dict, truth: dict, traps: dict) -> dict:
    """Returns true positives / false positives / false negatives per list field,
    correctness of single fields, dose correctness, and which traps fooled the method."""
    out = {}
    for field in LIST_FIELDS:
        if field == "medications":
            p = {m["name"].lower() for m in pred.get(field) or []}
            t = {m["name"].lower() for m in truth[field]}
        else:
            p = {x.lower() for x in pred.get(field) or []}
            t = {x.lower() for x in truth[field]}
        out[field] = {"tp": len(p & t), "fp": len(p - t), "fn": len(t - p),
                      "wrong_extra": sorted(p - t), "missed": sorted(t - p)}

    for field in SINGLE_FIELDS:
        out[field] = {"correct": str(pred.get(field)).lower() == str(truth[field]).lower()}

    pred_doses = {m["name"].lower(): _norm_dose(m.get("dose")) for m in pred.get("medications") or []}
    found = [m for m in truth["medications"] if m["name"].lower() in pred_doses]
    out["dose_correct"] = sum(1 for m in found if pred_doses[m["name"].lower()] == _norm_dose(m["dose"]))
    out["dose_total"] = len(found)

    p_dx = {x.lower() for x in pred.get("diagnoses") or []}
    p_med = {m["name"].lower() for m in pred.get("medications") or []}
    out["fooled_by"] = {
        "negation": any(x.lower() in p_dx for x in traps["negated"]),
        "family history": any(x.lower() in p_dx for x in traps["family"]),
        "stopped medicine": any(x.lower() in p_med for x in traps["stopped"]),
    }
    return out


def f1_table(results: list) -> dict:
    """Micro precision/recall/F1 for list fields and accuracy for single fields over many notes."""
    table = {}
    for field in LIST_FIELDS:
        tp = sum(r[field]["tp"] for r in results)
        fp = sum(r[field]["fp"] for r in results)
        fn = sum(r[field]["fn"] for r in results)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        table[field] = {"precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0}
    for field in SINGLE_FIELDS:
        table[field] = {"accuracy": sum(r[field]["correct"] for r in results) / len(results)}
    total = sum(r["dose_total"] for r in results)
    table["dose"] = {"accuracy": sum(r["dose_correct"] for r in results) / total if total else 0.0}
    for trap in ["negation", "family history", "stopped medicine"]:
        table[f"fooled: {trap}"] = {"rate": sum(r["fooled_by"][trap] for r in results) / len(results)}
    return table
