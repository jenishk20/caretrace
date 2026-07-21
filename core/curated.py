"""Curated clinical knowledge — the code-owned source of truth.

Confide's reliability rule: gpt-oss never decides pharmacology from memory. It only
extracts drug/allergy/symptom mentions and tags each with a normalized CATEGORY
from the controlled vocabulary below. Every clinical judgment — does this drug
conflict with an allergy, does it interact with another drug, when is a lab due —
is a deterministic lookup in these tables. Small, curated, auditable, and it fires
the same way every time. A real deployment swaps this for RxNorm / DrugBank.
"""
from __future__ import annotations

# --- Controlled vocabulary of categories -------------------------------------
# Gemma is told to tag every extracted drug/allergy/statement with one of these.
DRUG_CATEGORIES = [
    "anticoagulant",       # warfarin, heparin, apixaban, ...
    "nsaid",               # ibuprofen, ketorolac, aspirin, naproxen
    "penicillin_class",    # penicillin, amoxicillin, ampicillin
    "cephalosporin",       # cefazolin, ceftriaxone (cross-reacts with penicillin)
    "sulfonamide",         # sulfamethoxazole
    "opioid",              # morphine, oxycodone, fentanyl
    "ace_inhibitor",       # lisinopril, enalapril
    "beta_blocker",        # metoprolol, atenolol
    "statin",              # atorvastatin, simvastatin
    "benzodiazepine",      # lorazepam, diazepam
    "antibiotic_other",    # azithromycin, ciprofloxacin
    "other_drug",
]

# Map a specific drug name (lowercased) -> its category. Belt-and-suspenders on
# top of Gemma's own tagging: if the model tags loosely, we normalize by name.
DRUG_TO_CATEGORY = {
    "warfarin": "anticoagulant",
    "coumadin": "anticoagulant",
    "heparin": "anticoagulant",
    "enoxaparin": "anticoagulant",
    "lovenox": "anticoagulant",
    "apixaban": "anticoagulant",
    "eliquis": "anticoagulant",
    "rivaroxaban": "anticoagulant",
    "xarelto": "anticoagulant",
    "aspirin": "nsaid",
    "ibuprofen": "nsaid",
    "motrin": "nsaid",
    "advil": "nsaid",
    "naproxen": "nsaid",
    "ketorolac": "nsaid",
    "toradol": "nsaid",
    "penicillin": "penicillin_class",
    "amoxicillin": "penicillin_class",
    "ampicillin": "penicillin_class",
    "augmentin": "penicillin_class",
    "piperacillin": "penicillin_class",
    "cefazolin": "cephalosporin",
    "ceftriaxone": "cephalosporin",
    "cephalexin": "cephalosporin",
    "keflex": "cephalosporin",
    "sulfamethoxazole": "sulfonamide",
    "bactrim": "sulfonamide",
    "morphine": "opioid",
    "oxycodone": "opioid",
    "fentanyl": "opioid",
    "hydromorphone": "opioid",
    "dilaudid": "opioid",
    "lisinopril": "ace_inhibitor",
    "enalapril": "ace_inhibitor",
    "metoprolol": "beta_blocker",
    "atenolol": "beta_blocker",
    "atorvastatin": "statin",
    "lipitor": "statin",
    "simvastatin": "statin",
    "lorazepam": "benzodiazepine",
    "ativan": "benzodiazepine",
    "diazepam": "benzodiazepine",
    "azithromycin": "antibiotic_other",
    "ciprofloxacin": "antibiotic_other",
    "levofloxacin": "antibiotic_other",
}

# Allergy category -> drug categories it conflicts with (incl. cross-reactivity).
ALLERGY_CONFLICTS = {
    "penicillin_class": ["penicillin_class", "cephalosporin"],
    "cephalosporin": ["cephalosporin", "penicillin_class"],
    "sulfonamide": ["sulfonamide"],
    "nsaid": ["nsaid"],
    "opioid": ["opioid"],
    "anticoagulant": ["anticoagulant"],
}

# Drug-drug interactions: unordered pairs of categories -> (severity, why).
INTERACTIONS = {
    frozenset(["anticoagulant", "nsaid"]): (
        "critical",
        "Combining an anticoagulant with an NSAID sharply raises the risk of serious bleeding.",
    ),
    frozenset(["anticoagulant", "antibiotic_other"]): (
        "warning",
        "Some antibiotics potentiate anticoagulants and can raise INR — monitor closely.",
    ),
    frozenset(["opioid", "benzodiazepine"]): (
        "critical",
        "Opioids plus benzodiazepines cause additive respiratory depression and sedation.",
    ),
    frozenset(["ace_inhibitor", "nsaid"]): (
        "warning",
        "NSAIDs blunt ACE inhibitors and together can impair kidney function.",
    ),
}

