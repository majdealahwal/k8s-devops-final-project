import pytest

from app import create_app, db


@pytest.fixture
def client():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()


def test_default_priority_is_medium(client):
    res = client.post("/api/tasks", json={"title": "Write report"})
    assert res.status_code == 201
    assert res.get_json()["priority"] == "medium"


def test_create_task_with_valid_priorities(client):
    for p in ("low", "medium", "high"):
        res = client.post("/api/tasks", json={"title": f"task {p}", "priority": p})
        assert res.status_code == 201
        assert res.get_json()["priority"] == p


def test_invalid_priority_rejected(client):
    res = client.post("/api/tasks", json={"title": "Bad", "priority": "urgent"})
    assert res.status_code == 400
    assert "priority" in res.get_json()["error"]


def test_update_priority(client):
    task = client.post("/api/tasks", json={"title": "Fix bug"}).get_json()
    res = client.put(f"/api/tasks/{task['id']}", json={"priority": "high"})
    assert res.status_code == 200
    assert res.get_json()["priority"] == "high"


def test_filter_by_priority(client):
    client.post("/api/tasks", json={"title": "A", "priority": "high"})
    client.post("/api/tasks", json={"title": "B", "priority": "low"})
    res = client.get("/api/tasks?priority=high")
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_title_required(client):
    res = client.post("/api/tasks", json={"priority": "low"})
    assert res.status_code == 400


def test_health_and_ready(client):
    assert client.get("/health").get_json()["status"] == "ok"
    assert client.get("/ready").get_json()["status"] == "ready"
