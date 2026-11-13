"""Baseline: simple keyword and pattern matching, no AI.

This is what a quick script would do. It finds words, but it cannot understand
context, so it is expected to fall for negations, family history and stopped medicines.
"""

import re

from make_notes import ALLERGIES, DIAGNOSES, MEDICATIONS


def extract(text: str) -> dict:
    low = text.lower()

    age = re.search(r"(\d{2})[- ]?(?:year-old|yo)|aged (\d{2})", low)
    age = int(age.group(1) or age.group(2)) if age else None

    if re.search(r"\b(woman|she|mrs|f)\b", low):
        sex = "F"
    elif re.search(r"\b(man|he|mr|m)\b", low):
        sex = "M"
    else:
        sex = None

    diagnoses = sorted({name for name, variants in DIAGNOSES.items()
                        if any(re.search(r"\b" + re.escape(v.lower()) + r"\b", low) for v in variants)})

    medications = []
    for name in MEDICATIONS:
        m = re.search(name + r"\s+(\d+(?:\.\d+)?)\s?(mg|mcg)", low)
        if m:
            medications.append({"name": name, "dose": f"{m.group(1)} {m.group(2)}"})
        elif name in low:
            medications.append({"name": name, "dose": None})

    allergies = sorted(a for a in ALLERGIES if a.lower() in low)

    if "ex-smoker" in low or "stopped smoking" in low:
        smoking = "former"
    elif "never smoked" in low or "non-smoker" in low:
        smoking = "never"
    elif "smoke" in low:
        smoking = "current"
    else:
        smoking = None

    return {"age": age, "sex": sex, "diagnoses": diagnoses, "medications": medications,
            "allergies": allergies, "smoking": smoking}