# How long until an ordered item should be rechecked (hours). Drives the
# forgotten-order Guardian. Real windows; the demo scales them via DEMO_TIME_SCALE.
RECHECK_WINDOWS_HOURS = {
    "labs": 4.0,
    "troponin": 3.0,
    "vitals": 1.0,
    "reassess": 2.0,
    "imaging": 6.0,
    "default": 4.0,
}

# Words that, appearing in an order label, imply a recheck category.
ORDER_KEYWORDS = {
    "troponin": "troponin",
    "lab": "labs",
    "cbc": "labs",
    "bmp": "labs",
    "metabolic": "labs",
    "electrolyte": "labs",
    "vital": "vitals",
    "blood pressure": "vitals",
    "reassess": "reassess",
    "recheck": "labs",
    "x-ray": "imaging",
    "ct": "imaging",
    "imaging": "imaging",
    "scan": "imaging",
}

# Minimal demonstration set. A production deployment swaps this for licensed,
# versioned ICD-10-CM and CPT data while keeping the same validation boundary.
ICD10 = {
    "atrial fibrillation": ("I48.91", "Atrial fibrillation, unspecified"),
    "chest pain": ("R07.9", "Chest pain, unspecified"),
    "penicillin allergy": ("Z88.0", "Allergy status to penicillin"),
    "essential hypertension": ("I10", "Essential (primary) hypertension"),
    "shortness of breath": ("R06.02", "Shortness of breath"),
    "nausea": ("R11.0", "Nausea"),
    "fever": ("R50.9", "Fever, unspecified"),
    "type 2 diabetes": ("E11.9", "Type 2 diabetes mellitus without complications"),
    "hyperlipidemia": ("E78.5", "Hyperlipidemia, unspecified"),
    "acute kidney injury": ("N17.9", "Acute kidney failure, unspecified"),
    "anemia": ("D64.9", "Anemia, unspecified"),
    "anticoagulant use": ("Z79.01", "Long term use of anticoagulants"),
}

EM_LEVELS = {
    "low": ("99231", "Subsequent hospital care, low complexity"),
    "moderate": ("99232", "Subsequent hospital care, moderate complexity"),
    "high": ("99233", "Subsequent hospital care, high complexity"),
}


def category_for_drug(name: str, fallback: str | None = None) -> str | None:
    """Normalize a drug name to a category, preferring the curated map."""
    if not name:
        return fallback
    key = name.strip().lower()
    # exact
    if key in DRUG_TO_CATEGORY:
        return DRUG_TO_CATEGORY[key]
    # token contains a known drug ("started warfarin" -> warfarin)
    for drug, cat in DRUG_TO_CATEGORY.items():
        if drug in key:
            return cat
    return fallback


def recheck_hours_for_order(label: str) -> float:
    low = (label or "").lower()
    for kw, cat in ORDER_KEYWORDS.items():
        if kw in low:
            return RECHECK_WINDOWS_HOURS.get(cat, RECHECK_WINDOWS_HOURS["default"])
    return RECHECK_WINDOWS_HOURS["default"]


def allergy_conflict(allergy_category: str, drug_category: str) -> bool:
    return drug_category in ALLERGY_CONFLICTS.get(allergy_category, [])


def interaction_between(cat_a: str, cat_b: str) -> tuple[str, str] | None:
    return INTERACTIONS.get(frozenset([cat_a, cat_b]))


def code_for_term(term: str) -> dict | None:
    entry = ICD10.get((term or "").strip().lower())
    if not entry:
        return None
    return {"code": entry[0], "system": "ICD-10", "label": entry[1]}


def code_details(system: str, code: str) -> dict | None:
    normalized_system = (system or "").strip().upper()
    tables = []
    if normalized_system in ("ICD-10", "ICD10", "ICD-10-CM"):
        tables = [("ICD-10", ICD10)]
    elif normalized_system == "CPT":
        tables = [("CPT", EM_LEVELS)]
    for canonical_system, table in tables:
        for stored_code, label in table.values():
            if stored_code == code:
                return {"code": stored_code, "system": canonical_system, "label": label}
    return None


def validate_code(system: str, code: str) -> bool:
    return code_details(system, code) is not None
