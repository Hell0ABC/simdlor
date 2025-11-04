from kivymd.uix.label import MDLabel
from ui.widgets import ValueInput

from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDButton, MDButtonText

from ui.widgets import ConnectForm
from app.config import BASE_DIR
"""
TODO:
    Remote DB screen
    DatabaseScreen
"""

class HomeScreen(MDScreen):
    dialog = None

    def on_pre_enter(self, *args):
        # preparing file manager
        if not hasattr(self, "fm"):
            from kivymd.uix.filemanager import MDFileManager
            self.fm = MDFileManager(select_path=self._on_pick, exit_manager=self._on_close)

    # --- Local ---
    def open_file_manager(self):
        import os
        start_dir = os.path.expanduser(BASE_DIR)
        self.fm.show(start_dir)

    def _on_close(self, *args):
        self.fm.close()

    def _on_pick(self, path: str):
        if not path.lower().endswith(".db"):
            self._toast("Pick a *.db file")
            return
        from database.sqlite_connector import Database
        app = self.get_running_app()
        app.repo = Database(path)
        self.fm.close()
        self.manager.current = "database"

    # --- Remote DB ---
    # BROKEN
    def open_remote_dialog(self):
        if self.dialog is None:
            self.dialog = MDDialog(
                title="Connect to remote DB",
                type="custom",
                content_cls=ConnectForm(),
                buttons=[
                    MDButton(
                        MDButtonText(text="Cancel"),
                        on_release=lambda *_: self.dialog.dismiss()
                    ),
                    MDButton(
                        MDButtonText(text="Connect"),
                        on_release=self._connect_remote
                    ),
                ],
            )
        self.dialog.open()

    def _connect_remote(self, *_):
        form = self.dialog.content_cls
        params = form.get_values()  # dict: {"engine","host","port","user","password","database","ssl"}
        engine = params["engine"]
        app = self.get_running_app()

        if engine == "MySQL":
            # import mysql.connector
            # conn = mysql.connector.connect(host=..., port=..., user=..., password=..., database=..., ssl_disabled=not params["ssl"])
            pass
        elif engine == "PostgreSQL":
            # import psycopg2
            # conn = psycopg2.connect(host=..., port=..., user=..., password=..., dbname=...)
            pass
        elif engine == "MSSQL":
            # import pyodbc
            # conn = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=host,port;DATABASE=db;UID=user;PWD=pwd;Encrypt=yes/no;TrustServerCertificate=yes/no;")
            pass
        else:
            self._toast("Unsupported engine")
            return

        # TODO: обернуть драйвер в адаптер по интерфейсу репозитория.
        # app.repo = RemoteRepo(conn)  # твой класс-обёртка
        self.dialog.dismiss()
        self.manager.current = "database"

    def _toast(self, text):
        from kivymd.toast import toast
        toast(text)

class LoadingScreen(MDScreen):
    def on_enter(self):
        current = self.ids.progress_bar.value
        current += 10
        self.ids.progress_bar.value = current
        if self.ids.progress_bar.value == 100:
            self.manager.transition.direction = 'up'

# BROKEN
class DatabaseScreen(MDScreen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def button_press(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'table'
        self.db.selected_table = instance.text
        self.db.table_values = self.db.get_table_values(self.db.selected_table)

    def on_enter(self):
        self.ids.db_box_layout.clear_widgets()
        for name in self.db.tables:
            btn = MDButtonText(
                size_hint=(1, None),
                height="48dp",
                pos_hint={"center_x": .5}
            )
            btn.add_widget(MDButtonText(text=str(name)))
            btn.bind(on_release=self.button_press)
            self.ids.db_box_layout.add_widget(btn)

#Not tested
class TableScreen(MDScreen):
    def __init__(self, db, **kw):
        super().__init__(**kw)
        self.db = db
        self.last_text = None

    def widget_text_for_create(self, widget):
        return self.create_record(widget.text)

    def widget_text_for_update(self, widget):
        return self.update_table(self.last_text, widget.text, widget.column, widget.value_id)

    def pressed_button(self):
        self.db.save()

    def create_record(self, text):
        self.db.create_record(text)

    def update_table(self, lt, text, row, value):
        self.db.update_table(lt, text, row, value)

    def delete_row(self, value):
        self.db.delete_row(value)

    def on_focus(self, widget):
        self.last_text = widget.text

    def on_enter(self, *args):
        self.ids.table_grid_layout.clear_widgets()
        table = self.db.selected_table
        columns = self.db.get_table_columns(table)
        self.ids.table_grid_layout.cols = len(columns)
        values = self.db.get_table_values(table) or []

        for col in columns:
            self.ids.table_grid_layout.add_widget(MDLabel(text=str(col)))

        for i, row in enumerate(values):
            for j, cell in enumerate(row):
                readonly = (j % 10 == 0)
                w = ValueInput(
                    text=str(cell),
                    multiline=False,
                    value_id=i + 1,
                    column=j,
                    readonly=readonly
                )
                w.bind(focus=lambda inst, f: (not f) or self.on_focus(inst))
                w.bind(on_text_validate=self.widget_text_for_update)
                self.ids.table_grid_layout.add_widget(w)

        for i in range(len(columns)):
            readonly = (i % 10 == 0)
            w = ValueInput(
                text='',
                multiline=False,
                column=i,
                value_id=i + 1,
                readonly=readonly
            )
            w.bind(on_text_validate=self.widget_text_for_create)
            self.ids.table_grid_layout.add_widget(w)
