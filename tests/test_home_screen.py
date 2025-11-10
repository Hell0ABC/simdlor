import os
import sys
import types

from database import sqlite_connector
from kivy.uix.widget import Widget

import ui.screens as screens
from ui.screens import HomeScreen


def test_on_pre_enter_initializes_file_manager_once(monkeypatch):
    creations = []

    class FakeManager:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            creations.append(self)

        def show(self, *_):
            pass

        def close(self, *_):
            pass

    filemanager_module = sys.modules["kivymd.uix.filemanager"]
    monkeypatch.setattr(filemanager_module, "MDFileManager", FakeManager)

    screen = HomeScreen(name="home")
    screen.on_pre_enter()
    screen.on_pre_enter()

    assert len(creations) == 1
    assert screen.fm is creations[0]


def test_open_file_manager_uses_base_dir(monkeypatch):
    screen = HomeScreen(name="home")

    class StubFileManager:
        def __init__(self):
            self.shown = None

        def show(self, directory):
            self.shown = directory

    screen.fm = StubFileManager()
    monkeypatch.setattr(screens, "BASE_DIR", "~/databases")

    screen.open_file_manager()

    expected = os.path.expanduser("~/databases")
    assert screen.fm.shown == expected


def test_on_pick_rejects_non_db_and_shows_toast(monkeypatch):
    screen = HomeScreen(name="home")
    messages = []
    screen._toast = messages.append

    class StubFileManager:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    screen.fm = StubFileManager()
    screen.manager = types.SimpleNamespace(current="home")

    screen._on_pick("not_a_db.txt")

    assert messages == ["Pick a *.db file"]
    assert screen.fm.closed is False
    assert screen.manager.current == "home"


def test_on_pick_accepts_db_and_switches_screen(monkeypatch):
    screen = HomeScreen(name="home")

    class StubFileManager:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    screen.fm = StubFileManager()
    screen.manager = types.SimpleNamespace(current="home")

    app = types.SimpleNamespace(repo=None)
    screen.get_running_app = lambda: app

    created = []

    class FakeDatabase:
        def __init__(self, path):
            self.path = path
            created.append(self)

    monkeypatch.setattr(sqlite_connector, "Database", FakeDatabase)

    screen._on_pick("my_database.db")

    assert app.repo is created[0]
    assert created[0].path == "my_database.db"
    assert screen.fm.closed is True
    assert screen.manager.current == "database"


def test_open_remote_dialog_reuses_dialog_and_form(monkeypatch):
    forms = []

    class FakeForm(Widget):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            forms.append(self)

        def get_values(self):
            return {}

    dialogs = []

    class FakeDialog:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.open_calls = 0
            dialogs.append(self)

        def open(self):
            self.open_calls += 1

    monkeypatch.setattr(screens, "ConnectForm", FakeForm)
    monkeypatch.setattr(screens, "MDDialog", FakeDialog)

    screen = HomeScreen(name="home")
    screen.open_remote_dialog()
    screen.open_remote_dialog()

    assert len(forms) == 1
    assert len(dialogs) == 1
    assert dialogs[0].open_calls == 2


def test_connect_remote_supported_engine_dismisses_dialog_and_navigates():
    screen = HomeScreen(name="home")
    screen._connect_form = types.SimpleNamespace(get_values=lambda: {"engine": "MySQL"})

    class FakeDialog:
        def __init__(self):
            self.dismissed = False

        def dismiss(self):
            self.dismissed = True

    screen.dialog = FakeDialog()
    screen.manager = types.SimpleNamespace(current="home")
    screen.get_running_app = lambda: object()

    screen._connect_remote()

    assert screen.dialog.dismissed is True
    assert screen.manager.current == "database"


def test_connect_remote_unsupported_engine_shows_toast_and_stops():
    screen = HomeScreen(name="home")
    screen._connect_form = types.SimpleNamespace(get_values=lambda: {"engine": "DB2"})
    screen.manager = types.SimpleNamespace(current="home")

    class FakeDialog:
        def __init__(self):
            self.dismissed = False

        def dismiss(self):
            self.dismissed = True

    screen.dialog = FakeDialog()
    messages = []
    screen._toast = messages.append

    screen._connect_remote()

    assert messages == ["Unsupported engine"]
    assert screen.dialog.dismissed is False
    assert screen.manager.current == "home"
