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
    sheet.append([date(2025, 1, 3), market_amount, "food", "Market", "Groceries 2025-01-03 00:00:00", "Sam", None, None])
    sheet.append([date(2025, 1, 4), 7.25, "coffee", "Cafe", None, "Alex", "Sam", "Morning 2025-01-04 00:00:00"])
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
            "SELECT spent_on, amount, transfer_to, description FROM expenses ORDER BY id"
        ).fetchall()] == [
            ("2025-01-03", 12.5, None, "Groceries 2025-01-03"),
            ("2025-01-04", 7.25, "Sam", "Morning 2025-01-04"),
        ]
        assert "comments" not in {
            row["name"] for row in db.execute("PRAGMA table_info(expenses)")
        }
        db.execute("UPDATE expenses SET amount = 999")
    make_workbook(budget_app.WORKBOOK_FILE, market_amount=13.5)
    budget_app.initialize_database()
    with budget_app.connect() as db:
        assert db.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] == 20.75
    client.close()


def test_legacy_comments_are_merged_into_description_and_column_removed(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    with budget_app.connect() as db:
        db.execute("ALTER TABLE expenses ADD COLUMN comments TEXT")
        db.execute(
            "UPDATE expenses SET description = 'Groceries; organic', comments = 'Weekly shop' WHERE id = 1"
        )
        db.execute("UPDATE expenses SET description = NULL, comments = 'No prior description' WHERE id = 2")

    budget_app.initialize_database()

    with budget_app.connect() as db:
        rows = db.execute("SELECT description FROM expenses ORDER BY id").fetchall()
        assert [row["description"] for row in rows] == [
            "Groceries; organic; Weekly shop",
            "No prior description",
        ]
        assert "comments" not in {
            row["name"] for row in db.execute("PRAGMA table_info(expenses)")
        }
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
    assert '<span class="brand-mark">B</span><span>Budget</span>' in home.text
    assert '© <span id="current-year"></span> Budget' in home.text
    assert 'class="brand-dot"' not in home.text
    assert "login-form" in home.text
    login_panel = home.text[home.text.index('<div class="login-panel">'):home.text.index("</section>", home.text.index('<div class="login-panel">'))]
    assert 'data-i18n="privateSpace"' not in login_panel
    assert 'data-i18n="welcome"' not in login_panel
    assert 'data-i18n="signInPrompt"' not in login_panel
    assert 'data-i18n="privateNote"' not in login_panel
    assert "YOUR MONEY, IN FOCUS" not in home.text
    assert "art-caption" not in home.text
    translations = client.get("/static/app.js").text
    assert "VOTRE ESPACE PRIVÉ" not in translations
    assert "Voyez vos finances autrement." not in translations
    assert "Connectez-vous pour consulter le budget du foyer." not in translations
    assert "Votre budget est privé et réservé aux utilisateurs connectés." not in translations
    nav = home.text[home.text.index('<nav id="navigation"'):home.text.index("</nav>")]
    assert [nav.index(f'data-view="{view}"') for view in ("budget", "users", "categories", "report")] == sorted(
        nav.index(f'data-view="{view}"') for view in ("budget", "users", "categories", "report")
    )
    assert 'id="budget-month-filter" data-month-filter' in home.text
    assert 'data-search-field="filter_date"' not in home.text
    assert '<select id="budget-category-filter" data-search-field="filter_category">' in home.text
    assert '<input aria-label="Filter category" data-search-field="filter_category">' not in home.text
    assert 'id="clear-filters-button"' in home.text
    budget_table = home.text[home.text.index('<table><thead><tr>'):home.text.index("</table>", home.text.index('<table><thead><tr>'))]
    assert all(f'data-budget-sort="{field}"' in budget_table for field in (
        "spent_on", "supplier", "category", "amount", "paid_by", "transfer_to", "description"
    ))
    assert 'data-i18n="comments"' not in home.text
    form = home.text[home.text.index('id="expense-form"'):home.text.index("</form>", home.text.index('id="expense-form"'))]
    fields = ['for="expense-date"', 'for="expense-supplier"', 'for="expense-category"',
              'for="expense-amount"', 'for="expense-payer"', 'for="expense-recipient"',
              'for="expense-description"']
    assert [form.index(field) for field in fields] == sorted(form.index(field) for field in fields)
    assert home.text.index('id="budget-view"') < home.text.index('id="budget-error"') < home.text.index('id="expense-rows"')
    assert 'data-i18n="footerNote"' not in home.text
    assert 'id="categories-link"' in home.text
    assert 'id="categories-view"' in home.text
    assert 'id="categories-page-error"' in home.text
    assert home.text.index('id="categories-page-error"') < home.text.index('id="category-table-body"')
    assert 'id="add-category-button"' in home.text
    assert 'id="category-table-body"' in home.text
    assert 'id="category-existing"' not in home.text
    assert 'id="category-dialog"' in home.text
    assert 'id="category-en"' in home.text
    assert 'id="category-fr"' in home.text
    category_table = home.text[home.text.index('class="category-table"'):home.text.index("</table>", home.text.index('class="category-table"'))]
    assert 'data-i18n="categoryEnglish"' in category_table
    assert 'data-i18n="categoryFrench"' in category_table
    assert 'id="category-filter-en"' in category_table
    assert 'id="category-filter-fr"' in category_table
    assert 'data-category-sort="name_en"' in category_table
    assert 'data-category-sort="name_fr"' in category_table
    category_view = home.text[home.text.index('id="categories-view"'):home.text.index('id="report-view"')]
    assert 'data-i18n="categorySettings"' not in category_view
    assert 'data-i18n="categoriesSubtitle"' not in category_view
    assert "Please check the information you entered." not in home.text
    assert 'id="add-user-button"' in home.text
    assert 'id="users-table-body"' in home.text
    assert 'data-i18n="name"' in home.text
    assert 'data-i18n="accountType"' in home.text
    assert 'id="user-dialog"' in home.text
    assert 'id="user-form"' in home.text
    assert 'id="user-admin"' in home.text
    assert '<select id="expense-payer" name="paid_by">' in home.text
    assert '<select id="expense-recipient" name="transfer_to">' in home.text
    assert 'id="household-members-table-body"' not in home.text
    assert 'id="add-household-member-button"' not in home.text
    assert 'id="person-name"' in home.text
    assert 'id="user-email"' in home.text
    assert 'data-i18n="noAccount"' in home.text
    app_js = client.get("/static/app.js").text
    assert 'person.kind === "member" ? 2 : person.is_admin ? 0 : 1' in app_js
    assert 'a.name.localeCompare(b.name, language, { sensitivity: "base" })' in app_js
    assert home.headers["cache-control"] == "no-store"
    assert 'href="#report"' in home.text
    report_start = home.text.index('id="report-view"')
    users_start = home.text.index('id="users-view"')
    assert report_start < home.text.index('id="total-spent"') < users_start
    assert report_start < home.text.index('id="category-chart"') < users_start
    assert report_start < home.text.index('id="monthly-chart"') < users_start
    assert home.text.index('id="expense-rows"') < report_start
    assert home.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in home.headers["content-security-policy"]
    assert client.get("/favicon.svg").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me").headers["cache-control"] == "no-store"
    assert client.get("/api/filters").status_code == 401
    assert client.get("/api/expenses").status_code == 401
    assert client.get("/api/users").status_code == 401
    assert client.get("/api/household-members").status_code == 401

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
    assert [member["name"] for member in client.get("/api/household-members").json()] == [
        "Alex", "Sam", "Sam Admin",
    ]

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
    assert client.post(
        "/api/household-members",
        json={"name": "No access"},
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
    member_names = {member["name"] for member in client.get("/api/household-members").json()}
    assert "New User" in member_names
    account_id = created.json()["id"]
    updated = client.put(
        f"/api/users/{account_id}",
        json={
            "email": "updated@example.ca",
            "first_name": "Updated",
            "last_name": "Account",
            "is_admin": True,
            "password": None,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    updated_account = next(user for user in client.get("/api/users").json() if user["id"] == account_id)
    assert (updated_account["email"], updated_account["first_name"], updated_account["is_admin"]) == (
        "updated@example.ca", "Updated", True
    )
    member_names = {member["name"] for member in client.get("/api/household-members").json()}
    assert "Updated Account" in member_names
    assert "New User" not in member_names
    assert client.put(
        f"/api/users/{account_id}",
        json={
            "email": "updated@example.ca",
            "first_name": "Updated",
            "last_name": "Account",
            "is_admin": False,
            "password": None,
        },
        headers=headers,
    ).status_code == 200
    own_id = next(user["id"] for user in client.get("/api/users").json() if user["email"] == "admin@example.ca")
    assert client.put(
        f"/api/users/{own_id}",
        json={
            "email": "admin@example.ca",
            "first_name": "Sam",
            "last_name": "Admin",
            "is_admin": False,
            "password": None,
        },
        headers=headers,
    ).status_code == 400
    assert client.delete(f"/api/users/{created.json()['id']}", headers=headers).status_code == 200
    member_names = {member["name"] for member in client.get("/api/household-members").json()}
    assert "Updated Account" in member_names
    assert client.delete(f"/api/users/{own_id}", headers=headers).status_code == 400
    client.close()


def test_expense_month_filters_sorting_and_crud(monkeypatch, tmp_path):
    budget_app, client = create_test_app(monkeypatch, tmp_path)
    budget_app.create_user("admin@example.ca", "correct horse battery", "Sam", "Admin", is_admin=True)
    headers = {"Origin": "http://testserver"}
    assert client.post(
        "/api/login",
        json={"email": "admin@example.ca", "password": "correct horse battery"},
        headers=headers,
    ).status_code == 200

    filters = client.get("/api/filters").json()
    assert filters["months"] == ["2025-01"]
    assert filters["payers"] == ["Alex", "Sam"]
    assert filters["recipients"] == ["Sam"]
    assert [member["name"] for member in client.get("/api/household-members").json()] == [
        "Alex", "Sam", "Sam Admin",
    ]
    default_month = client.get("/api/expenses").json()
    assert default_month["count"] == 2
    assert [item["spent_on"] for item in default_month["items"]] == ["2025-01-03", "2025-01-04"]
    assert [item["spent_on"] for item in client.get(
        "/api/expenses", params={"month": "all", "sort_by": "spent_on", "sort_dir": "desc"}
    ).json()["items"]] == ["2025-01-04", "2025-01-03"]
    assert [item["amount"] for item in client.get(
        "/api/expenses", params={"month": "all", "sort_by": "amount", "sort_dir": "desc"}
    ).json()["items"]] == [12.5, 7.25]
    assert [item["supplier"] for item in client.get(
        "/api/expenses", params={"month": "all", "sort_by": "supplier", "sort_dir": "asc"}
    ).json()["items"]] == ["Cafe", "Market"]
    assert client.get("/api/expenses", params={"sort_by": "unknown"}).status_code == 422
    assert client.get("/api/expenses", params={"month": "all", "filter_paid_by": "Alex"}).json()["count"] == 1
    assert client.get("/api/expenses", params={"month": "all", "filter_transfer_to": "Sam"}).json()["count"] == 1
    assert client.get("/api/expenses", params={"filter_date": "2025-01-03"}).json()["count"] == 1
    assert client.get("/api/expenses", params={"filter_amount": "12.50"}).json()["count"] == 1

    household_member = client.post(
        "/api/household-members", json={"name": "Taylor"}, headers=headers
    )
    assert household_member.status_code == 201
    household_member_data = household_member.json()
    assert household_member_data["name"] == "Taylor"
    assert set(household_member_data) == {"id", "name"}
    duplicate_member = client.post(
        "/api/household-members", json={"name": "Taylor Lee"}, headers=headers
    )
    assert duplicate_member.status_code == 201

    created_category = client.post(
        "/api/categories",
        json={"name_en": "Utilities", "name_fr": "Services publics"},
        headers=headers,
    )
    assert created_category.status_code == 201
    category_key = created_category.json()["category_key"]
    updated_category = client.put(
        "/api/categories/food",
        json={"name_en": "Food", "name_fr": "Alimentation"},
        headers=headers,
    )
    assert updated_category.status_code == 200
    assert any(item["category_key"] == category_key for item in client.get("/api/categories").json())
    assert client.get("/api/expenses", params={"filter_category": "Alimentation"}).json()["count"] == 1

    expense = {
        "spent_on": "2025-01-01",
        "amount": 42.75,
        "category": category_key,
        "supplier": "Power",
        "description": "Electricity 2025-01-01 00:00:00",
        "paid_by": "Taylor",
        "transfer_to": "Sam",
    }
    created = client.post("/api/expenses", json=expense, headers=headers)
    assert created.status_code == 201
    invalid_member_expense = {**expense, "paid_by": "Unknown person"}
    assert client.post("/api/expenses", json=invalid_member_expense, headers=headers).status_code == 422
    with budget_app.connect() as db:
        assert db.execute(
            "SELECT description FROM expenses WHERE id = ?", (created.json()["id"],)
        ).fetchone()["description"] == "Electricity 2025-01-01"
    duplicate_category = client.post(
        "/api/categories",
        json={"name_en": "Temporary duplicate", "name_fr": "Temporaire"},
        headers=headers,
    )
    assert duplicate_category.status_code == 201
    duplicate_expense = {**expense, "category": duplicate_category.json()["category_key"]}
    duplicate_expense_response = client.post(
          "/api/expenses", json=duplicate_expense, headers=headers
    )
    assert duplicate_expense_response.status_code == 201
    duplicate_expense_id = duplicate_expense_response.json()["id"]
    merged_category = client.put(
        f"/api/categories/{duplicate_category.json()['category_key']}",
        json={"name_en": " food ", "name_fr": "ALIMENTATION"},
        headers=headers,
    )
    assert merged_category.status_code == 200
    assert merged_category.json() == {
        "category_key": "food", "name_en": "Food", "name_fr": "Alimentation", "merged": True,
    }
    with budget_app.connect() as db:
        assert db.execute(
            "SELECT category FROM expenses WHERE id = ?", (duplicate_expense_id,)
        ).fetchone()["category"] == "food"
        assert db.execute(
            "SELECT COUNT(*) FROM categories WHERE category_key = ?",
            (duplicate_category.json()["category_key"],),
        ).fetchone()[0] == 0
    assert client.delete(
        f"/api/categories/{category_key}", headers=headers
    ).status_code == 409
    removable_category = client.post(
        "/api/categories",
        json={"name_en": "Other", "name_fr": "Autre"},
        headers=headers,
    )
    assert removable_category.status_code == 201
    assert client.delete(
        f"/api/categories/{removable_category.json()['category_key']}", headers=headers
    ).status_code == 200
    expense_id = created.json()["id"]
    all_month = client.get("/api/expenses", params={"month": "all"}).json()
    assert all_month["items"][0]["id"] == expense_id
    assert all_month["items"][0]["spent_on"] == "2025-01-01"

    expense["amount"] = 50
    expense["spent_on"] = "2025-02-01"
    assert client.put(f"/api/expenses/{expense_id}", json=expense, headers=headers).status_code == 200
    with budget_app.connect() as db:
        assert db.execute(
            "SELECT description FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()["description"] == "Electricity 2025-01-01"
    assert client.get("/api/filters").json()["months"] == ["2025-01", "2025-02"]
    assert client.get("/api/expenses", params={"month": "2025-02"}).json()["total"] == 50
    updated_member = client.put(
        f"/api/household-members/{household_member.json()['id']}",
        json={"name": "Taylor Lee"},
        headers=headers,
    )
    assert updated_member.status_code == 200
    assert updated_member.json() == {
        "id": duplicate_member.json()["id"], "name": "Taylor Lee", "merged": True,
    }
    with budget_app.connect() as db:
        assert db.execute(
            "SELECT paid_by FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()["paid_by"] == "Taylor Lee"
    assert client.delete(
        f"/api/household-members/{duplicate_member.json()['id']}", headers=headers
    ).status_code == 409
    assert client.delete(
        f"/api/household-members/{household_member.json()['id']}", headers=headers
    ).status_code == 404
    assert client.delete(
        f"/api/expenses/{duplicate_expense_id}", headers=headers
    ).status_code == 204
    assert client.delete(f"/api/expenses/{expense_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/expenses/{expense_id}", headers=headers).status_code == 404
    assert client.delete(
        f"/api/household-members/{duplicate_member.json()['id']}", headers=headers
    ).status_code == 200
    client.close()
