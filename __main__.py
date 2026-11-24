from __future__ import annotations

import argparse
import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3 as std_sqlite
import tempfile
import unicodedata
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openpyxl import load_workbook
from pydantic import BaseModel, Field
from sqlcipher3 import dbapi2 as sqlite3

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _config_path(name: str, default: str) -> Path:
    value = Path(os.environ.get(name, default)).expanduser()
    return value if value.is_absolute() else ROOT / value


def _config_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
        raise ValueError(f"{name} must be a boolean value.")
    return normalized in {"1", "true", "yes", "on"}


DATABASE_FILE = _config_path("BUDGET_DATABASE", "data/budget.sqlite3")
WORKBOOK_FILE = _config_path("BUDGET_WORKBOOK", "data/budget.xlsx")
DATABASE_PASSWORD = os.environ.get("BUDGET_DATABASE_PASSWORD", "")
HOST = os.environ.get("BUDGET_HOST", "127.0.0.1").strip()
PORT = int(os.environ.get("BUDGET_PORT", "80"))
COOKIE_NAME = "budget_session"
SESSION_HOURS = int(os.environ.get("BUDGET_SESSION_HOURS", "12"))
COOKIE_SECURE = _config_bool("BUDGET_COOKIE_SECURE", False)
PROXY_HEADERS = _config_bool("BUDGET_PROXY_HEADERS", True)
FORWARDED_ALLOW_IPS = os.environ.get("BUDGET_FORWARDED_ALLOW_IPS", "127.0.0.1")
LOG_LEVEL = os.environ.get("BUDGET_LOG_LEVEL", "INFO").upper()
PASSWORD_LENGTH = 12
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

if not HOST:
    raise ValueError("BUDGET_HOST cannot be empty.")
if not 1 <= PORT <= 65535:
    raise ValueError("BUDGET_PORT must be between 1 and 65535.")
if SESSION_HOURS < 1:
    raise ValueError("BUDGET_SESSION_HOURS must be at least 1.")
