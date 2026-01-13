from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty, NumericProperty
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogContentContainer,
    MDDialogHeadlineText,
)
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivy.uix.widget import Widget
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
            modal = self._get_table_editor_modal()
            if modal:
                modal.open_new_table()
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
        query = (text or "").strip()
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            Logger.warning("SearchBar: Search invoked with no database")
            notify("No database selected")
            return

        manager = getattr(app, "root", None)
        if not manager:
            Logger.error("SearchBar: Screen manager not found")
            return

        try:
            screen = manager.get_screen("database")
        except Exception:
            screen = manager.current_screen

        if not screen or not hasattr(screen, "_refresh_tables"):
            Logger.error("SearchBar: Database screen not available for search")
            return

        if not query:
            screen._refresh_tables(db)
            return

        needle = query.casefold()
        tables = db.list_tables() or []
        filtered = [name for name in tables if needle in str(name).casefold()]
        screen.table_items = [screen._build_table_item(name) for name in filtered]

    def _get_table_editor_modal(self):
        app = App.get_running_app()
        modal = getattr(app, "_table_editor_modal", None)
        if not modal:
            modal = Factory.TableEditorForm()
            app._table_editor_modal = modal
        return modal

class TableEditorForm(ModalView):
    db_label = StringProperty("Table editor")
    table_name = StringProperty("")
    original_table_name = StringProperty("")
    column_items = ListProperty([])
    editing_table = BooleanProperty(False)

    def on_open(self):
        Clock.schedule_once(lambda *_: self._animate_in(), 0)

    def open_new_table(self):
        self.editing_table = False
        self.table_name = ""
        self.original_table_name = ""
        self.db_label = "New table"
        self.column_items = [self._build_column_item()]
        self.open()

    def open_existing_table(self, table_name: str):
        name = (table_name or "").strip()
        if not name:
            self.open_new_table()
            return
        self.editing_table = True
        self.table_name = name
        self.original_table_name = name
        self.db_label = f"Edit table\n{name}"
        self._load_columns(name)
        self.open()

    def close(self):
        content = self.ids.get("content")
        if not content:
            super().dismiss()
            return
        Animation.cancel_all(content)
        anim = Animation(y=-content.height, d=0.22, t="out_quad")
        def _finish(*_):
            content.opacity = 0
            super(TableEditorForm, self).dismiss()
        anim.bind(on_complete=_finish)
        anim.start(content)

    def _animate_in(self):
        content = self.ids.get("content")
        if not content:
            return
        Animation.cancel_all(content)
        content.opacity = 1
        content.y = -content.height
        Animation(y=0, d=0.25, t="out_quad").start(content)

    def add_column(self):
        items = list(self.column_items or [])
        items.append(self._build_column_item())
        self.column_items = items

    def _build_column_item(
        self,
        name: str = "",
        col_type: str = "",
        is_pk: bool = False,
        source_name: str | None = None,
    ):
        return {
            "name": name,
            "col_type": col_type,
            "is_pk": is_pk,
            "source_name": source_name,
        }

    def _load_columns(self, table_name: str):
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            Logger.warning("TableEditorForm: no database selected")
            notify("No database selected")
            self.column_items = [self._build_column_item()]
            return
        try:
            columns = db.describe_table(table_name)
        except Exception:
            Logger.exception("TableEditorForm: failed to load table %s", table_name)
            notify("Could not load table")
            self.column_items = [self._build_column_item()]
            return

        items = []
        for idx, column in enumerate(columns or []):
            col_name = str(column.get("name", ""))
            items.append(
                self._build_column_item(
                    col_name,
                    str(column.get("type", "")),
                    bool(column.get("pk")),
                    col_name,
                )
            )
        if not items:
            items.append(self._build_column_item())
        self.column_items = items

    def save(self):
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            notify("No database selected")
            return

        table_name = (self.table_name or "").strip()
        if not table_name:
            notify("Table name is required")
            return

        columns = self._collect_columns()
        if not columns:
            return

        try:
            if self.editing_table:
                original = (self.original_table_name or table_name).strip() or table_name
                if table_name == original and self._columns_match_db(original, columns):
                    self.close()
                    return
                tables = set(db.list_tables() or [])
                if table_name != original and table_name in tables:
                    notify("Table already exists")
                    return
                if original in tables:
                    db.rebuild_table(original, table_name, columns)
                else:
                    db.create_table(table_name, columns)
            else:
                if table_name in (db.list_tables() or []):
                    notify("Table already exists")
                    return
                db.create_table(table_name, columns)
        except Exception:
            Logger.exception("TableEditorForm: save failed")
            notify("Save failed")
            return

        self._refresh_tables()
        self.close()

    def _collect_columns(self):
        items = []
        seen = set()
        for item in self.column_items or []:
            name = (item.get("name") or "").strip()
            col_type = (item.get("col_type") or "").strip()
            is_pk = bool(item.get("is_pk"))
            source_name = (item.get("source_name") or "").strip() or None

            if not name and not col_type and not is_pk:
                continue
            if not name:
                notify("Column name is required")
                return None
            if not col_type:
                col_type = "TEXT"

            key = name.lower()
            if key in seen:
                notify("Duplicate column name")
                return None
            seen.add(key)

            items.append(
                {
                    "name": name,
                    "type": col_type,
                    "is_pk": is_pk,
                    "source_name": source_name,
                }
            )
        if not items:
            notify("Add at least one column")
            return None
        return items

    def _columns_match_db(self, table_name: str, columns: list[dict]) -> bool:
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            return False
        try:
            current = db.describe_table(table_name) or []
        except Exception:
            return False
        if len(current) != len(columns):
            return False

        for incoming, existing in zip(columns, current):
            if self._normalize_name(incoming.get("name")) != self._normalize_name(existing.get("name")):
                return False
            if self._normalize_type(incoming.get("type")) != self._normalize_type(existing.get("type")):
                return False
            if bool(incoming.get("is_pk")) != bool(existing.get("pk")):
                return False
        return True

    def _normalize_name(self, value) -> str:
        return (value or "").strip().lower()

    def _normalize_type(self, value) -> str:
        text = " ".join(str(value or "").strip().split())
        if not text:
            return "TEXT"
        return text.upper()

    def _refresh_tables(self):
        app = App.get_running_app()
        root = getattr(app, "root", None)
        if not root or not hasattr(root, "get_screen"):
            return
        try:
            screen = root.get_screen("database")
        except Exception:
            return
        if screen and hasattr(screen, "_refresh_tables"):
            screen._refresh_tables()


