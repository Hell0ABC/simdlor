from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.textfield import MDTextField
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDSwitch

"""
TODO:
    
"""

class ConnectForm(BoxLayout):
    engine = StringProperty("MySQL")
    ssl = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        # Выпадающее меню движков
        self._menu = MDDropdownMenu(
            caller=self.ids.engine_btn,
            items=[
                {"text": "MySQL", "on_release": lambda t="MySQL": self._set_engine(t)},
                {"text": "PostgreSQL", "on_release": lambda t="PostgreSQL": self._set_engine(t)},
                {"text": "MSSQL", "on_release": lambda t="MSSQL": self._set_engine(t)},
            ],
            width_mult=3,
        )

    def open_menu(self):
        self._menu.caller = self.ids.engine_btn
        self._menu.open()

    def _set_engine(self, name: str):
        self.engine = name
        self.ids.engine_btn_text.text = name
        self._menu.dismiss()
        # автозаполняем порт по умолчанию
        defaults = {"MySQL": "3306", "PostgreSQL": "5432", "MSSQL": "1433"}
        self.ids.port.text = defaults.get(name, "")

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