if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    raise ValueError("BUDGET_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("budget")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    if len(DATABASE_PASSWORD) < 16:
        raise ValueError(
            "Set BUDGET_DATABASE_PASSWORD to at least 16 characters in .env before starting the app."
        )
    if DATABASE_FILE.is_file() and _is_plaintext_database(DATABASE_FILE):
        _migrate_plaintext_database()

    connection = sqlite3.connect(str(DATABASE_FILE), timeout=10)
    escaped_password = DATABASE_PASSWORD.replace("'", "''")
    connection.execute(f"PRAGMA key = '{escaped_password}'")
    try:
        connection.execute("SELECT COUNT(1) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError as exc:
        connection.close()
        raise ValueError(
            "Unable to unlock the database; verify BUDGET_DATABASE_PASSWORD."
        ) from exc

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    if os.name == "posix":
        os.chmod(DATABASE_FILE, 0o600)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _is_plaintext_database(path: Path) -> bool:
    with path.open("rb") as database:
        return database.read(16) == b"SQLite format 3\x00"


def _migrate_plaintext_database() -> None:
    """Encrypt an existing SQLite file, preserving committed data without leaving a plaintext backup."""

    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, snapshot_name = tempfile.mkstemp(
        prefix=f".{DATABASE_FILE.name}.", suffix=".plaintext", dir=DATABASE_FILE.parent
    )
    os.close(file_descriptor)
    snapshot = Path(snapshot_name)
    encrypted = snapshot.with_suffix(".encrypted")
    try:
        plaintext = std_sqlite.connect(str(DATABASE_FILE), timeout=10)
        copy = std_sqlite.connect(str(snapshot), timeout=10)
        try:
            plaintext.backup(copy)
        finally:
            copy.close()
            plaintext.close()

        escaped_password = DATABASE_PASSWORD.replace("'", "''")
        escaped_path = str(encrypted).replace("'", "''")
        connection = sqlite3.connect(str(snapshot), timeout=10)
        try:
            connection.execute(
                f"ATTACH DATABASE '{escaped_path}' AS encrypted KEY '{escaped_password}'"
            )
            try:
                connection.execute("SELECT sqlcipher_export('encrypted')")
            finally:
                connection.execute("DETACH DATABASE encrypted")
        finally:
            connection.close()

        verification = sqlite3.connect(str(encrypted), timeout=10)
        try:
            verification.execute(f"PRAGMA key = '{escaped_password}'")
            verification.execute("SELECT COUNT(1) FROM sqlite_master").fetchone()
        finally:
            verification.close()

        original_rows = std_sqlite.connect(f"file:{snapshot.as_posix()}?mode=ro", uri=True)
        try:
            try:
                expected_expenses = original_rows.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            except std_sqlite.OperationalError:
                expected_expenses = None
        finally:
            original_rows.close()
        if expected_expenses is not None:
            verification = sqlite3.connect(str(encrypted), timeout=10)
            try:
                verification.execute(f"PRAGMA key = '{escaped_password}'")
                actual_expenses = verification.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            finally:
                verification.close()
            if actual_expenses != expected_expenses:
                raise RuntimeError(
                    "Encrypted database verification failed; original database was not replaced."
                )

        for suffix in ("-wal", "-shm"):
            Path(f"{DATABASE_FILE}{suffix}").unlink(missing_ok=True)
        os.replace(encrypted, DATABASE_FILE)
    finally:
        snapshot.unlink(missing_ok=True)
        encrypted.unlink(missing_ok=True)
    logger.info("Encrypted the existing database with SQLCipher.")


def _value_text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _clean_description(value: str | None) -> str | None:
    if not value:
        return None
    result = re.sub(r"\s*00:00:00\b", "", value).strip()
    return result or None


def _sync_household_members(db: sqlite3.Connection) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO household_members (name)
        SELECT DISTINCT trim(name)
        FROM (
            SELECT paid_by AS name FROM expenses
            UNION ALL
            SELECT transfer_to AS name FROM expenses
            UNION ALL
            SELECT first_name || ' ' || last_name AS name FROM users
        )
        WHERE name IS NOT NULL AND trim(name) <> ''
        """
    )
    for column in ("paid_by", "transfer_to"):
        db.execute(
            f"""
            UPDATE expenses
            SET {column} = (
                SELECT name FROM household_members
                WHERE name = trim(expenses.{column}) COLLATE NOCASE
                LIMIT 1
            )
            WHERE {column} IS NOT NULL AND trim({column}) <> ''
            """
        )


def _merge_description(description: str | None, comments: str | None) -> str | None:
    parts = []
    for value in (description, comments):
        cleaned = _clean_description(value)
        if cleaned:
            parts.append(cleaned)
    return "; ".join(parts) or None


def _parse_amount(value: Any, row_number: int) -> float:
    if isinstance(value, str):
        normalized = value.strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            whole, fraction = normalized.rsplit(",", 1)
            normalized = whole.replace(",", "") + (f".{fraction}" if len(fraction) != 3 else fraction)
        try:
            return float(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid amount in 'Brut' row {row_number}") from exc
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid amount in 'Brut' row {row_number}") from exc


def initialize_database() -> None:
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(WORKBOOK_FILE.read_bytes()).hexdigest() if WORKBOOK_FILE.is_file() else None
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY,
                spent_on TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                supplier TEXT,
                description TEXT,
                paid_by TEXT,
                transfer_to TEXT
            );
            CREATE TABLE IF NOT EXISTS categories (
                category_key TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_fr TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS household_members (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            );
            CREATE INDEX IF NOT EXISTS expenses_date ON expenses(spent_on);
            CREATE INDEX IF NOT EXISTS expenses_category ON expenses(category);
            CREATE INDEX IF NOT EXISTS expenses_payer ON expenses(paid_by);
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        expense_columns = {row["name"] for row in db.execute("PRAGMA table_info(expenses)")}
        if "comments" in expense_columns:
            db.execute(
                """
                UPDATE expenses
                SET description = CASE
                    WHEN description IS NULL OR trim(description) = '' THEN trim(comments)
                    WHEN comments IS NULL OR trim(comments) = '' THEN description
                    ELSE trim(description) || '; ' || trim(comments)
                END
                WHERE comments IS NOT NULL AND trim(comments) <> ''
                """
            )
            db.execute("ALTER TABLE expenses DROP COLUMN comments")
        db.execute(
            """
            INSERT OR IGNORE INTO categories (category_key, name_en, name_fr)
            SELECT DISTINCT category, category, category
            FROM expenses
            WHERE category IS NOT NULL AND trim(category) <> ''
            """
        )
        _sync_household_members(db)
        current = db.execute(
            "SELECT value FROM app_metadata WHERE key = 'workbook_sha256'"
        ).fetchone()
        if current and (fingerprint is None or current["value"] == fingerprint):
            _apply_migrations(db)
            return

        if fingerprint is None:
            raise FileNotFoundError(
                f"Budget workbook not found: {WORKBOOK_FILE}. It is required for the initial import."
            )
        workbook = load_workbook(WORKBOOK_FILE, read_only=True, data_only=True)
        if "Brut" not in workbook.sheetnames:
            workbook.close()
            raise ValueError(f"The workbook has no 'Brut' (Budget) sheet: {WORKBOOK_FILE}")

        sheet = workbook["Brut"]
        rows: list[tuple[Any, ...]] = []
        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            values = tuple(row[:8])
            values += (None,) * (8 - len(values))
            if not values or values[0] is None:
                continue
            spent_on = values[0]
            if isinstance(spent_on, (datetime, date)):
                date_text = spent_on.date().isoformat() if isinstance(spent_on, datetime) else spent_on.isoformat()
            elif isinstance(spent_on, str):
                try:
                    date_text = date.fromisoformat(spent_on.strip()).isoformat()
                except ValueError as exc:
                    workbook.close()
                    raise ValueError(f"Invalid date in 'Brut' row {row_number}") from exc
            else:
                workbook.close()
                raise ValueError(f"Invalid date in 'Brut' row {row_number}")

            try:
                amount = _parse_amount(values[1], row_number)
            except ValueError:
                workbook.close()
                raise

            description = _merge_description(_value_text(values[4]), _value_text(values[7]))
            rows.append(
                (
                    date_text,
                    amount,
                    *(_value_text(value) for value in values[2:4]),
                    description,
                    *(_value_text(value) for value in values[5:7]),
                )
            )
        workbook.close()

        db.execute("DELETE FROM expenses")
        db.executemany(
            """
            INSERT INTO expenses
                (spent_on, amount, category, supplier, description, paid_by, transfer_to)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        db.execute(
            """
            INSERT OR IGNORE INTO categories (category_key, name_en, name_fr)
            SELECT DISTINCT category, category, category
            FROM expenses
            WHERE category IS NOT NULL AND trim(category) <> ''
            """
        )
        _sync_household_members(db)
        db.execute(
            """
            INSERT INTO app_metadata (key, value) VALUES ('workbook_sha256', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (fingerprint,),
        )
        logger.info("Imported %d rows from the workbook's Brut sheet", len(rows))
        # A re-import replaces every expense, so the data migrations apply again to the new rows.
        db.execute("DELETE FROM app_metadata WHERE key LIKE 'migration:%'")
        _apply_migrations(db)


def _migrate_dog_and_cat_into_pet(db: sqlite3.Connection) -> None:
    """Move every Dog or Cat expense to a Pet category, then delete Dog and Cat."""
    sources = [
        row["category_key"]
        for row in db.execute(
            """
            SELECT category_key FROM categories
            WHERE lower(category_key) IN ('dog', 'cat') OR lower(trim(name_en)) IN ('dog', 'cat')
            """
        )
    ]
    orphaned = db.execute(
        "SELECT 1 FROM expenses WHERE lower(trim(category)) IN ('dog', 'cat') LIMIT 1"
    ).fetchone()
    if not sources and not orphaned:
        return

    pet = db.execute(
        """
        SELECT category_key FROM categories
        WHERE category_key = 'pet' OR lower(trim(name_en)) = 'pet'
        ORDER BY category_key = 'pet' DESC
        LIMIT 1
        """
    ).fetchone()
    if pet:
        pet_key = pet["category_key"]
    else:
        pet_key = "pet"
        db.execute(
            "INSERT INTO categories (category_key, name_en, name_fr) VALUES (?, ?, ?)",
            (pet_key, "Pet", "Animal de compagnie"),
        )

    placeholders = ", ".join("?" for _ in sources) or "NULL"
    moved = db.execute(
        f"""
        UPDATE expenses SET category = ?
        WHERE category IN ({placeholders}) OR lower(trim(category)) IN ('dog', 'cat')
        """,
        (pet_key, *sources),
    ).rowcount
    db.execute(f"DELETE FROM categories WHERE category_key IN ({placeholders})", sources)
    logger.info("Moved %d Dog/Cat expenses to %r and deleted categories %s", moved, pet_key, sources)


def _same_name(name: str | None, target: str) -> bool:
    return name is not None and unicodedata.normalize("NFC", name).strip().casefold() == target.casefold()


def _recipient_values(db: sqlite3.Connection, target: str) -> list[str]:
    """The stored spellings of the recipient `target` (case, spacing and Unicode form aside)."""
    return [
        row["transfer_to"]
        for row in db.execute("SELECT DISTINCT transfer_to FROM expenses WHERE transfer_to IS NOT NULL")
        if _same_name(row["transfer_to"], target)
    ]


def _clear_recipient(db: sqlite3.Connection, target: str) -> int:
    """Clear the recipient `target` from every expense, then remove that household member if unused."""
    cleared = sum(
        db.execute("UPDATE expenses SET transfer_to = NULL WHERE transfer_to = ?", (name,)).rowcount
        for name in _recipient_values(db, target)
    )
    for member in db.execute("SELECT id, name FROM household_members").fetchall():
        if _same_name(member["name"], target) and not db.execute(
            "SELECT 1 FROM expenses WHERE paid_by = ? OR transfer_to = ? LIMIT 1", (member["name"], member["name"])
        ).fetchone():
            db.execute("DELETE FROM household_members WHERE id = ?", (member["id"],))
    logger.info("Cleared recipient %s from %d expenses", target, cleared)
    return cleared


def _merge_categories(
    db: sqlite3.Connection, sources: tuple[str, ...], target_key: str, name_en: str, name_fr: str
) -> int:
    """Move every expense of the `sources` categories (keys or English names) to `target_key`, then delete them.

    The target is created with `name_en` / `name_fr` when no category has that key or English name.
    Does nothing when no source category or expense exists.
    """
    wanted = {source.casefold() for source in sources}
    source_keys = [
        row["category_key"]
        for row in db.execute("SELECT category_key, name_en FROM categories").fetchall()
        if row["category_key"].casefold() in wanted or row["name_en"].strip().casefold() in wanted
    ]
    orphan_keys = [
        row["category"]
        for row in db.execute("SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL").fetchall()
        if row["category"].strip().casefold() in wanted
    ]
    keys = sorted(set(source_keys) | set(orphan_keys))
    if not keys:
        return 0
    target = db.execute(
        """
        SELECT category_key FROM categories
        WHERE category_key = ? OR lower(trim(name_en)) = lower(?)
        ORDER BY category_key = ? DESC
        LIMIT 1
        """,
        (target_key, name_en, target_key),
    ).fetchone()
    if target:
        target_key = target["category_key"]
    else:
        db.execute(
            "INSERT INTO categories (category_key, name_en, name_fr) VALUES (?, ?, ?)",
            (target_key, name_en, name_fr),
        )
    keys = [key for key in keys if key != target_key]
    placeholders = ", ".join("?" for _ in keys) or "NULL"
    moved = db.execute(
        f"UPDATE expenses SET category = ? WHERE category IN ({placeholders})", (target_key, *keys)
    ).rowcount
    db.execute(f"DELETE FROM categories WHERE category_key IN ({placeholders})", keys)
    logger.info("Moved %d expenses from categories %s to %r and deleted them", moved, keys, target_key)
    return moved


def _migrate_bus_and_transportation_into_transit(db: sqlite3.Connection) -> None:
    """Move every Bus or Transportation expense to a new Transit category, then delete those two."""
    _merge_categories(db, ("bus", "transport", "transportation"), "transit", "Transit", "Transport en commun")


def _migrate_medication_into_health(db: sqlite3.Connection) -> None:
    """Move every Medication expense to the Health category, then delete Medication."""
    _merge_categories(db, ("drug", "medication"), "health", "Health", "Santé")


# (target key, English name, French name, rename the target?, source category keys)
CATEGORY_GROUPS_2026_11_24: tuple[tuple[str, str, str, bool, tuple[str, ...]], ...] = (
    ("miscellaneous", "Miscellaneous", "Divers", False, ("unknown", "lost", "services", "work", "entreprise")),
    ("succession", "Inheritance", "Succession", False, ("lawyer",)),
    ("restaurant", "Restaurant", "Restaurant", False, ("coffee", "drinks", "tip", "snack", "dessert")),
    ("alcohol", "Alcohol", "Alcool", False, ("brewing",)),
    ("grocery", "Groceries", "Épicerie", False, ("cooking",)),
    ("house", "House", "Maison", False, (
        "furniture", "appliance", "hardware", "tool", "repair", "cleaning", "pool", "kitchen",
    )),
    ("entertainment", "Entertainment", "Divertissement", False, ("console", "gambling", "gym")),
    ("car", "Car", "Voiture", False, ("gas", "parking", "fine")),
    ("transit", "Transportation", "Transport", True, ("taxi",)),
    ("utilities", "Utilities", "Services", True, ("electricity", "internet", "phone", "television")),
    ("order", "Order", "Commande", False, ("shipping",)),
    ("hygiene", "Hygiene", "Hygiène", False, ("haircut",)),
    ("health", "Health", "Santé", False, ("psychology",)),
    ("income", "Income", "Revenu", False, ("refund", "discount", "found")),
    ("gift", "Gift", "Cadeau", False, ("charity",)),
    ("computer", "Technology", "Informatique", True, ("electronics", "mouse")),
    ("finance", "Finance", "Finances", True, ("bank", "fee", "interests", "credit", "loan", "crypto", "insurance")),
    ("travel", "Travel", "Voyage", False, ("hotel",)),
)


def _migrate_group_categories(db: sqlite3.Connection) -> None:
    """Reduce the categories to a short list of one-word categories (see CATEGORY_GROUPS_2026_11_24)."""
    # The business registration fee is SLCTI's; the other work expenses are personal and keep their recipient
    registration = db.execute(
        """
        SELECT id FROM expenses
        WHERE spent_on = '2018-11-12' AND round(amount, 2) = 331.0 AND supplier LIKE 'Registre des entreprises%'
        """
    ).fetchall()
    if registration:
        if not db.execute("SELECT 1 FROM household_members WHERE name = 'SLCTI'").fetchone():
            db.execute("INSERT INTO household_members (name) VALUES ('SLCTI')")
        db.executemany("UPDATE expenses SET transfer_to = 'SLCTI' WHERE id = ?", [(row["id"],) for row in registration])
        logger.info("Set recipient SLCTI on %d business registration expense(s)", len(registration))
    # A personal flight, filed under Work: it belongs with the travel expenses
    flight = db.execute(
        """
        UPDATE expenses SET category = 'travel'
        WHERE spent_on = '2026-09-08' AND round(amount, 2) = 643.97 AND supplier = 'Air Canada'
            AND EXISTS (SELECT 1 FROM categories WHERE category_key = 'travel')
        """
    ).rowcount
    logger.info("Moved %d Air Canada flight(s) to Travel", flight)
    for target_key, name_en, name_fr, rename, sources in CATEGORY_GROUPS_2026_11_24:
        _merge_categories(db, sources, target_key, name_en, name_fr)
        if rename:
            db.execute(
                "UPDATE categories SET name_en = ?, name_fr = ? WHERE category_key = ?",
                (name_en, name_fr, target_key),
            )


def _merge_person(db: sqlite3.Connection, source: str, target: str) -> int:
    """Replace the person `source` with `target` as payer and recipient, then remove `source` if unused.

    Also renames: `target` is created when it does not exist yet. Does nothing when `source` is absent.
    """
    names = {
        column: [
            row["name"]
            for row in db.execute(f"SELECT DISTINCT {column} AS name FROM expenses WHERE {column} IS NOT NULL")
            if _same_name(row["name"], source)
        ]
        for column in ("paid_by", "transfer_to")
    }
    source_members = [
        member for member in db.execute("SELECT id, name FROM household_members").fetchall()
        if _same_name(member["name"], source)
    ]
    if not source_members and not any(names.values()):
        return 0
    # The name column compares without case, so this also finds « slcti » for « SLCTI »
    if not db.execute("SELECT 1 FROM household_members WHERE name = ?", (target,)).fetchone():
        db.execute("INSERT INTO household_members (name) VALUES (?)", (target,))
    merged = 0
    for column, values in names.items():
        merged += sum(
            db.execute(f"UPDATE expenses SET {column} = ? WHERE {column} = ?", (target, name)).rowcount
            for name in values
        )
    for member in db.execute("SELECT id, name FROM household_members").fetchall():
        if _same_name(member["name"], source) and not db.execute(
            "SELECT 1 FROM expenses WHERE paid_by = ? OR transfer_to = ? LIMIT 1", (member["name"], member["name"])
        ).fetchone():
            db.execute("DELETE FROM household_members WHERE id = ?", (member["id"],))
    logger.info("Merged person %s into %s on %d expense fields", source, target, merged)
    return merged


def _migrate_merge_conjointe_into_conjoint(db: sqlite3.Connection) -> None:
    """Merge the person « conjointe » into « conjoint » (payer and recipient)."""
    _merge_person(db, "conjointe", "conjoint")


def _migrate_merge_first_names_into_full_names(db: sqlite3.Connection) -> None:
    """Merge « Simon » into « Simon Charest » and « Julie » into « Julie Emond » (payer and recipient)."""
    _merge_person(db, "Simon", "Simon Charest")
    _merge_person(db, "Julie", "Julie Emond")


def _migrate_rename_entreprise_to_slcti(db: sqlite3.Connection) -> None:
    """Rename the person « entreprise » to « SLCTI » (payer and recipient)."""
    _merge_person(db, "entreprise", "SLCTI")


def _migrate_remove_im_recipient(db: sqlite3.Connection) -> None:
    """Clear the recipient « Î.-M. » from every expense, then remove that household member."""
    _clear_recipient(db, "Î.-M.")


def _migrate_succession_recipient_to_category(db: sqlite3.Connection) -> None:
    """Move every expense whose recipient is « succession » to the Succession category, then clear that recipient."""
    recipients = _recipient_values(db, "succession")
    if not recipients:
        return
    category = db.execute(
        """
        SELECT category_key FROM categories
        WHERE category_key = 'succession' OR lower(trim(name_fr)) = 'succession'
        ORDER BY category_key = 'succession' DESC
        LIMIT 1
        """
    ).fetchone()
    if category:
        category_key = category["category_key"]
    else:
        category_key = "succession"
        db.execute(
            "INSERT INTO categories (category_key, name_en, name_fr) VALUES (?, ?, ?)",
            (category_key, "Inheritance", "Succession"),
        )
    moved = sum(
        db.execute("UPDATE expenses SET category = ? WHERE transfer_to = ?", (category_key, name)).rowcount
        for name in recipients
    )
    logger.info("Moved %d succession expenses to category %r", moved, category_key)
    _clear_recipient(db, "succession")


# Data migrations run once each, in order, at startup (and so on every deploy), inside the startup
# transaction: a failure rolls the whole migration back. Never rename an applied migration.
MIGRATIONS = (
    ("2026-11-23-merge-dog-and-cat-into-pet", _migrate_dog_and_cat_into_pet),
    ("2026-11-23-remove-im-recipient", _migrate_remove_im_recipient),
    ("2026-11-23-succession-recipient-to-category", _migrate_succession_recipient_to_category),
    ("2026-11-23-merge-conjointe-into-conjoint", _migrate_merge_conjointe_into_conjoint),
    ("2026-11-23-rename-entreprise-to-slcti", _migrate_rename_entreprise_to_slcti),
    ("2026-11-24-merge-first-names-into-full-names", _migrate_merge_first_names_into_full_names),
    ("2026-11-24-merge-bus-and-transportation-into-transit", _migrate_bus_and_transportation_into_transit),
    ("2026-11-24-merge-medication-into-health", _migrate_medication_into_health),
    ("2026-11-24-group-categories", _migrate_group_categories),
)


def _apply_migrations(db: sqlite3.Connection) -> None:
    for name, migrate in MIGRATIONS:
        key = f"migration:{name}"
        if db.execute("SELECT 1 FROM app_metadata WHERE key = ?", (key,)).fetchone():
            continue
        migrate(db)
        db.execute(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            (key, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        logger.info("Applied database migration %s", name)


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_LENGTH or len(password) > 128:
        raise HTTPException(
            status_code=422,
            detail=f"Password must be between {PASSWORD_LENGTH} and 128 characters.",
        )


def create_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    *,
    is_admin: bool = False,
) -> int:
    email = _validate_email(email)
    _validate_password(password)
    first_name, last_name = first_name.strip(), last_name.strip()
    if not first_name or not last_name or len(first_name) > 100 or len(last_name) > 100:
        raise HTTPException(status_code=422, detail="First and last names are required.")
    salt = secrets.token_bytes(16)
    with connect() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO users (email, first_name, last_name, password_salt, password_hash, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    first_name,
                    last_name,
                    salt,
                    _password_hash(password, salt),
                    int(is_admin),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="An account with that email already exists.") from exc
        return int(cursor.lastrowid)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _cookie_settings() -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": "strict",
        "path": "/",
        "max_age": SESSION_HOURS * 60 * 60,
    }


def _check_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit

        if urlsplit(origin).netloc.casefold() != request.headers.get("host", "").casefold():
            raise HTTPException(status_code=403, detail="Cross-origin request rejected.")
    elif request.headers.get("sec-fetch-site", "same-origin") not in {"same-origin", "none"}:
        raise HTTPException(status_code=403, detail="Cross-origin request rejected.")


async def require_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    with connect() as db:
        row = db.execute(
            """
            SELECT u.id, u.email, u.first_name, u.last_name, u.is_admin, s.expires_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_token_digest(token),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Sign in to continue.")
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_digest(token),))
            raise HTTPException(status_code=401, detail="Your session has expired.")
        return dict(row)


async def require_admin(user: Annotated[dict[str, Any], Depends(require_user)]) -> dict[str, Any]:
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


class LoginInput(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserInput(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=PASSWORD_LENGTH, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    is_admin: bool = False


class UserUpdateInput(BaseModel):
    email: str = Field(max_length=254)
    password: str | None = Field(default=None, min_length=PASSWORD_LENGTH, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    is_admin: bool


class HouseholdMemberInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ExpenseInput(BaseModel):
    spent_on: date
    amount: float = Field(allow_inf_nan=False)
    category: str | None = Field(default=None, max_length=100)
    supplier: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2500)
    paid_by: str | None = Field(default=None, max_length=100)
    transfer_to: str | None = Field(default=None, max_length=100)


class CategoryInput(BaseModel):
    name_en: str = Field(min_length=1, max_length=100)
    name_fr: str = Field(min_length=1, max_length=100)


app = FastAPI(title="Budget", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; "
        "object-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(ROOT / "static" / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/me")
def me(user: Annotated[dict[str, Any], Depends(require_user)]) -> dict[str, Any]:
    return {key: user[key] for key in ("email", "first_name", "last_name", "is_admin")}


@app.post("/api/login")
def login(data: LoginInput, request: Request, response: Response) -> dict[str, str]:
    _check_same_origin(request)
    email = _validate_email(data.email)
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        valid = user is not None
        if user:
            valid = hmac.compare_digest(
                _password_hash(data.password, user["password_salt"]), user["password_hash"]
            )
        if not valid:
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        db.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_digest(token), user["id"], expiry.isoformat()),
        )
        response.set_cookie(COOKIE_NAME, token, **_cookie_settings())
    return {"ok": "true"}


@app.post("/api/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    _check_same_origin(request)
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_digest(token),))
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    return {"ok": "true"}


