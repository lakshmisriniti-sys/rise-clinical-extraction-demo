"""Creates 30 synthetic (fake) clinical notes, each with the correct answer ("ground truth").

No real patient data is used. The notes deliberately include traps that simple
keyword matching gets wrong:
  - negations         ("No history of asthma")
  - family history    ("Mother had heart failure")
  - stopped medicines ("Ramipril was stopped due to cough")
  - abbreviations     (HTN, T2DM, AF, CKD, bd, od)
"""

import json
import random

random.seed(42)

DIAGNOSES = {  # canonical name -> ways a doctor might write it
    "hypertension": ["hypertension", "HTN", "high blood pressure"],
    "type 2 diabetes": ["type 2 diabetes", "T2DM", "type II diabetes mellitus"],
    "asthma": ["asthma"],
    "COPD": ["COPD", "chronic obstructive pulmonary disease"],
    "atrial fibrillation": ["atrial fibrillation", "AF", "AFib"],
    "heart failure": ["heart failure", "HF"],
    "chronic kidney disease": ["chronic kidney disease", "CKD stage 3"],
    "depression": ["depression", "low mood (diagnosed depression)"],
    "hypothyroidism": ["hypothyroidism", "underactive thyroid"],
    "osteoarthritis": ["osteoarthritis", "OA of the knees"],
}

MEDICATIONS = {  # name -> typical doses
    "metformin": ["500 mg", "1000 mg"],
    "amlodipine": ["5 mg", "10 mg"],
    "ramipril": ["2.5 mg", "5 mg"],
    "atorvastatin": ["20 mg", "40 mg"],
    "salbutamol": ["100 mcg"],
    "levothyroxine": ["50 mcg", "100 mcg"],
    "sertraline": ["50 mg", "100 mg"],
    "apixaban": ["5 mg"],
    "bisoprolol": ["2.5 mg", "5 mg"],
    "furosemide": ["40 mg"],
    "omeprazole": ["20 mg"],
}

ALLERGIES = {"penicillin": "penicillin", "latex": "latex", "NSAIDs": "NSAIDs", "codeine": "codeine"}
FREQ = ["once daily", "od", "twice daily", "bd", "at night"]


def make_note(i: int) -> dict:
    age = random.randint(28, 89)
    female = random.random() < 0.5
    sex = "F" if female else "M"
    pron = "She" if female else "He"

    dx = random.sample(list(DIAGNOSES), random.randint(1, 3))
    others = [d for d in DIAGNOSES if d not in dx]
    negated = random.sample(others, 1)
    family = random.sample([d for d in others if d not in negated], 1)

    meds = random.sample(list(MEDICATIONS), random.randint(1, 3))
    stopped = random.choice([m for m in MEDICATIONS if m not in meds])
    doses = {m: random.choice(MEDICATIONS[m]) for m in meds}

    allergy = random.sample(list(ALLERGIES), random.choice([0, 0, 1, 1, 2]))
    smoking = random.choice(["never", "former", "current"])

    # --- write the note text in varied styles ---
    style = i % 3
    if style == 0:
        opening = f"{age}-year-old {'woman' if female else 'man'} reviewed in clinic today."
    elif style == 1:
        opening = f"Pt is a {age}yo {sex}, seen for routine follow-up."
    else:
        opening = f"Review of {'Mrs' if female else 'Mr'} X, aged {age}."

    pmh = ", ".join(random.choice(DIAGNOSES[d]) for d in dx)
    neg_text = random.choice(["No history of", "Denies", "No known"]) + " " + random.choice(DIAGNOSES[negated[0]]) + "."
    fam_text = f"{random.choice(['Mother', 'Father', 'Brother'])} had {random.choice(DIAGNOSES[family[0]])}."

    med_bits = [f"{m} {doses[m].replace(' ', '') if style == 1 else doses[m]} {random.choice(FREQ)}" for m in meds]
    if style == 0:
        med_text = f"{pron} takes " + "; ".join(med_bits) + "."
    else:
        med_text = "Current meds: " + ", ".join(med_bits) + "."
    stop_text = f"{stopped.capitalize()} was stopped last year due to side effects."

    if allergy:
        allergy_text = "Allergies: " + ", ".join(ALLERGIES[a] for a in allergy) + " (rash)."
    else:
        allergy_text = random.choice(["NKDA.", "No known drug allergies."])

    smoke_text = {
        "never": random.choice(["Never smoked.", "Non-smoker, never smoked."]),
        "former": random.choice(["Ex-smoker, quit in 2015.", "Stopped smoking 10 years ago."]),
        "current": random.choice(["Smokes 10 cigarettes a day.", "Current smoker."]),
    }[smoking]

    parts = [opening, f"PMH: {pmh}.", neg_text, med_text, stop_text, allergy_text, smoke_text, fam_text,
             "BP stable today. Plan: continue current treatment and review in 3 months."]
    text = " ".join(parts)

    truth = {
        "age": age,
        "sex": sex,
        "diagnoses": sorted(dx),
        "medications": sorted([{"name": m, "dose": doses[m]} for m in meds], key=lambda x: x["name"]),
        "allergies": sorted(allergy),
        "smoking": smoking,
    }
    traps = {"negated": negated, "family": family, "stopped": [stopped]}
    return {"id": f"N{i + 1:02d}", "text": text, "truth": truth, "traps": traps}


if __name__ == "__main__":
    notes = [make_note(i) for i in range(30)]
    with open("data/notes.json", "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)
    print(f"Wrote {len(notes)} notes to data/notes.json\n\nExample:\n{notes[0]['text']}\n")
    print(json.dumps(notes[0]["truth"], indent=2))
