from core import repo
from core.seed import seed


def test_seed_matches_maria_demo_scenario(temp_db):
    seed()

    maria = repo.patient_by_username("maria")
    assert maria["name"] == "María Alvarez"
    assert maria["primary_language"] == "es"
    assert maria["reason_for_visit"] == "Chest pain"
