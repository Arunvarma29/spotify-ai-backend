from fastapi.testclient import TestClient

from memory import api, db, errors
from memory.auth import mint_token

client = TestClient(api.app)
ADMIN_AUTH = {"Authorization": f"Bearer {mint_token('quality_admin', 'quality-console')}"}
USER_AUTH = {"Authorization": f"Bearer {mint_token('regular_user', 'quality-console')}"}


def test_quality_runs_identifies_admin_and_running_state(monkeypatch):
    monkeypatch.setenv("QUALITY_ADMIN_SUBJECTS", "quality_admin, another_admin ")
    monkeypatch.setattr(db, "golden_runs", lambda: [])
    monkeypatch.setattr(db, "experiment_status", lambda: {"experiment": "pilot"})

    admin = client.get("/quality/runs", headers=ADMIN_AUTH)
    user = client.get("/quality/runs", headers=USER_AUTH)

    assert admin.status_code == user.status_code == 200
    assert admin.json()["can_run"] is True
    assert user.json()["can_run"] is False
    assert admin.json()["is_running"] is False


def test_only_allowlisted_subject_can_start_quality_run(monkeypatch):
    monkeypatch.setenv("QUALITY_ADMIN_SUBJECTS", "quality_admin")
    started = []

    def fake_start(run_id):
        started.append(run_id)
        api.QUALITY_RUN_LOCK.release()

    monkeypatch.setattr(api, "_start_quality_run", fake_start)

    response = client.post("/quality/runs", headers=USER_AUTH)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == errors.FORBIDDEN
    assert started == []

    response = client.post("/quality/runs", headers=ADMIN_AUTH)
    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert started == [response.json()["run_id"]]


def test_only_one_quality_run_can_start_at_a_time(monkeypatch):
    monkeypatch.setenv("QUALITY_ADMIN_SUBJECTS", "quality_admin")
    assert api.QUALITY_RUN_LOCK.acquire(blocking=False)
    try:
        response = client.post("/quality/runs", headers=ADMIN_AUTH)
    finally:
        api.QUALITY_RUN_LOCK.release()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == errors.CONFLICT


def test_quality_run_lock_is_released_if_thread_cannot_start(monkeypatch):
    monkeypatch.setenv("QUALITY_ADMIN_SUBJECTS", "quality_admin")

    def fail_to_start(_run_id):
        raise RuntimeError("thread unavailable")

    monkeypatch.setattr(api, "_start_quality_run", fail_to_start)
    response = client.post("/quality/runs", headers=ADMIN_AUTH)

    assert response.status_code == 503
    assert api.QUALITY_RUN_LOCK.locked() is False


def test_quality_run_configuration_is_empty_by_default(monkeypatch):
    monkeypatch.delenv("QUALITY_ADMIN_SUBJECTS", raising=False)
    assert api.quality_admin_subjects() == set()
