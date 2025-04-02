from abc import ABC, abstractmethod
import sqlite3
from typing import Union
from datetime import datetime
import os
from oaplustools.package import AttributeObject


class _TableColumn:
    def __init__(self, table_name, column_name):
        self.table_name = table_name
        self.column_name = column_name

    def __repr__(self):
        return f"{self.table_name}({self.column_name})"


class _Table:
    def __init__(self, name, db_manager, columns=None, primary_key=None, foreign_keys=None):
        self.name = name
        self.db_manager = db_manager

        self.column = AttributeObject()
        self.columns = {}
        columns = columns if columns is not None else {}
        for column_name, column_type in columns.items():
            self.create_column(column_name, column_type)

        self.primary_key = primary_key
        self.foreign_keys = foreign_keys if foreign_keys is not None else {}

    def create_column(self, column_name, column_type):
        type_mapping = {
            int: "INTEGER",
            str: "TEXT",  # Or VARCHAR, depending on your SQL dialect
            float: "REAL",
            bytes: "BINARY",
            datetime: "DATETIME",  # "DATE",
            bool: "BOOLEAN",  # "BIT",
            # Add other Python types and their SQL equivalents as needed
        }
        sql_type = type_mapping.get(column_type, "TEXT")  # Default to TEXT if type is not mapped
        self.columns[column_name] = sql_type
        setattr(self.column, column_name, _TableColumn(self.name, column_name))
        return _TableColumn(self.name, column_name)

    def add_foreign_key(self, column_name, reference):
        if isinstance(reference, _TableColumn):
            reference = str(reference)
        self.foreign_keys[column_name] = reference

    def create(self):
        self.db_manager._execute_query(*self._build_create_table_query())

    def _build_create_table_query(self):
        col_defs = [f"{col_name} {col_type}" for col_name, col_type in self.columns.items()]
        if self.primary_key:
            col_defs.append(f"PRIMARY KEY ({self.primary_key})")

        for col_name, ref in self.foreign_keys.items():
            col_defs.append(f"FOREIGN KEY({col_name}) REFERENCES {ref}")

        query = f"CREATE TABLE IF NOT EXISTS {self.name} ({', '.join(col_defs)})"
        return query, ()

    def __getattr__(self, item):
        if item in self.columns:
            return _TableColumn(self.name, item)
        raise AttributeError(f"{self.name} has no attribute {item}")

    def __repr__(self):
        return self.name


class AbstractDBManager(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._commit()
        self._close()

    def __del__(self):
        self._close()

    @abstractmethod
    def _execute_query(self, query: str, params: tuple = ()):
        pass

    @abstractmethod
    def _fetch_all(self, query: str, params: tuple = ()):
        pass

    @abstractmethod
    def _commit(self):
        pass

    @abstractmethod
    def _close(self):
        pass

    def raw_query(self, query: str, params: tuple = ()):
        results = self._fetch_all(query, params)
        self._commit()
        return results

    def Table(self, name, columns=None, primary_key=None, foreign_keys=None):
        return _Table(name, self, columns, primary_key, foreign_keys)


class SQLiteDBManager(AbstractDBManager):
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def _execute_query(self, query: str, params: tuple = ()):
        try:
            self.cursor.execute(query, params)
        except Exception as e:
            print(f"SQLite error: {e}")

    def _fetch_all(self, query: str, params: tuple = ()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"SQLite error: {e}")
            return []

    def _commit(self):
        try:
            self.conn.commit()
        except Exception as e:
            print(f"SQLite error: {e}")

    def _close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            print(f"SQLite error: {e}")

    def insert(self, table: Union[str, _Table], data: dict):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self._execute_query(query, tuple(data.values()))
        self._commit()

    def update(self, table: Union[str, _Table], data: dict, where: dict):
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k.column_name if type(k) is not str else k} = ?" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        self._execute_query(query, tuple(data.values()) + tuple(where.values()))
        self._commit()

    def delete(self, table: Union[str, _Table], where: dict):
        where_clause = ' AND '.join([f"{k.column_name if type(k) is not str else k} = ?" for k in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        self._execute_query(query, tuple(where.values()))
        self._commit()

    def select(self, table: Union[str, _Table], columns: list = ["*"], where: dict = None, order_by: str = None):
        cols = ', '.join([column if type(column) is str else column.column_name for column in columns])
        query = f"SELECT {cols} FROM {table}"

        if where:
            where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
            query += f" WHERE {where_clause}"

        if order_by:
            query += f" ORDER BY {order_by}"

        return self._fetch_all(query, tuple(where.values()) if where else ())

    def create_table(self, table: Union[str, _Table], columns: dict, primary_key: str = None, foreign_keys: dict = None
                     ) -> _Table:
        if isinstance(table, str):
            table = self.Table(table, columns, primary_key, foreign_keys)

        col_defs = []
        for col_name, col_type in table.columns.items():
            col_def = f"{col_name} {col_type}"
            if col_name == table.primary_key:
                col_def += " PRIMARY KEY"
            col_defs.append(col_def)

        if table.foreign_keys:
            for col, ref in table.foreign_keys.items():
                col_defs.append(f"FOREIGN KEY({col}) REFERENCES {ref}")

        col_defs_str = ", ".join(col_defs)
        query = f"CREATE TABLE IF NOT EXISTS {table.name} ({col_defs_str})"
        self._execute_query(query)
        self._commit()
        return table

    def drop_table(self, table: Union[str, _Table]):
        query = f"DROP TABLE IF EXISTS {table}"
        self._execute_query(query)
        self._commit()


def local_test():
    db_path = "test.db"

    try:
        with SQLiteDBManager(db_path) as db:
            # Create 'users' table
            users_table = db.create_table("users", {"user_id": int, "name": str}, "user_id")
            print(f"Table created: {users_table.name}")

            # Insert data into 'users'
            db.insert(users_table, {"user_id": 1, "name": "Alice"})
            db.insert(users_table, {"user_id": 2, "name": "Bob"})

            # Update data in 'users'
            db.update(users_table, {"name": "Alice Smith"}, {users_table.column.user_id: 1})

            # Create a new column
            order_id_column = users_table.create_column("order_id", int)

            # Select data from 'users'
            users = db.select(users_table, [users_table.column.user_id, users_table.column.name])
            print("Users:", users)

            # Delete data from 'users'
            db.delete(users_table, {users_table.column.user_id: 2})

            # Re-fetch data from 'users'
            users_after_delete = db.select(users_table, ["user_id", "name"])
            print("Users after delete:", users_after_delete)

        # Check results
        assert len(users) == 2, "There should be two users initially."
        assert len(users_after_delete) == 1, "There should be one user after deletion."
        assert users_after_delete[0][1] == "Alice Smith", "The remaining user should be Alice Smith."

        print("All tests passed.")

    finally:
        # Clean up: remove the database file
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    local_test()
