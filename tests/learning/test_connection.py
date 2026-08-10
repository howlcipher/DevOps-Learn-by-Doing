import sqlite3
from pathlib import Path

import pytest

from devops_learn.learning.persistence.connection import (
    connect,
    connect_in_memory,
    default_db_path,
)


def test_default_db_path_is_under_the_home_directory() -> None:
    assert default_db_path() == Path.home() / ".devops_learn" / "learning.db"


def test_connect_creates_missing_parent_directories(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "learning.db"

    conn = connect(db_path)
    try:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO t (name) VALUES ('x')")
        row = conn.execute("SELECT name FROM t").fetchone()
    finally:
        conn.close()

    assert db_path.exists()
    assert row["name"] == "x"


def test_connect_enables_foreign_key_enforcement(tmp_path: Path) -> None:
    conn = connect(tmp_path / "learning.db")
    try:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER "
            "REFERENCES parent(id))"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child (parent_id) VALUES (999)")
    finally:
        conn.close()


def test_in_memory_connections_are_isolated_from_each_other() -> None:
    first = connect_in_memory()
    second = connect_in_memory()
    try:
        first.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        with pytest.raises(sqlite3.OperationalError):
            second.execute("SELECT * FROM t")
    finally:
        first.close()
        second.close()