@app.get("/api/filters")
def filters(user: Annotated[dict[str, Any], Depends(require_user)]) -> dict[str, list[str]]:
    with connect() as db:
        years = db.execute("SELECT DISTINCT substr(spent_on, 1, 4) AS year FROM expenses ORDER BY year DESC")
        months = db.execute("SELECT DISTINCT substr(spent_on, 1, 7) AS month FROM expenses ORDER BY month ASC")
        categories = db.execute(
            "SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL ORDER BY category COLLATE NOCASE"
        )
        payers = db.execute(
            "SELECT DISTINCT paid_by FROM expenses WHERE paid_by IS NOT NULL ORDER BY paid_by COLLATE NOCASE"
        )
        recipients = db.execute(
            "SELECT DISTINCT transfer_to FROM expenses WHERE transfer_to IS NOT NULL ORDER BY transfer_to COLLATE NOCASE"
        )
        return {
            "years": [row["year"] for row in years],
            "months": [row["month"] for row in months],
            "categories": [row["category"] for row in categories],
            "payers": [row["paid_by"] for row in payers],
            "recipients": [row["transfer_to"] for row in recipients],
        }


@app.get("/api/categories")
def categories(_: Annotated[dict[str, Any], Depends(require_user)]) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT c.category_key, c.name_en, c.name_fr, COUNT(e.id) AS usage_count
            FROM categories AS c
            LEFT JOIN expenses AS e ON e.category = c.category_key
            GROUP BY c.category_key
            ORDER BY c.name_en COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/categories", status_code=201)
