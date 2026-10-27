def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_exposes_safe_database_and_version_details(client) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["migration"] == "not_managed"
    assert response.json()["version"]
    assert "url" not in response.text.lower()
