"""Offline test with a fake model (no API key needed). Writes its cache to results/test_run/."""
import json
import os

import extract_llm
import extract_rules
import run

NOTES = {n["text"]: n for n in json.load(open("data/notes.json", encoding="utf-8"))}


def fake_extract(text, mode):
    if mode == "guided" and text in NOTES:
        return NOTES[text]["truth"]  # pretend the guided LLM is perfect on clean notes
    return extract_rules.extract(text)  # otherwise behave like the keyword rules


extract_llm.extract = fake_extract
extract_llm.augment = lambda t: t.replace("Current meds", "Meds").replace("once daily", "OD")
os.makedirs("results/test_run", exist_ok=True)
run.CACHE = "results/test_run/cache.json"
if os.path.exists(run.CACHE):
    os.remove(run.CACHE)
run.main()
