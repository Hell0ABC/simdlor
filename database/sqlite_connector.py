import logging
import datetime as _dt
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping, Sequence

#Логгер Kivy или стандартный
try:
    from kivy.logger import Logger
except ImportError:
    Logger = logging.getLogger("sqlite_connector")
    if not Logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
        Logger.addHandler(handler)
    Logger.setLevel(logging.INFO)

#Конвертер даты для предотвращения ValueError: invalid literal for int() with base 10: b'12.04.2021'
def _flexible_date_converter(value: bytes):
    """Конвертер для поля DATE c несколькими форматами."""
    text = value.decode()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    logging.getLogger("sqlite_connector").warning("Unexpected DATE format: %s", text)
    return text 

sqlite3.register_converter("DATE", _flexible_date_converter)

class Database:
    """Обёртка над sqlite3 для безопасной работы c БД.

    Основные возможности:
      • автоматическое открытие / закрытие соединения;
      • безопасная работа c именами таблиц и колонок;
      • простые методы CRUD (select / insert / update / delete);
      • контекстный менеджер для транзакций.

    Использование:
      db = Database("my.db")
      rows = db.fetch_rows("users", where="age > ?", params=[18])

    Для мобильного приложения:
      • открываешь БД один раз на экран/репозиторий;
      • дергаешь методы этого класса в репозиториях/сервисах;
      • закрываешь через db.close() при уничтожении экрана/приложения.

    Методы:
      • list_tables / describe_table — структура БД.
      • fetch_rows — получение данных.
      • insert_row / update_rows / delete_rows — модификация.
      • drop_table — удаление таблицы.
    """

    _IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(
        self,
        db_path: str | Path,
        *,
        check_same_thread: bool = True,
        pragmas: Mapping[str, Any] | None = None,
    ) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite файл не найден: {self.db_path}")

        Logger.info("DB: opening %s", self.db_path)
        self._conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=check_same_thread,
        )
        self._conn.row_factory = sqlite3.Row

        self._apply_pragmas({"foreign_keys": "ON", "journal_mode": "WAL"}, replace=False)
        if pragmas:
            self._apply_pragmas(pragmas, replace=True)

    # ---------- Публичный API ----------

    def list_tables(self) -> list[str]:
        sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        rows = self._conn.execute(sql).fetchall()
        tables = [row[0] for row in rows]
        Logger.debug("DB: tables=%s", tables)
        return tables

    def describe_table(self, table: str) -> list[dict[str, Any]]:
        table = self._validate_table(table)
        sql = f'PRAGMA table_info("{table}")'
        rows = self._conn.execute(sql).fetchall()
        info = [dict(row) for row in rows]
        Logger.debug("DB: describe %s -> %s", table, info)
        return info

    def fetch_rows(
        self,
        table: str,
        *,
        columns: Sequence[str] | None = None,
        where: str | None = None,
        params: Sequence[Any] | None = None,
        order_by: Sequence[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        table = self._validate_table(table)
        bind_params: list[Any] = list(params) if params is not None else []
        selected = ", ".join(self._validate_column(col, table) for col in columns) if columns else "*"

        sql = [f'SELECT {selected} FROM "{table}"']
        if where:
            sql.append(f"WHERE {where}")
        if order_by:
            order_clause = ", ".join(self._validate_column(col, table) for col in order_by)
            sql.append(f"ORDER BY {order_clause}")
        if limit is not None:
            sql.append("LIMIT ?")
            bind_params.append(limit)
        if offset is not None:
            sql.append("OFFSET ?")
            bind_params.append(offset)

        query = " ".join(sql)
        Logger.debug("DB: fetch query=%s params=%s", query, bind_params)
        rows = self._conn.execute(query, tuple(bind_params)).fetchall()
        return [dict(row) for row in rows]

    def insert_row(self, table: str, data: Mapping[str, Any]) -> int:
        if not data:
            raise ValueError("insert_row: data пустое")
        table = self._validate_table(table)
        columns = ", ".join(self._validate_column(col, table) for col in data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})'
        Logger.debug("DB: insert into %s data=%s", table, data)
        cur = self._conn.execute(sql, tuple(data.values()))
        self._conn.commit()
        return cur.lastrowid

    def update_rows(
        self,
        table: str,
        data: Mapping[str, Any],
        *,
        where: str,
        params: Sequence[Any],
    ) -> int:
        if not data:
            raise ValueError("update_rows: data пустое")
        table = self._validate_table(table)
        assignments = ", ".join(f'{self._validate_column(col, table)} = ?' for col in data.keys())
        sql = f'UPDATE "{table}" SET {assignments} WHERE {where}'
        bind_params = list(data.values())
        bind_params.extend(params)
        Logger.debug("DB: update %s set=%s where=%s params=%s", table, data, where, bind_params)
        cur = self._conn.execute(sql, tuple(bind_params))
        self._conn.commit()
        return cur.rowcount

    def delete_rows(self, table: str, *, where: str, params: Sequence[Any] | Mapping[str, Any]) -> int:
        table = self._validate_table(table)
        sql = f'DELETE FROM "{table}" WHERE {where}'
        Logger.debug("DB: delete %s where=%s params=%s", table, where, params)
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur.rowcount

    def drop_table(self, table: str) -> None:
        table = self._validate_table(table)
        sql = f'DROP TABLE IF EXISTS "{table}"'
        Logger.warning("DB: drop table %s", table)
        self._conn.execute(sql)
        self._conn.commit()

    def commit(self) -> None:
        Logger.debug("DB: commit")
        self._conn.commit()

    def rollback(self) -> None:
        Logger.debug("DB: rollback")
        self._conn.rollback()

    def close(self) -> None:
        if getattr(self, "_conn", None):
            Logger.info("DB: closing %s", self.db_path)
            self._conn.close()
            self._conn = None

    # ---------- Контекстная транзакция ----------

    @contextmanager
    def transaction(self):
        try:
            Logger.debug("DB: begin")
            yield
        except Exception:
            Logger.exception("DB: rollback triggered")
            self.rollback()
            raise
        else:
            self.commit()

    # ---------- Внутренние помощники ----------

    def _apply_pragmas(self, pragmas: Mapping[str, Any], *, replace: bool) -> None:
        for key, value in pragmas.items():
            sql = f"PRAGMA {key} = {value}"
            Logger.debug("DB: PRAGMA %s", sql)
            if replace:
                self._conn.execute(sql)
            else:
                self._conn.execute(sql).fetchall()

    def _validate_table(self, table: str) -> str:
        if not table or not self._IDENT_RE.match(table):
            raise ValueError(f"Incorrect table name: {table!r}")
        return table

    def _validate_column(self, column: str, table: str) -> str:
        if column == "*":
            return column
        if not column or not self._IDENT_RE.match(column):
            raise ValueError(f"Incorrect column name: {column!r}")
        return column

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            Logger.exception("DB: error at __del__")


if __name__ == "__main__":
    connector = Database("hospital.db")

    print("Tables:", connector.list_tables())
    print("Describe 'patients':", connector.describe_table("patients"))
    print("Fetching rows from 'patients':", connector.fetch_rows("patients"))
    print("Inserting a new row into 'patients'")
    new_id = connector.insert_row("patients", {"name": "John Doe", "Birthday": "19.02.2003", "Sex": "M"})
    print("New row ID:", new_id)
    print("Fetching rows from 'patients':", connector.fetch_rows("patients"))

    connector.close()