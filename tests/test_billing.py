from core import curated


def test_validate_code_accepts_only_curated_codes():
    assert curated.validate_code("ICD-10", "I48.91") is True
    assert curated.validate_code("CPT", "99232") is True
    assert curated.validate_code("ICD-10", "ZZZ.999") is False
    assert curated.validate_code("unknown", "99232") is False


def test_code_details_are_derived_from_curated_tables():
    assert curated.code_details("ICD-10", "I48.91") == {
        "code": "I48.91",
        "system": "ICD-10",
        "label": "Atrial fibrillation, unspecified",
    }
    assert curated.code_for_term("chest pain") == {
        "code": "R07.9",
        "system": "ICD-10",
        "label": "Chest pain, unspecified",
    }
