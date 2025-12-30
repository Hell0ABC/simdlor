from kivy.app import App
from kivymd.uix.label import MDLabel
from ui.widgets import ValueInput
from kivy.properties import BooleanProperty, ListProperty, StringProperty
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
from kivy.animation import Animation
from kivy.factory import Factory
from kivy.clock import Clock

from ui.widgets import ConnectForm
from app.config import BASE_DIR
from app.file_picker import AndroidDatabasePicker, PickResult, is_android
from app.notify import notify


class HomeScreen(MDScreen):
    dialog = None
    _connect_form = None

    def on_pre_enter(self, *args):
        # preparing file manager or SAF picker
        if is_android():
            if not hasattr(self, "_android_picker"):
                try:
                    self._android_picker = AndroidDatabasePicker()
                    Logger.debug("HomeScreen: SAF picker ready for Android")
                except Exception as exc:
                    Logger.exception("HomeScreen: failed to init SAF picker (%s)", exc)
        elif not hasattr(self, "fm"):
            from kivymd.uix.filemanager import MDFileManager
            self.fm = MDFileManager(select_path=self._on_pick, exit_manager=self._on_close)
            Logger.debug("HomeScreen: Initialized file manager for local database selection")
        else:
            Logger.debug("HomeScreen: Reusing existing file manager instance")

    # --- Local ---
    def open_file_manager(self):
        if is_android():
            Logger.debug("HomeScreen: Local DB button pressed (Android SAF)")
            try:
                picker = getattr(self, "_android_picker")
            except AttributeError:
                notify("Cannot open file picker")
                Logger.error("HomeScreen: SAF picker is not available")
                return
            Logger.info("HomeScreen: Launching SAF picker for local database")
            picker.pick(self._on_android_pick)
            return

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
        self.fm.close()
        self._load_local_database(path)

    def _on_android_pick(self, result: PickResult):
        if result.cancelled:
            Logger.info("HomeScreen: SAF picker cancelled by user")
            notify("Cancelled")
            return
        if result.error:
            Logger.error("HomeScreen: SAF picker failed (%s)", result.error)
            notify("Could not import file")
            return
        if not result.path:
            Logger.error("HomeScreen: SAF picker returned no path")
            notify("Could not import file")
            return
        self._load_local_database(str(result.path))

    def _load_local_database(self, path: str):
        from database.sqlite_connector import Database
        app = App.get_running_app()
        app.db = Database(path)
        self.manager.current = "database"
        Logger.info("HomeScreen: Loaded '%s' and switched to database screen", path)

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