def create_category(
    data: CategoryInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, str]:
    _check_same_origin(request)
    name_en = data.name_en.strip()
    name_fr = data.name_fr.strip()
    if not name_en or not name_fr:
        raise HTTPException(status_code=422, detail="Category names cannot be empty.")
    normalized = unicodedata.normalize("NFKD", name_en.casefold())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    category_key = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not category_key:
        raise HTTPException(status_code=422, detail="English category name must contain a letter or number.")
    with connect() as db:
        try:
            db.execute(
                "INSERT INTO categories (category_key, name_en, name_fr) VALUES (?, ?, ?)",
                (category_key, name_en, name_fr),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="A category with this English name already exists.") from exc
    return {"category_key": category_key, "name_en": name_en, "name_fr": name_fr}


@app.put("/api/categories/{category_key}")
def update_category(
    category_key: str,
    data: CategoryInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    _check_same_origin(request)
    name_en = data.name_en.strip()
    name_fr = data.name_fr.strip()
    if not name_en or not name_fr:
        raise HTTPException(status_code=422, detail="Category names cannot be empty.")

    def normalized_name(name: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", name).casefold().split())

    with connect() as db:
        current = db.execute(
            "SELECT category_key FROM categories WHERE category_key = ?", (category_key,)
        ).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Category not found.")
        normalized_names = (normalized_name(name_en), normalized_name(name_fr))
        matches = db.execute(
            "SELECT category_key, name_en, name_fr FROM categories WHERE category_key <> ?",
            (category_key,),
        ).fetchall()
        duplicate = next(
            (
                row for row in matches
                if (normalized_name(row["name_en"]), normalized_name(row["name_fr"])) == normalized_names
            ),
            None,
        )
        if duplicate:
            db.execute(
                "UPDATE expenses SET category = ? WHERE category = ?",
                (duplicate["category_key"], category_key),
            )
            db.execute("DELETE FROM categories WHERE category_key = ?", (category_key,))
            return {
                "category_key": duplicate["category_key"],
                "name_en": duplicate["name_en"],
                "name_fr": duplicate["name_fr"],
                "merged": True,
            }
        cursor = db.execute(
            "UPDATE categories SET name_en = ?, name_fr = ? WHERE category_key = ?",
            (name_en, name_fr, category_key),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found.")
    return {"category_key": category_key, "name_en": name_en, "name_fr": name_fr, "merged": False}


@app.delete("/api/categories/{category_key}")
def delete_category(
    category_key: str,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, str]:
    _check_same_origin(request)
    with connect() as db:
        if not db.execute("SELECT 1 FROM categories WHERE category_key = ?", (category_key,)).fetchone():
            raise HTTPException(status_code=404, detail="Category not found.")
        if db.execute("SELECT 1 FROM expenses WHERE category = ? LIMIT 1", (category_key,)).fetchone():
            raise HTTPException(status_code=409, detail="This category is used by existing expenses.")
        db.execute("DELETE FROM categories WHERE category_key = ?", (category_key,))
    return {"ok": "true"}


@app.get("/api/expenses")
def expenses(
    user: Annotated[dict[str, Any], Depends(require_user)],
    month: Annotated[str | None, Query(pattern=r"^(?:\d{4}-\d{2}|all)$")] = None,
    year: Annotated[str | None, Query(pattern=r"^\d{4}$")] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    payer: Annotated[str | None, Query(max_length=100)] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    filter_date: Annotated[str | None, Query(max_length=10)] = None,
    filter_amount: Annotated[str | None, Query(max_length=30)] = None,
    filter_category: Annotated[str | None, Query(max_length=100)] = None,
    filter_supplier: Annotated[str | None, Query(max_length=200)] = None,
    filter_description: Annotated[str | None, Query(max_length=2500)] = None,
    filter_paid_by: Annotated[str | None, Query(max_length=100)] = None,
    filter_transfer_to: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    sort_by: Annotated[str, Query(pattern=r"^(spent_on|supplier|category|amount|paid_by|transfer_to|description)$")] = "spent_on",
    sort_dir: Annotated[str, Query(pattern=r"^(asc|desc)$")] = "asc",
    category_language: Annotated[str, Query(pattern=r"^(en|fr)$")] = "en",
) -> dict[str, Any]:
    conditions: list[str] = []
    params: list[Any] = []
    if month is None:
        with connect() as db:
            latest_month = db.execute("SELECT MAX(substr(spent_on, 1, 7)) AS month FROM expenses").fetchone()["month"]
        if latest_month:
            conditions.append("substr(spent_on, 1, 7) = ?")
            params.append(latest_month)
    elif month != "all":
        conditions.append("substr(spent_on, 1, 7) = ?")
        params.append(month)
    if year:
        conditions.append("substr(spent_on, 1, 4) = ?")
        params.append(year)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if payer:
        conditions.append("paid_by = ?")
        params.append(payer)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(
            "(supplier LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' "
            "OR category LIKE ? ESCAPE '\\')"
        )
        params.extend([f"%{escaped}%"] * 3)
    for column, value in (
        ("spent_on", filter_date),
        ("supplier", filter_supplier),
        ("description", filter_description),
        ("paid_by", filter_paid_by),
        ("transfer_to", filter_transfer_to),
    ):
        if value:
            escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(f"{column} LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
    if filter_amount:
        escaped = filter_amount.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            "(CAST(amount AS TEXT) LIKE ? ESCAPE '\\' OR printf('%.2f', amount) LIKE ? ESCAPE '\\')"
        )
        params.extend([pattern, pattern])
    if filter_category:
        escaped = filter_category.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append(
            "(category LIKE ? ESCAPE '\\' OR EXISTS ("
            "SELECT 1 FROM categories c WHERE c.category_key = expenses.category "
            "AND (c.name_en LIKE ? ESCAPE '\\' OR c.name_fr LIKE ? ESCAPE '\\')))"
        )
        params.extend([pattern, pattern, pattern])
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    page_size = 50
    sort_columns = {
        "spent_on": "expenses.spent_on",
        "supplier": "expenses.supplier COLLATE NOCASE",
        "category": f"categories.name_{category_language} COLLATE NOCASE",
        "amount": "expenses.amount",
        "paid_by": "expenses.paid_by COLLATE NOCASE",
        "transfer_to": "expenses.transfer_to COLLATE NOCASE",
        "description": "expenses.description COLLATE NOCASE",
    }
    sort_direction = sort_dir.upper()

    with connect() as db:
        summary = db.execute(
            f"""
            SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total,
                   COALESCE(AVG(amount), 0) AS average
            FROM expenses{where}
            """,
            params,
        ).fetchone()
        category_totals = db.execute(
            f"""
            SELECT COALESCE(category, '') AS category, SUM(amount) AS total
            FROM expenses{where}
            GROUP BY category ORDER BY total DESC LIMIT 8
            """,
            params,
        ).fetchall()
        monthly = db.execute(
            f"""
            SELECT substr(spent_on, 1, 7) AS month, SUM(amount) AS total
            FROM expenses{where}
            GROUP BY month ORDER BY month DESC LIMIT 12
            """,
            params,
        ).fetchall()
        rows = db.execute(
            f"""
            SELECT expenses.id, expenses.spent_on, expenses.amount, expenses.category,
                   expenses.supplier, expenses.description, expenses.paid_by, expenses.transfer_to
            FROM expenses
            LEFT JOIN categories ON categories.category_key = expenses.category{where}
            ORDER BY {sort_columns[sort_by]} {sort_direction}, expenses.id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()

    return {
        "items": [dict(row) for row in rows],
        "count": summary["count"],
        "total": round(summary["total"], 2),
        "average": round(summary["average"], 2),
        "page": page,
        "page_size": page_size,
        "categories": [dict(row) for row in category_totals],
        "monthly": [dict(row) for row in reversed(monthly)],
    }


def _expense_values(data: ExpenseInput) -> tuple[Any, ...]:
    category = data.category.strip() if data.category else ""
    return (
        data.spent_on.isoformat(),
        data.amount,
        category or None,
        *(value.strip() or None if value else None for value in (
            data.supplier, _clean_description(data.description), data.paid_by, data.transfer_to
        )),
    )


def _validate_expense_members(
    db: sqlite3.Connection, values: tuple[Any, ...]
) -> tuple[Any, ...]:
    validated = list(values)
    for index in (5, 6):
        name = validated[index]
        if name is None:
            continue
        member = db.execute(
            "SELECT name FROM household_members WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if not member:
            raise HTTPException(status_code=422, detail="Select a valid household member.")
        validated[index] = member["name"]
    return tuple(validated)


@app.post("/api/expenses", status_code=201)
def create_expense(
    data: ExpenseInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_user)],
) -> dict[str, int]:
    _check_same_origin(request)
    values = _expense_values(data)
    with connect() as db:
        values = _validate_expense_members(db, values)
        if values[2] is not None and not db.execute(
            "SELECT 1 FROM categories WHERE category_key = ?", (values[2],)
        ).fetchone():
            raise HTTPException(status_code=422, detail="Select a valid category.")
        cursor = db.execute(
            """
            INSERT INTO expenses
                (spent_on, amount, category, supplier, description, paid_by, transfer_to)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    return {"id": cursor.lastrowid}


@app.put("/api/expenses/{expense_id}")
def update_expense(
    expense_id: int,
    data: ExpenseInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_user)],
) -> dict[str, int]:
    _check_same_origin(request)
    values = _expense_values(data)
    with connect() as db:
        values = _validate_expense_members(db, values)
        if values[2] is not None and not db.execute(
            "SELECT 1 FROM categories WHERE category_key = ?", (values[2],)
        ).fetchone():
            raise HTTPException(status_code=422, detail="Select a valid category.")
        cursor = db.execute(
            """
            UPDATE expenses
            SET spent_on = ?, amount = ?, category = ?, supplier = ?, description = ?,
                paid_by = ?, transfer_to = ?
            WHERE id = ?
            """,
            (*values, expense_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Expense not found.")
    return {"id": expense_id}


@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_user)],
) -> Response:
    _check_same_origin(request)
    with connect() as db:
        cursor = db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Expense not found.")
    return Response(status_code=204)


@app.get("/api/users")
def users(_: Annotated[dict[str, Any], Depends(require_admin)]) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            "SELECT id, email, first_name, last_name, is_admin, created_at FROM users ORDER BY last_name COLLATE NOCASE"
        )
        return [dict(row) for row in rows]