class ColumnField(RecycleDataViewBehavior, MDBoxLayout):
    index = NumericProperty(-1)
    name = StringProperty("")
    col_type = StringProperty("")
    is_pk = BooleanProperty(False)
    _rv = None
    _updating = False

    def refresh_view_attrs(self, rv, index, data):
        self._rv = rv
        self.index = index
        self._updating = True
        result = super().refresh_view_attrs(rv, index, data)
        self._updating = False
        return result

    def notify_name(self, value: str):
        if self._updating:
            return
        self._update_data("name", value)

    def notify_type(self, value: str):
        if self._updating:
            return
        self._update_data("col_type", value)

    def notify_pk(self, value: bool):
        if self._updating:
            return
        self._update_data("is_pk", value)

    def _update_data(self, field: str, value):
        self._set_property(field, value)
        rv = self._rv
        if not rv:
            return
        if self.index < 0 or self.index >= len(rv.data):
            return
        rv.data[self.index][field] = value

    def _set_property(self, field: str, value):
        if getattr(self, field) == value:
            return
        self._updating = True
        setattr(self, field, value)
        self._updating = False

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
        name = (self.table_name or table or "").strip()
        if not name:
            notify("No table selected")
            return
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            notify("No database selected")
            return
        if not hasattr(db, "drop_table"):
            notify("Delete not supported")
            return
        dialog = getattr(app, "_delete_table_dialog", None)
        label = getattr(app, "_delete_table_label", None)
        if not dialog:
            label = MDLabel(text="", theme_text_color="Secondary")
            dialog = MDDialog(
                MDDialogHeadlineText(text="Delete table?"),
                MDDialogContentContainer(
                    label,
                    orientation="vertical",
                ),
                MDDialogButtonContainer(
                    Widget(),
                    MDButton(
                        MDButtonText(text="Cancel"),
                        style="text",
                        on_release=lambda *_: dialog.dismiss(),
                    ),
                    MDButton(
                        MDButtonText(text="Delete"),
                        style="text",
                        on_release=self._confirm_delete_table,
                    ),
                    spacing="8dp",
                ),
            )
            app._delete_table_dialog = dialog
            app._delete_table_label = label
        app._delete_table_name = name
        if label:
            label.text = f'Delete table "{name}"? This cannot be undone.'
        dialog.open()

    def _confirm_delete_table(self, *_):
        app = App.get_running_app()
        name = (getattr(app, "_delete_table_name", "") or "").strip()
        if not name:
            notify("No table selected")
            return
        dialog = getattr(app, "_delete_table_dialog", None)
        if dialog:
            dialog.dismiss()
        db = getattr(app, "db", None)
        if not db:
            notify("No database selected")
            return
        try:
            db.drop_table(name)
        except Exception:
            Logger.exception("TableItem: failed to delete table %s", name)
            notify("Delete failed")
            return
        if getattr(db, "selected_table", None) == name:
            db.selected_table = None
        root = getattr(app, "root", None)
        if root and hasattr(root, "get_screen"):
            try:
                screen = root.get_screen("database")
            except Exception:
                screen = root.current_screen
            if screen and hasattr(screen, "_refresh_tables"):
                screen._refresh_tables(db)
        notify("Table deleted")

    def do_edit_table(self, table: str):
        modal = self._get_table_editor_modal()
        if not modal:
            return
        modal.open_existing_table(self.table_name or table)

    def _get_table_editor_modal(self):
        app = App.get_running_app()
        modal = getattr(app, "_table_editor_modal", None)
        if not modal:
            modal = Factory.TableEditorForm()
            app._table_editor_modal = modal
        return modal
