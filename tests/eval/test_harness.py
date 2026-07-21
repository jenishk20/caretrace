from eval import harness
from core import repo


def test_temp_db_is_isolated_and_seedable():
    with harness.temp_db():
        p = harness.seed_patient(name="Ada")
        assert p["id"] and p["name"] == "Ada"
        assert repo.get_patient(p["id"])["name"] == "Ada"
    with harness.temp_db():
        assert repo.list_patients() == []


def test_timed_returns_latency():
    val, ms = harness.timed(lambda x: x + 1, 41)
    assert val == 42 and ms >= 0