@app.post("/api/users", status_code=201)
def add_user(
    data: UserInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, int]:
    _check_same_origin(request)
    user_id = create_user(
        data.email, data.password, data.first_name, data.last_name, is_admin=data.is_admin
    )
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO household_members (name) VALUES (?)",
            (f"{data.first_name.strip()} {data.last_name.strip()}",),
        )
    return {"id": user_id}


@app.put("/api/users/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateInput,
    request: Request,
    admin: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, str]:
    _check_same_origin(request)
    email = _validate_email(data.email)
    first_name, last_name = data.first_name.strip(), data.last_name.strip()
    if not first_name or not last_name:
        raise HTTPException(status_code=422, detail="First and last names are required.")
    with connect() as db:
        target = db.execute(
            "SELECT id, is_admin, first_name, last_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Account not found.")
        if target["is_admin"] and not data.is_admin:
            admin_count = db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
            if admin_count <= 1 or target["id"] == admin["id"]:
                raise HTTPException(status_code=400, detail="The last administrator cannot be demoted.")
        values: tuple[Any, ...]
        if data.password:
            _validate_password(data.password)
            salt = secrets.token_bytes(16)
            values = (
                email, first_name, last_name, int(data.is_admin), salt,
                _password_hash(data.password, salt), user_id,
            )
            query = """
                UPDATE users
                SET email = ?, first_name = ?, last_name = ?, is_admin = ?,
                    password_salt = ?, password_hash = ?
                WHERE id = ?
            """
        else:
            values = (email, first_name, last_name, int(data.is_admin), user_id)
            query = """
                UPDATE users
                SET email = ?, first_name = ?, last_name = ?, is_admin = ?
                WHERE id = ?
            """
        try:
            db.execute(query, values)
            old_name = f"{target['first_name']} {target['last_name']}"
            new_name = f"{first_name} {last_name}"
            if old_name.casefold() != new_name.casefold():
                db.execute(
                    "UPDATE expenses SET paid_by = ? WHERE paid_by = ? COLLATE NOCASE",
                    (new_name, old_name),
                )
                db.execute(
                    "UPDATE expenses SET transfer_to = ? WHERE transfer_to = ? COLLATE NOCASE",
                    (new_name, old_name),
                )
                existing_member = db.execute(
                    "SELECT id FROM household_members WHERE name = ? COLLATE NOCASE",
                    (old_name,),
                ).fetchone()
                if existing_member:
                    duplicate = db.execute(
                        "SELECT id FROM household_members WHERE name = ? COLLATE NOCASE",
                        (new_name,),
                    ).fetchone()
                    if duplicate:
                        db.execute(
                            "DELETE FROM household_members WHERE id = ?", (existing_member["id"],)
                        )
                    else:
                        db.execute(
                            "UPDATE household_members SET name = ? WHERE id = ?",
                            (new_name, existing_member["id"]),
                        )
                else:
                    db.execute(
                        "INSERT OR IGNORE INTO household_members (name) VALUES (?)", (new_name,)
                    )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="An account with that email already exists.") from exc
    return {"ok": "true"}


