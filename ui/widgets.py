from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.textfield import MDTextField
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDSwitch

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


class ValueInput(MDTextField):
    def __init__(self, column, value_id, **kw):
        self.column = column
        self.value_id = value_id
        self.background_color = 'red'
        self.mode = 'rectangle'
        super().__init__(**kw)
