import pytest

from core import db, repo


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    path = tmp_path / "confide-test.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    return path


@pytest.fixture
def patient(temp_db):
    staff = repo.create_staff("doctor", "confide", "Dr. Test")
    return repo.create_patient(
        "María Alvarez",
        staff["id"],
        age=68,
        room="4B",
        primary_language="es",
        reason_for_visit="Chest pain",
    )
