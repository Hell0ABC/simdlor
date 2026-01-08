from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.factory import Factory
from kivy.clock import Clock
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivy.logger import Logger
from kivy.app import App

from app.notify import notify

class ConnectForm(BoxLayout):
    engine = StringProperty("MySQL")
    ssl = BooleanProperty(False)
    items = ListProperty(
        [
            {"text": "MySQL", "default_port": "3306"},
            {"text": "PostgreSQL", "default_port": "5432"},
            {"text": "MSSQL", "default_port": "1433"},
        ]
    )
    _menu = None

    def __init__(self, **kw):
        self._menu = None
        super().__init__(**kw)

    def on_kv_post(self, base_widget):
        self._build_menu()

    def on_items(self, *_):
        self._build_menu()

    def _build_menu(self):
        if "engine_btn" not in self.ids:
            return

        menu_entries = []
        for entry in self.items or []:
            data = entry if isinstance(entry, dict) else {"text": str(entry)}
            label = data.get("text", "")
            menu_entries.append(
                {
                    "text": label,
                    "on_release": (lambda *_args, data=data: self._set_engine(data)),
                }
            )

        if self._menu:
            self._menu.dismiss()

        self._menu = MDDropdownMenu(
            caller=self.ids.engine_btn,
            items=menu_entries,
            width_mult=3,
        )

    def open_menu(self):
        if not self._menu:
            self._build_menu()
        if not self._menu:
            return
        self._menu.caller = self.ids.engine_btn
        self._menu.open()

    def _set_engine(self, data):
        if isinstance(data, dict):
            name = data.get("text", "")
            default_port = data.get("default_port")
        else:
            name = str(data)
            default_port = None

        self.engine = name
        self.ids.engine_btn_text.text = name
        if self._menu:
            self._menu.dismiss()

        port = default_port
        if port is None:
            for entry in self.items:
                if isinstance(entry, dict) and entry.get("text") == name:
                    port = entry.get("default_port")
                    if port:
                        break
        if port is None:
            defaults = {"MySQL": "3306", "PostgreSQL": "5432", "MSSQL": "1433"}
            port = defaults.get(name)
        if port is not None:
            self.ids.port.text = str(port)

    def get_values(self):
        return {
            "engine": self.engine,
            "host": self.ids.host.text.strip(),
            "port": int(self.ids.port.text.strip() or 0),
            "database": self.ids.database.text.strip(),
            "user": self.ids.user.text.strip(),
            "password": self.ids.password.text,
            "ssl": self.ids.ssl.active,
        }

class Content(BoxLayout):
    pass

class SearchBar(MDCard):
    hint_text = StringProperty("Search")
    menu_items = ListProperty(
        [
            {"text": "Add table", "action": "Add"},
            {"text": "Save", "action": "Save"},
            {"text": "Home", "action": "Home"},
        ]
    )
    search_menu = ObjectProperty(None)

    def on_kv_post(self, base_widget):
        self._build_search_menu()

    def on_menu_items(self, *_):
        self._build_search_menu()

    def _build_search_menu(self):
        if "menu_btn" not in self.ids:
            return

        menu_entries = []
        for entry in self.menu_items or []:
            if isinstance(entry, dict):
                data = dict(entry)
                if "on_release" not in data:
                    label = data.get("text", "")
                    action = data.get("action", label)
                    data["on_release"] = lambda *_args, action=action: self.menu_action(action)
                menu_entries.append(data)
                continue

            label = str(entry)
            menu_entries.append(
                {
                    "text": label,
                    "on_release": lambda *_args, action=label: self.menu_action(action),
                }
            )

        if self.search_menu:
            self.search_menu.dismiss()

        self.search_menu = MDDropdownMenu(
            caller=self.ids.menu_btn,
            items=menu_entries,
            width=dp(160),
            position="auto",
        )

    def open_search_menu(self, caller=None):
        if not self.search_menu:
            self._build_search_menu()
        if not self.search_menu:
            return
        if caller is None:
            caller = self.ids.get("menu_btn")
        if caller:
            self.search_menu.caller = caller
        self.search_menu.open()

    def menu_action(self, action: str):
        if self.search_menu:
            self.search_menu.dismiss()

        if action == "Add":
            Logger.info("SearchBar: Add action triggered")
            # TODO Table editor implementation
            notify("Not implemented")
            pass
        elif action == "Save":
            Logger.info("SearchBar: Save action triggered")
            app = App.get_running_app()
            db = getattr(app, "db", None)
            if not db:
                Logger.warning("DatabaseScreen: Save action invoked with no database")
                notify("No database selected")
                return

            if hasattr(db, "save"):
                db.save()
                notify("Saved")
            elif hasattr(db, "commit"):
                db.commit()
                notify("Saved")
            else:
                Logger.critical("DatabaseScreen: DB object has no save or commit method")
                notify("Save not supported")

        elif action == "Home":
            Logger.info("SearchBar: Home action triggered")
            app = App.get_running_app()
            manager = getattr(app, "root", None)
            if not manager:
                Logger.error("SearchBar: Screen manager not found")
                return
            manager.transition.direction = "right"
            manager.current = "home"

    def do_search(self, text: str):
        # TODO: implement search functionality
        notify("Not implemented")
        pass

class TableEditorForm(MDBoxLayout):
    db_label = StringProperty("Database\nUnknown")
    # TODO: implement table editor form

class ValueInput(MDTextField):
    def __init__(self, column, value_id, **kw):
        self.column = column
        self.value_id = value_id
        self.background_color = 'red'
        self.mode = 'rectangle'
        super().__init__(**kw)


class TableItem(BoxLayout):
    table_name = StringProperty("")
    on_open = ObjectProperty(lambda *_: None)

    def do_delete_table(self, table: str):
        # TODO implement delete table functionality
        notify("Not implemented")
        pass

    def do_edit_table(self, table: str):
        # TODO implement edit table functionality
        notify("Not implemented")
        pass
