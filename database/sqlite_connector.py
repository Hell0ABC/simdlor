import logging
import datetime as _dt
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping, Sequence

"""
TODO:
    Initiate DB connect with closing
    Get tables and values
    Data modification
    Drop and rename tables
    Remove hashes like self.tables, just call for data
"""

try:  # Пытаемся использовать логгер Kivy
    from kivy.logger import Logger
except ImportError:  # Фоллбэк на стандартный logging
    Logger = logging.getLogger("sqlite_connector")
    if not Logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
        Logger.addHandler(handler)
    Logger.setLevel(logging.INFO)

def _flexible_date_converter(value: bytes):
    text = value.decode()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    logging.getLogger("sqlite_connector").warning("Unexpected DATE format: %s", text)
    return text  # отдаём строку, если форматы не подошли

sqlite3.register_converter("DATE", _flexible_date_converter)

class Database:
    """
    Небольшой слой поверх sqlite3:
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
        tables = [row["name"] for row in rows]
        Logger.debug("DB: tables = %s", tables)
        return tables

    def describe_table(self, table: str) -> list[dict[str, Any]]:
        table = self._validate_table(table)
        pragma_sql = f'PRAGMA table_info("{table}")'
        rows = self._conn.execute(pragma_sql).fetchall()
        if not rows:
            raise ValueError(f"Таблица '{table}' не найдена")
        return [dict(row) for row in rows]

    def fetch_rows(
        self,
        table: str,
        *,
        columns: Sequence[str] | None = None,
        where: str | None = None,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
        order_by: Sequence[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        table = self._validate_table(table)
        params = params or ()
        selected = ", ".join(self._validate_column(col, table) for col in columns) if columns else "*"

        sql = [f'SELECT {selected} FROM "{table}"']
        if where:
            sql.append(f"WHERE {where}")
        if order_by:
            order_clause = ", ".join(self._validate_column(col, table) for col in order_by)
            sql.append(f"ORDER BY {order_clause}")
        if limit is not None:
            sql.append("LIMIT ?")
            params = (*params, limit) if isinstance(params, tuple) else list(params) + [limit]
        if offset is not None:
            sql.append("OFFSET ?")
            params = (*params, offset) if isinstance(params, tuple) else list(params) + [offset]

        query = " ".join(sql)
        Logger.debug("DB: fetch query=%s params=%s", query, params)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def insert_row(self, table: str, data: Mapping[str, Any]) -> int:
        if not data:
            raise ValueError("insert_row: data пустое")
        table = self._validate_table(table)
        columns = [self._validate_column(col, table) for col in data.keys()]
        placeholders = ", ".join("?" for _ in columns)
        sql = f'INSERT INTO "{table}" ({", ".join(columns)}) VALUES ({placeholders})'
        Logger.debug("DB: insert %s data=%s", table, data)
        cur = self._conn.execute(sql, tuple(data.values()))
        self._conn.commit()
        return cur.lastrowid

    def update_rows(
        self,
        table: str,
        data: Mapping[str, Any],
        *,
        where: str,
        params: Sequence[Any] | Mapping[str, Any],
    ) -> int:
        if not data:
            raise ValueError("update_rows: data пустое")
        table = self._validate_table(table)
        assignments = ", ".join(f'{self._validate_column(col, table)} = ?' for col in data.keys())
        sql = f'UPDATE "{table}" SET {assignments} WHERE {where}'
        bind_params = tuple(data.values())
        if isinstance(params, Mapping):
            raise ValueError("Для именованных параметров используйте синтаксис :name и объедините словари вручную.")
        bind_params += tuple(params)
        Logger.debug("DB: update %s set=%s where=%s params=%s", table, data, where, bind_params)
        cur = self._conn.execute(sql, bind_params)
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
        Logger.warning("DB: drop table %s", table)
        self._conn.execute(f'DROP TABLE IF EXISTS "{table}"')
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
                try:
                    self._conn.execute(sql)
                except sqlite3.DatabaseError:
                    Logger.warning("DB: pragma %s не поддерживается", key)

    def _validate_table(self, table: str) -> str:
        if not table or not self._IDENT_RE.match(table):
            raise ValueError(f"Некорректное имя таблицы: {table!r}")
        return table

    def _validate_column(self, column: str, table: str) -> str:
        if column == "*":
            return column
        if not column or not self._IDENT_RE.match(column):
            raise ValueError(f"Некорректное имя колонки: {column!r}")
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