@app.delete("/api/users/{user_id}")
def remove_user(
    user_id: int,
    request: Request,
    admin: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, str]:
    _check_same_origin(request)
    with connect() as db:
        target = db.execute("SELECT id, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Account not found.")
        if target["id"] == admin["id"]:
            raise HTTPException(status_code=400, detail="You cannot remove your own account.")
        if target["is_admin"] and db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0] <= 1:
            raise HTTPException(status_code=400, detail="The last administrator cannot be removed.")
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return {"ok": "true"}


@app.get("/api/household-members")
def household_members(_: Annotated[dict[str, Any], Depends(require_user)]) -> list[dict[str, Any]]:
    with connect() as db:
        _sync_household_members(db)
        # Expenses where the person is the payer or the recipient (counted once when both)
        rows = db.execute(
            """
            SELECT m.id, m.name, (
                SELECT COUNT(*) FROM expenses AS e
                WHERE e.paid_by = m.name COLLATE NOCASE OR e.transfer_to = m.name COLLATE NOCASE
            ) AS usage_count
            FROM household_members AS m
            ORDER BY m.name COLLATE NOCASE
            """
        )
        return [dict(row) for row in rows]


@app.post("/api/household-members", status_code=201)
def add_household_member(
    data: HouseholdMemberInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    _check_same_origin(request)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="A name is required.")
    with connect() as db:
        try:
            cursor = db.execute("INSERT INTO household_members (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="A household member with that name already exists.") from exc
    return {"id": cursor.lastrowid, "name": name}


@app.put("/api/household-members/{member_id}")
def update_household_member(
    member_id: int,
    data: HouseholdMemberInput,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, Any]:
    _check_same_origin(request)
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="A name is required.")
    with connect() as db:
        current = db.execute(
            "SELECT name FROM household_members WHERE id = ?", (member_id,)
        ).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Household member not found.")
        duplicate = db.execute(
            """
            SELECT id, name FROM household_members
            WHERE name = ? COLLATE NOCASE AND id <> ?
            """,
            (name, member_id),
        ).fetchone()
        try:
            if duplicate:
                db.execute(
                    "UPDATE expenses SET paid_by = ? WHERE paid_by = ? COLLATE NOCASE",
                    (duplicate["name"], current["name"]),
                )
                db.execute(
                    "UPDATE expenses SET transfer_to = ? WHERE transfer_to = ? COLLATE NOCASE",
                    (duplicate["name"], current["name"]),
                )
                db.execute("DELETE FROM household_members WHERE id = ?", (member_id,))
                return {"id": duplicate["id"], "name": duplicate["name"], "merged": True}
            db.execute(
                "UPDATE expenses SET paid_by = ? WHERE paid_by = ? COLLATE NOCASE",
                (name, current["name"]),
            )
            db.execute(
                "UPDATE expenses SET transfer_to = ? WHERE transfer_to = ? COLLATE NOCASE",
                (name, current["name"]),
            )
            db.execute("UPDATE household_members SET name = ? WHERE id = ?", (name, member_id))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="A household member with that name already exists.") from exc
    return {"id": member_id, "name": name, "merged": False}