class DatabaseScreen(MDScreen):
    table_items = ListProperty([])
    db_label = StringProperty("Database\nUnknown")
    fab_open = BooleanProperty(False)
    _add_table_dialog = None

    def on_enter(self, *args):
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            self.table_items = []
            return

        db_path = getattr(db, "db_path", None)
        if db_path:
            db_name = db_path.name
        else:
            db_name = "Database"
        db_type = "SQLite" if db.__class__.__module__.endswith("sqlite_connector") else db.__class__.__name__
        self.db_label = f"{db_name}\n{db_type}"

        self._refresh_tables(db)

    def _refresh_tables(self, db=None):
        if db is None:
            app = App.get_running_app()
            db = getattr(app, "db", None)
            if not db:
                self.table_items = []
                return
        tables = db.list_tables() or []
        self.table_items = [self._build_table_item(name) for name in tables]

    def _build_table_item(self, table_name):
        name = str(table_name)
        return {
            "table_name": name,
            "on_open": lambda *_: self._open_table(name),
        }

    def _open_table(self, table_name):
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            notify("No database selected")
            return
        db.selected_table = table_name
        self.manager.transition.direction = "left"
        self.manager.current = "table"

    def _anim_to(self, widget, *, x=None, y=None, opacity=None, enable=None, d=0.18, t="out_quad"):
        anim = Animation(d=d, t=t)
        if x is not None or y is not None:
            anim &= Animation(x=x if x is not None else widget.x,
                              y=y if y is not None else widget.y, d=d, t=t)
        if opacity is not None:
            anim &= Animation(opacity=opacity, d=d, t=t)
        if enable is not None:
            def _set(*_): widget.disabled = not enable
            anim.bind(on_complete=lambda *_: _set())
            if not enable:
                widget.disabled = True
            else:
                widget.disabled = False
        anim.start(widget)

    def toggle_fab_menu(self):
        fab = self.ids.fab_menu
        gap = dp(70)

        if not self.fab_open:
            # initialize wrappers at the FAB position/size so animation starts from the menu
            for i, btn in enumerate((self.ids.fab_new_table_btn, self.ids.fab_edit_btn, self.ids.fab_save_btn), start=1):
                try:
                    btn.size = fab.size
                    btn.pos = fab.pos
                    btn.opacity = 0
                    btn.disabled = True
                except Exception:
                    pass

            self._anim_to(self.ids.fab_new_table_btn, x=fab.x, y=fab.y + gap*1, opacity=1, enable=True)
            self._anim_to(self.ids.fab_edit_btn, x=fab.x, y=fab.y + gap*2, opacity=1, enable=True, d=0.22)
            self._anim_to(self.ids.fab_save_btn, x=fab.x, y=fab.y + gap*3, opacity=1, enable=True, d=0.26)
            self.fab_open = True
        else:
            for btn in (self.ids.fab_new_table_btn, self.ids.fab_edit_btn, self.ids.fab_save_btn):
                self._anim_to(btn, x=fab.x, y=fab.y, opacity=0, enable=False, d=0.18)
            self.fab_open = False

    def close_fab_menu(self):
        self.fab_open = False

    def action_new_table(self):
        Logger.debug("DatabaseScreen: New table action triggered")
        if self._add_table_dialog is None:
            # Create the TableRedactorForm from KV and wrap into dialog
            content = Factory.TableRedactorForm()
            try:
                content.db_label = self.db_label
            except Exception:
                pass
            # start hidden for animation
            content.opacity = 0
            try:
                # nudge down a bit to animate upwards
                content.y = content.y - 24
            except Exception:
                pass

            self._add_table_dialog = MDDialog(
                MDDialogHeadlineText(text="Create table"),
                MDDialogContentContainer(content, orientation="vertical"),
                MDDialogButtonContainer(
                    Widget(),
                    MDButton(MDButtonText(text="Cancel"), style="text", on_release=lambda *_: self._dismiss_add_table_dialog()),
                    MDButton(MDButtonText(text="Create"), style="text", on_release=lambda *_: self._create_table(content)),
                    spacing="8dp",
                ),
            )

        self._add_table_dialog.open()

        # animate content into view on next frame (ensure layouted)
        def _anim(dt):
            try:
                content = self._add_table_dialog.content_cls.children[0]
            except Exception:
                content = None
            if content:
                anim = Animation(opacity=1, d=0.22, t="out_quad") + Animation(y=content.y + 24, d=0.18, t="out_quad")
                anim.start(content)

        Clock.schedule_once(_anim, 0.06)

    def action_home(self):
        if self.manager:
            Logger.debug("DatabaseScreen: Navigating to home screen")
            self.manager.transition.direction = "right"
            self.manager.current = "home"

    def action_save(self):
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


    def handle_fab_action(self, action):
        self.close_fab_menu()
        if action == "home":
            self.go_home()
        elif action == "add":
            self.open_add_table_dialog()
        elif action == "save":
            self.save_changes()

    def _dismiss_add_table_dialog(self):
        if self._add_table_dialog:
            self._add_table_dialog.dismiss()

    def _create_table(self, form):
        app = App.get_running_app()
        db = getattr(app, "db", None)
        if not db:
            notify("No database selected")
            return


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
