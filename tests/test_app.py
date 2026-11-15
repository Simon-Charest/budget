from __future__ import annotations

import hashlib
import importlib
import sqlite3
import sys
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook


def load_budget_app():
    app_path = Path(__file__).resolve().parents[1] / "__main__.py"
    spec = importlib.util.spec_from_file_location("budget_application", app_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_amount_import_accepts_workbook_number_formats():
    budget_app = load_budget_app()
    assert budget_app._parse_amount("263,50", 1) == 263.5
    assert budget_app._parse_amount("1 010.30", 2) == 1010.3
    assert budget_app._parse_amount("1.010,30", 3) == 1010.3


def test_runtime_configuration_uses_environment_and_project_relative_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("BUDGET_DATABASE", "instance/budget.sqlite3")
    monkeypatch.setenv("BUDGET_DATABASE_PASSWORD", "test-database-password")
    monkeypatch.setenv("BUDGET_WORKBOOK", "data/source.xlsx")
    monkeypatch.setenv("BUDGET_HOST", "0.0.0.0")
    monkeypatch.setenv("BUDGET_PORT", "8765")
    monkeypatch.setenv("BUDGET_COOKIE_SECURE", "yes")
    monkeypatch.setenv("BUDGET_SESSION_HOURS", "6")
    monkeypatch.setenv("BUDGET_PROXY_HEADERS", "off")
    monkeypatch.setenv("BUDGET_FORWARDED_ALLOW_IPS", "10.0.0.2")
    monkeypatch.setenv("BUDGET_LOG_LEVEL", "DEBUG")
    budget_app = load_budget_app()

    assert budget_app.DATABASE_FILE == budget_app.ROOT / "instance" / "budget.sqlite3"
    assert budget_app.DATABASE_PASSWORD == "test-database-password"
    assert budget_app.WORKBOOK_FILE == budget_app.ROOT / "data" / "source.xlsx"
    assert budget_app.HOST == "0.0.0.0"
    assert budget_app.PORT == 8765
    assert budget_app.COOKIE_SECURE is True
    assert budget_app.SESSION_HOURS == 6
    assert budget_app.PROXY_HEADERS is False
    assert budget_app.FORWARDED_ALLOW_IPS == "10.0.0.2"
    assert budget_app.LOG_LEVEL == "DEBUG"


def make_workbook(path: Path, market_amount: float = 12.5) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Brut"
    sheet.append(["Date", "Montant", "Type", "Fournisseur", "Description", "Payé par", "À transférer à", "Commentaires"])
    sheet.append([date(2025, 1, 3), market_amount, "food", "Market", "Groceries", "Sam", None, None])
    sheet.append([date(2025, 1, 4), 7.25, "coffee", "Cafe", None, "Alex", "Sam", "Morning"])
    workbook.save(path)


def create_test_app(monkeypatch, tmp_path):
    workbook_path = tmp_path / "budget.xlsx"
    database_path = tmp_path / "budget.sqlite3"
    make_workbook(workbook_path)
    monkeypatch.setenv("BUDGET_DATABASE", str(database_path))
    monkeypatch.setenv("BUDGET_DATABASE_PASSWORD", "test-database-password")
    monkeypatch.setenv("BUDGET_WORKBOOK", str(workbook_path))
    budget_app = load_budget_app()
    budget_app.initialize_database()
    return budget_app, TestClient(budget_app.app)


def test_workbook_imports_budget_sheet_and_refreshes_when_changed(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    with budget_app.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 2
        assert [tuple(row) for row in db.execute(
            "SELECT spent_on, amount, transfer_to FROM expenses ORDER BY id"
        ).fetchall()] == [
            ("2025-01-03", 12.5, None),
            ("2025-01-04", 7.25, "Sam"),
        ]
        db.execute("UPDATE expenses SET amount = 999")
    make_workbook(budget_app.WORKBOOK_FILE, market_amount=13.5)
    budget_app.initialize_database()
    with budget_app.connect() as db:
        assert db.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] == 20.75
    client.close()


def test_plaintext_database_is_migrated_to_encrypted_sqlcipher(monkeypatch, tmp_path):
    database_path = tmp_path / "budget.sqlite3"
    legacy = sqlite3.connect(database_path)
    legacy.execute("CREATE TABLE expenses (id INTEGER PRIMARY KEY, amount REAL NOT NULL)")
    legacy.executemany("INSERT INTO expenses (amount) VALUES (?)", [(12.5,), (7.25,)])
    legacy.commit()
    legacy.close()
    monkeypatch.setenv("BUDGET_DATABASE", str(database_path))
    monkeypatch.setenv("BUDGET_DATABASE_PASSWORD", "secure-test-database-password")
    budget_app = load_budget_app()

    with budget_app.connect() as db:
        assert tuple(db.execute("SELECT COUNT(*), SUM(amount) FROM expenses").fetchone()) == (2, 19.75)
    assert database_path.read_bytes()[:16] != b"SQLite format 3\x00"
    assert list(tmp_path.glob("*.plaintext")) == []
    backup_path = tmp_path / "verified-backup.sqlite3"
    assert budget_app.backup_database(backup_path) == 2
    assert budget_app.verify_database(backup_path) == 2

    monkeypatch.setenv("BUDGET_DATABASE_PASSWORD", "a different incorrect password")
    wrong_key_app = load_budget_app()
    try:
        with wrong_key_app.connect():
            pass
    except ValueError as exc:
        assert "verify BUDGET_DATABASE_PASSWORD" in str(exc)
    else:
        raise AssertionError("A wrong SQLCipher password must not open the database.")


def test_imported_budget_remains_available_after_workbook_is_removed(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    budget_app.WORKBOOK_FILE.unlink()
    budget_app.initialize_database()
    with budget_app.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 2
    client.close()


def test_budget_apis_are_private_and_login_filters_expenses(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    home = client.get("/")
    assert home.status_code == 200
    assert "login-form" in home.text
    assert home.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in home.headers["content-security-policy"]
    assert client.get("/favicon.svg").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/filters").status_code == 401
    assert client.get("/api/expenses").status_code == 401
    assert client.get("/api/users").status_code == 401

    budget_app.create_user("admin@example.ca", "correct horse battery", "Sam", "Admin", is_admin=True)
    login = client.post(
        "/api/login",
        json={"email": "ADMIN@example.ca", "password": "correct horse battery"},
        headers={"Origin": "http://testserver"},
    )
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert client.get("/api/filters").json()["years"] == ["2025"]

    expenses = client.get("/api/expenses", params={"category": "food"}).json()
    assert expenses["count"] == 1
    assert expenses["total"] == 12.5
    assert expenses["items"][0]["supplier"] == "Market"
    assert client.post("/api/logout", headers={"Origin": "http://testserver"}).status_code == 200
    assert client.get("/api/expenses").status_code == 401
    client.close()


def test_user_management_is_admin_only_and_password_is_never_stored(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    budget_app.create_user("member@example.ca", "a sufficiently long password", "Alex", "Member")
    client.post(
        "/api/login",
        json={"email": "member@example.ca", "password": "a sufficiently long password"},
        headers={"Origin": "http://testserver"},
    )
    assert client.get("/api/users").status_code == 403
    assert client.post(
        "/api/users",
        json={
            "email": "new@example.ca",
            "password": "another sufficiently long password",
            "first_name": "New",
            "last_name": "User",
        },
        headers={"Origin": "http://testserver"},
    ).status_code == 403
    with budget_app.connect() as db:
        user = db.execute("SELECT password_salt, password_hash FROM users").fetchone()
        assert b"a sufficiently long password" not in user["password_salt"]
        assert user["password_hash"] != hashlib.sha256(b"a sufficiently long password").digest()
    client.close()


def test_cross_origin_login_is_rejected(monkeypatch, tmp_path):
    _, client = create_test_app(monkeypatch, tmp_path)
    response = client.post(
        "/api/login",
        json={"email": "admin@example.ca", "password": "password123456"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    client.close()


def test_admin_can_create_and_remove_user_accounts(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    budget_app.create_user("admin@example.ca", "correct horse battery", "Sam", "Admin", is_admin=True)
    client.post(
        "/api/login",
        json={"email": "admin@example.ca", "password": "correct horse battery"},
        headers={"Origin": "http://testserver"},
    )
    headers = {"Origin": "http://testserver"}
    account = {
        "email": "new@example.ca",
        "password": "another sufficiently long password",
        "first_name": "New",
        "last_name": "User",
    }
    created = client.post("/api/users", json=account, headers=headers)
    assert created.status_code == 201
    assert len(client.get("/api/users").json()) == 2
    assert client.delete(f"/api/users/{created.json()['id']}", headers=headers).status_code == 200
    own_id = client.get("/api/users").json()[0]["id"]
    assert client.delete(f"/api/users/{own_id}", headers=headers).status_code == 400
    client.close()

