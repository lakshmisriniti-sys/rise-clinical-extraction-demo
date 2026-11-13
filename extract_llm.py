"""LLM extraction with Gemini, plus LLM-based data augmentation (rewriting notes in a messier style)."""

import json
import os
import re
import time

from dotenv import load_dotenv

from make_notes import ALLERGIES, DIAGNOSES, MEDICATIONS

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
CALL_DELAY = float(os.getenv("CALL_DELAY", "6"))

SCHEMA_TEXT = """Return JSON only, in exactly this shape:
{"age": int, "sex": "F" or "M", "diagnoses": [string], "medications": [{"name": string, "dose": string}],
 "allergies": [string], "smoking": "never" or "former" or "current"}"""

PLAIN = "Extract the patient's information from this clinical note.\n" + SCHEMA_TEXT

GUIDED = PLAIN + f"""

Rules:
- Only include the PATIENT's CURRENT diagnoses. Exclude anything negated ("no history of", "denies", "no known")
  and anything about family members.
- Only include medicines the patient is CURRENTLY taking. Exclude stopped or discontinued medicines.
- Use these exact diagnosis names: {", ".join(DIAGNOSES)}.
- Use these exact medicine names: {", ".join(MEDICATIONS)}. Write doses like "500 mg" or "100 mcg".
- Use these exact allergy names: {", ".join(ALLERGIES)}. Use [] if there are no known allergies."""

AUGMENT = """Rewrite this clinical note as a hurried doctor would type it: heavy abbreviations, shorthand,
different sentence order, a typo or two. Keep EVERY fact exactly the same: the same conditions, the same
negated conditions, the same family history, the same medicines and doses, the same stopped medicine,
the same allergies, age, sex and smoking status. Do not add new facts. Return only the rewritten note."""

_client = None


def ask(prompt: str, json_mode: bool) -> str:
    global _client
    from google import genai
    from google.genai import types
    if _client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise SystemExit("No GEMINI_API_KEY in .env")
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    config = types.GenerateContentConfig(
        temperature=0.0 if json_mode else 0.7,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    for attempt in range(5):
        try:
            time.sleep(CALL_DELAY)
            return _client.models.generate_content(model=MODEL, contents=prompt, config=config).text or ""
        except Exception as err:
            code = getattr(err, "code", None)
            if code in (400, 401, 403, 404) or "per day" in str(err):
                raise SystemExit(f"Gemini error {code}: {str(err)[:300]}")
            wait = 30 * (attempt + 1)
            print(f"   API error ({str(err)[:70]}...). Waiting {wait}s.")
            time.sleep(wait)
    raise RuntimeError("Gemini kept failing.")


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def extract(text: str, mode: str) -> dict:
    instructions = GUIDED if mode == "guided" else PLAIN
    return parse_json(ask(f"{instructions}\n\nNote:\n{text}", json_mode=True))


def augment(text: str) -> str:
    return ask(f"{AUGMENT}\n\nNote:\n{text}", json_mode=False).strip()


def facts_preserved(original: dict, new_text: str) -> list:
    """Cheap check that the rewrite still contains each medicine's dose number.
    Returns a list of problems (empty list = looks fine)."""
    low = new_text.lower()
    problems = []
    for m in original["truth"]["medications"]:
        number = m["dose"].split()[0]
        if number not in low:
            problems.append(f"dose {m['dose']} of {m['name']} missing")
    if str(original["truth"]["age"]) not in low:
        problems.append("age missing")
    return problems
