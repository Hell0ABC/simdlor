from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screenmanager import MDScreenManager
from kivy.resources import resource_add_path

from database import sqlite_connector
from ui.screens import LoadingScreen, TableScreen, DatabaseScreen, HomeScreen
from app.config import KV_DIR, KV_APP, KV_SCREENS, KV_WIDGETS

class DatabaseApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        resource_add_path(str(KV_DIR))
        if KV_WIDGETS.exists():
            Builder.load_file(str(KV_WIDGETS))
        if KV_SCREENS.exists():
            Builder.load_file(str(KV_SCREENS))
        Builder.load_file(str(KV_APP))
        
        sm = MDScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        return sm


if __name__ == '__main__':
    DatabaseApp().run()
