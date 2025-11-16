import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from database.sqlite_connector import Database

@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "hospital_test.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(
            """
            CREATE TABLE Patients (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                Name      TEXT NOT NULL,
                Birthday  DATE NOT NULL,
                Sex       TEXT NOT NULL
            );
            CREATE TABLE Doctors (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                Name    TEXT NOT NULL,
                Special TEXT NOT NULL
            );
            INSERT INTO Patients (Name, Birthday, Sex)
            VALUES
                ('Alice', '1990-07-12', 'F'),
                ('Bob',   '1985-03-04', 'M');
            INSERT INTO Doctors (Name, Special)
            VALUES ('Dr. Smith', 'Cardiology');
            """
        )
        conn.commit()
    return path


@pytest.fixture
def db(db_path: Path):
    connector = Database(db_path)
    try:
        yield connector
    finally:
        connector.close()


def test_list_tables(db: Database):
    tables = db.list_tables()
    assert "Patients" in tables
    assert "Doctors" in tables


def test_describe_table(db: Database):
    columns = db.describe_table("Patients")
    assert {col["name"] for col in columns} == {"id", "Name", "Birthday", "Sex"}


def test_fetch_rows_default(db: Database):
    rows = db.fetch_rows("Patients", order_by=["id"])
    assert rows[0]["Name"] == "Alice"
    assert rows[1]["Sex"] == "M"


def test_fetch_rows_with_filter(db: Database):
    rows = db.fetch_rows("Patients", where="Sex = ?", params=("F",))
    assert len(rows) == 1
    assert rows[0]["Name"] == "Alice"


def test_insert_row(db: Database):
    new_id = db.insert_row(
        "Patients",
        {"Name": "Clara", "Birthday": "1992-11-23", "Sex": "F"},
    )
    rows = db.fetch_rows("Patients", where="id = ?", params=(new_id,))
    assert rows[0]["Name"] == "Clara"


def test_update_rows(db: Database):
    updated = db.update_rows(
        "Patients",
        {"Sex": "F"},
        where="Name = ?",
        params=("Bob",),
    )
    assert updated == 1
    rows = db.fetch_rows("Patients", where="Name = ?", params=("Bob",))
    assert rows[0]["Sex"] == "F"


def test_delete_rows(db: Database):
    deleted = db.delete_rows("Patients", where="Name = ?", params=("Alice",))
    assert deleted == 1
    rows = db.fetch_rows("Patients", where="Name = ?", params=("Alice",))
    assert rows == []


def test_drop_table(db: Database):
    db.drop_table("Doctors")
    assert db.describe_table("Doctors") == []


def test_transaction_context(db_path: Path):
    with closing(Database(db_path)) as db:
        with db.transaction():
            db.insert_row(
                "Patients",
                {"Name": "Duke", "Birthday": "1980-01-01", "Sex": "M"},
            )
    rows = Database(db_path).fetch_rows("Patients", where="Name = ?", params=("Duke",))
    assert rows


def test_transaction_rollback(db_path: Path):
    with closing(Database(db_path)) as db:
        with pytest.raises(ZeroDivisionError):
            with db.transaction():
                db._conn.execute(
                    'INSERT INTO "Patients" (Name, Birthday, Sex) VALUES (?, ?, ?)',
                    ("Eve", "1995-05-17", "F"),
                )
                raise ZeroDivisionError
    with closing(Database(db_path)) as db_check:
        rows = db_check.fetch_rows("Patients", where="Name = ?", params=("Eve",))
    assert rows == []