import sqlite3

"""
TODO:
    
"""


class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()
        self.tables = self.get_tables()
        self.selected_table = None
        self.table_values = self.get_table_values(self.selected_table)

    def get_tables(self):
        tables = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = tables.fetchall()
        for i in range(len(tables)):
            k = tables[i][0]
            tables[i] = k
        return tables

    def get_table_columns(self, table_name):
        info = self.cursor.execute(f"PRAGMA table_info({table_name})")
        info = info.fetchall()
        for i in range(len(info)):
            k = info[i][1]
            info[i] = k
        return info

    def get_table_values(self, table):
        if table is None:
            return None
        else:
            values = self.cursor.execute(f"SELECT * FROM {table}")
            values = values.fetchall()
            return values

    def create_record(self, value):
        max_id = 0
        for i in range(len(self.table_values)):
            if int(self.table_values[i][0]) > max_id:
                max_id = self.table_values[i][0]
        if value is '':
            value = max_id + 1
        self.table_values.append(str(value))
        self.cursor.execute(f'DELETE FROM {self.selected_table};')
        for i in range(len(self.table_values)):
            try:
                if len(self.table_values[i]) < len(self.get_table_columns(self.selected_table)):
                    self.table_values[i] = list(self.table_values[i])
                    try:
                        self.table_values[i].append(self.table_values[i + 1])
                        self.table_values.remove(self.table_values[i + 1])
                    except IndexError:
                        continue
            except IndexError:
                continue
            if (len(self.table_values[i]) % len(self.get_table_columns(self.selected_table)) == 0) and (
                    len(self.table_values[i]) != 0):
                val = []
                for j in range(len(self.table_values[0])):
                    val.append("'" + str(self.table_values[i][j]) + "'")
                if len(self.get_table_columns(self.selected_table)) == 2:
                    self.cursor.execute(f"INSERT INTO {self.selected_table} VALUES({val[0]}, {val[1]});")
                if len(self.get_table_columns(self.selected_table)) == 3:
                    self.cursor.execute(f"INSERT INTO {self.selected_table} VALUES({val[0]}, {val[1]}, {val[2]});")
                if len(self.get_table_columns(self.selected_table)) == 4:
                    self.cursor.execute(
                        f"INSERT INTO {self.selected_table} VALUES({val[0]}, {val[1]}, {val[2]}, {val[3]});")
                if len(self.get_table_columns(self.selected_table)) == 5:
                    self.cursor.execute(
                        f"INSERT INTO {self.selected_table} VALUES({val[0]}, {val[1]}, {val[2]}, {val[3]}, {val[4]});")
                if len(self.get_table_columns(self.selected_table)) == 6:
                    self.cursor.execute(
                        f"INSERT INTO {self.selected_table} VALUES({val[0]}, {val[1]}, {val[2]}, {val[3]}, {val[4]}, {val[5]});")
            else:
                break

    def update_table(self, last_value, value, row, value_id):
        column = self.get_table_columns(self.selected_table)
        column = column[row]
        last_value = "'" + str(last_value) + "'"
        value = "'" + str(value) + "'"
        self.cursor.execute(f"UPDATE {self.selected_table} SET {column} = {value} WHERE id = {value_id};")

    def delete_row(self, value_id):
        table = self.selected_table
        self.cursor.execute(f"DELETE FROM {table} WHERE id = {value_id};")
        return f'Row with id: {value_id} deleted from {table}'

    def save(self):
        self.db.commit()