@app.delete("/api/household-members/{member_id}")
def remove_household_member(
    member_id: int,
    request: Request,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> dict[str, str]:
    _check_same_origin(request)
    with connect() as db:
        member = db.execute(
            "SELECT name FROM household_members WHERE id = ?", (member_id,)
        ).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Household member not found.")
        if db.execute(
            "SELECT 1 FROM expenses WHERE paid_by = ? COLLATE NOCASE OR transfer_to = ? COLLATE NOCASE LIMIT 1",
            (member["name"], member["name"]),
        ).fetchone():
            raise HTTPException(status_code=409, detail="This household member is used by existing expenses.")
        db.execute("DELETE FROM household_members WHERE id = ?", (member_id,))
    return {"ok": "true"}


def create_initial_admin() -> None:
    initialize_database()
    with connect() as db:
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise SystemExit("Users already exist; ask an administrator to create the account.")
    email = input("Email: ").strip()
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    password = getpass("Password (12+ characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    user_id = create_user(email, password, first_name, last_name, is_admin=True)
    print(f"Administrator account created (user id {user_id}).")


def backup_database(destination: Path) -> int:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing database backup: {destination}")

    with connect() as db:
        expected_count = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        escaped_path = str(destination).replace("'", "''")
        escaped_password = DATABASE_PASSWORD.replace("'", "''")
        db.execute(f"ATTACH DATABASE '{escaped_path}' AS budget_backup KEY '{escaped_password}'")
        try:
            db.execute("SELECT sqlcipher_export('budget_backup')")
        finally:
            db.execute("DETACH DATABASE budget_backup")

    try:
        actual_count = verify_database(destination)
        if actual_count != expected_count:
            raise RuntimeError(
                f"Backup verification failed: expected {expected_count} expenses, found {actual_count}."
            )
        if os.name == "posix":
            os.chmod(destination, 0o600)
        logger.info("Created encrypted database backup with %d expenses.", actual_count)
        return actual_count
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def verify_database(database_file: Path) -> int:
    database_file = database_file.expanduser().resolve()
    if not database_file.is_file():
        raise FileNotFoundError(f"Database file not found: {database_file}")
    if _is_plaintext_database(database_file):
        raise ValueError(f"Database is not encrypted with SQLCipher: {database_file}")

    connection = sqlite3.connect(str(database_file), timeout=10)
    escaped_password = DATABASE_PASSWORD.replace("'", "''")
    try:
        connection.execute(f"PRAGMA key = '{escaped_password}'")
        connection.execute("SELECT COUNT(1) FROM sqlite_master").fetchone()
        return connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise ValueError(
            f"Unable to verify {database_file}; check BUDGET_DATABASE_PASSWORD."
        ) from exc
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Budget web application.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("create-admin", "backup-database", "verify-database"),
        help="Create an administrator or manage an encrypted database",
    )
    parser.add_argument("database_file", nargs="?", type=Path, help="Backup destination or database to verify")
    args = parser.parse_args()
    if args.command == "create-admin":
        if args.database_file:
            parser.error("create-admin does not take a database file.")
        create_initial_admin()
    elif args.command == "backup-database":
        if not args.database_file:
            parser.error("backup-database requires a new destination path.")
        backup_database(args.database_file)
    elif args.command == "verify-database":
        if args.database_file:
            logger.info("Verified %d expenses.", verify_database(args.database_file))
        else:
            initialize_database()
            logger.info("Verified %d expenses.", verify_database(DATABASE_FILE))
    else:
        if args.database_file:
            parser.error("A database file requires a database command.")
        import uvicorn

        uvicorn.run(
            "__main__:app",
            host=HOST,
            port=PORT,
            log_level=LOG_LEVEL.lower(),
            proxy_headers=PROXY_HEADERS,
            forwarded_allow_ips=FORWARDED_ALLOW_IPS,
        )
