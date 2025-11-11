from kivy.app import App
from kivymd.uix.label import MDLabel
from ui.widgets import ValueInput
from kivy.properties import ObjectProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogContentContainer,
    MDDialogHeadlineText,
)
from kivymd.uix.button import MDButton, MDButtonText
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.logger import Logger

from ui.widgets import ConnectForm
from app.config import BASE_DIR
from app.notify import notify


class HomeScreen(MDScreen):
    dialog = None
    _connect_form = None

    def on_pre_enter(self, *args):
        # preparing file manager
        if not hasattr(self, "fm"):
            from kivymd.uix.filemanager import MDFileManager
            self.fm = MDFileManager(select_path=self._on_pick, exit_manager=self._on_close)
            Logger.debug("HomeScreen: Initialized file manager for local database selection")
        else:
            Logger.debug("HomeScreen: Reusing existing file manager instance")

    # --- Local ---
    def open_file_manager(self):
        import os
        start_dir = os.path.expanduser(BASE_DIR)
        Logger.debug("HomeScreen: Local DB button pressed (start_dir=%s)", start_dir)
        Logger.info("HomeScreen: Showing local database picker at %s", start_dir)
        self.fm.show(start_dir)

    def _on_close(self, *args):
        self.fm.close()
        Logger.debug("HomeScreen: File manager closed")

    def _on_pick(self, path: str):
        if not path.lower().endswith(".db"):
            Logger.warning("HomeScreen: Rejected non-DB file '%s'", path)
            notify("Pick a *.db file")
            return
        from database.sqlite_connector import Database
        app = App.get_running_app()
        app.db = Database(path)
        self.fm.close()
        self.manager.current = "database"
        Logger.info("Loaded '%s' and switched to database screen", path)

    # --- Remote DB ---
    def open_remote_dialog(self):
        Logger.debug("HomeScreen: Remote DB button pressed")
        Logger.info("HomeScreen: Opening remote database connection dialog")
        if self._connect_form is None:
            Logger.debug("HomeScreen: Creating ConnectForm for remote dialog")
            self._connect_form = ConnectForm()

        if self.dialog is None:
            form_scroll = ScrollView(
                size_hint=(1, None),
                height=dp(360),
                do_scroll_x=False,
                bar_width="2dp",
            )
            form_scroll.add_widget(self._connect_form)

            self.dialog = MDDialog(
                MDDialogHeadlineText(text="Connect to remote DB"),
                MDDialogContentContainer(
                    form_scroll,
                    orientation="vertical",
                ),
                MDDialogButtonContainer(
                    Widget(),
                    MDButton(
                        MDButtonText(text="Cancel"),
                        style="text",
                        on_release=self._cancel_remote_dialog
                    ),
                    MDButton(
                        MDButtonText(text="Connect"),
                        style="text",
                        on_release=self._connect_remote
                    ),
                    spacing="8dp",
                ),
            )
            Logger.debug("HomeScreen: Remote dialog created")
        self.dialog.open()
        Logger.info("HomeScreen: Remote dialog opened")

    def _cancel_remote_dialog(self, *_):
        Logger.debug("HomeScreen: Remote dialog cancel button pressed")
        Logger.info("HomeScreen: Remote dialog cancelled by user")
        if self.dialog:
            self.dialog.dismiss()

    def _connect_remote(self, *_):
        form = self._connect_form
        params = form.get_values()  # dict: {"engine","host","port","user","password","database","ssl"}
        engine = params["engine"]
        app = App.get_running_app()

        Logger.debug("HomeScreen: Connect button pressed for engine '%s'", engine)
        if engine == "MySQL":
            Logger.debug("HomeScreen: Preparing MySQL connection parameters")
            pass
        elif engine == "PostgreSQL":
            Logger.debug("HomeScreen: Preparing PostgreSQL connection parameters")
            pass
        elif engine == "MSSQL":
            Logger.debug("HomeScreen: Preparing MSSQL connection parameters")
            pass
        else:
            Logger.error("HomeScreen: Unsupported engine '%s'", engine)
            notify("Unsupported engine")
            return

        self.dialog.dismiss()
        self.manager.current = "database"
        Logger.info("HomeScreen: Remote DB flow completed; switching to database screen")

class LoadingScreen(MDScreen):
    def on_enter(self):
        current = self.ids.progress_bar.value
        current += 10
        self.ids.progress_bar.value = current
        if self.ids.progress_bar.value == 100:
            self.manager.transition.direction = 'up'

# BROKEN
class DatabaseScreen(MDScreen):
    db = ObjectProperty(None)

    def button_press(self, instance):
        self.manager.transition.direction = 'left'
        self.manager.current = 'table'
        self.db.selected_table = instance.text # TODO 'MDButton' object has no attribute 'text'
        self.db.table_values = self.db.get_table_values(self.db.selected_table)

    def on_enter(self):
        if not self.db:
            self.db = getattr(App.get_running_app(), 'db', None)

        if not self.db:
            self.ids.db_box_layout.clear_widgets()
            self.ids.db_box_layout.add_widget(MDLabel(text="No database selected"))
            return

        self.ids.db_box_layout.clear_widgets()
        for name in self.db.tables:
            btn = MDButton(
                on_release=self.button_press,
                size_hint=(1, None),
                height="48dp",
                pos_hint={"center_x": .5},
            )
            btn.add_widget(MDButtonText(text=str(name)))
            self.ids.db_box_layout.add_widget(btn)

#Not tested
class TableScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
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
        if not self.db:
            self.db = getattr(App.get_running_app(), 'db', None)
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
