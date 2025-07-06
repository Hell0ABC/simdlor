from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRoundFlatButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
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


db = Database('hospital.db')


class Content(BoxLayout):
    pass


class ValueInput(MDTextField):
    def __init__(self, column, value_id, **kw):
        self.column = column
        self.value_id = value_id
        self.background_color = 'red'
        self.mode = 'rectangle'
        super().__init__(**kw)


class LoadingScreen(MDScreen):

    def on_enter(self):
        current = self.ids.progress_bar.value
        current += 100
        self.ids.progress_bar.value = current
        if self.ids.progress_bar.value == 100:
            self.manager.transition.direction = 'up'


class DatabaseScreen(MDScreen):

    def button_press(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'table'
        db.selected_table = instance.text
        db.table_values = db.get_table_values(db.selected_table)

    def on_enter(self):
        self.ids.db_box_layout.clear_widgets()
        for i in range(len(db.tables)):
            self.ids.db_box_layout.add_widget(
                MDRoundFlatButton(text=str(db.tables[i]),
                                  on_press=self.button_press,
                                  pos_hint={'center_x': .5, 'center_y': .5},
                                  padding=15,
                                  size_hint=(1, None)
                                  )
            )


class TableScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.last_text = None

    def widget_text_for_create(self, widget):
        return self.create_record(widget.text)

    def widget_text_for_update(self, widget):
        return self.update_table(self.last_text, widget.text, widget.column, widget.value_id)

    @staticmethod
    def pressed_button():
        db.save()

    @staticmethod
    def create_record(text):
        db.create_record(text)

    @staticmethod
    def update_table(lt, text, row, value):
        db.update_table(lt, text, row, value)

    @staticmethod
    def delete_row(value):
        db.delete_row(value)

    def on_focus(self, widget):
        self.last_text = widget.text

    def on_enter(self, *args):
        self.ids.table_grid_layout.clear_widgets()
        table = db.selected_table
        columns = db.get_table_columns(table)
        self.ids.table_grid_layout.cols = len(columns)
        values = db.get_table_values(table)
        values_len = len(values)
        for i in range(len(columns)):
            self.ids.table_grid_layout.add_widget(
                MDLabel(
                    text=str(columns[i])
                )
            )
        if values_len > 0:
            for i in range(values_len):
                for j in range(len(values[i])):
                    if j % 10 == 0:
                        self.ids.table_grid_layout.add_widget(
                            ValueInput(text=str(values[i][j]),
                                       on_double_tap=self.on_focus,
                                       on_text_validate=self.widget_text_for_update,
                                       multiline=False,
                                       value_id=i + 1,
                                       column=j,
                                       readonly=True)
                        )
                    else:
                        self.ids.table_grid_layout.add_widget(
                            ValueInput(text=str(values[i][j]),
                                       on_double_tap=self.on_focus,
                                       on_text_validate=self.widget_text_for_update,
                                       multiline=False,
                                       value_id=i + 1,
                                       column=j)
                        )
            for i in range(len(columns)):
                if i % 10 == 0:
                    self.ids.table_grid_layout.add_widget(ValueInput(
                        text='',
                        on_text_validate=self.widget_text_for_create,
                        multiline=False,
                        column=i,
                        value_id=i + 1,
                        readonly=True
                    ))
                else:
                    self.ids.table_grid_layout.add_widget(ValueInput(
                        text='',
                        on_text_validate=self.widget_text_for_create,
                        multiline=False,
                        column=i,
                        value_id=i + 1
                    ))
        else:
            for i in range(len(columns)):
                if i % 10 == 0:
                    self.ids.table_grid_layout.add_widget(ValueInput(
                        multiline=False,
                        on_text_validate=self.widget_text_for_create,
                        column=i,
                        value_id=i + 1,
                        readonly=True
                    ))
                else:
                    self.ids.table_grid_layout.add_widget(ValueInput(
                        multiline=False,
                        on_text_validate=self.widget_text_for_create,
                        column=i,
                        value_id=i + 1
                    ))


class DatabaseApp(MDApp):
    dialog = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        Builder.load_file('gui.kv')
        self.title = 'GUI for sqlite'
        sm = MDScreenManager()
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(TableScreen(name='table'))
        sm.add_widget(DatabaseScreen(name='database'))
        sm.current = 'database'
        return sm

    def show_confirmation_dialog(self):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Delete",
                type="custom",
                content_cls=Content()
            )
        self.dialog.open()


if __name__ == '__main__':
    DatabaseApp().run()
