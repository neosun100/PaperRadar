def test_register(client):
    response = client.post("/api/auth/register", json={"email": "test@test.com", "password": "secret123"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert "id" in data


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"email": "dup@test.com", "password": "secret123"})
    response = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "secret123"})
    assert response.status_code == 400


def test_login(client):
    client.post("/api/auth/register", json={"email": "login@test.com", "password": "secret123"})
    response = client.post("/api/auth/login", data={"username": "login@test.com", "password": "secret123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "wrong@test.com", "password": "secret123"})
    response = client.post("/api/auth/login", data={"username": "wrong@test.com", "password": "badpass"})
    assert response.status_code == 400


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data


def test_swagger_docs(client):
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_openapi_json(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
