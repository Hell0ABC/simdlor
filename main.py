from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screenmanager import MDScreenManager
from kivy.resources import resource_add_path
from kivy.logger import Logger

from ui.screens import LoadingScreen, TableScreen, DatabaseScreen, HomeScreen
from app.config import KV_DIR, KV_APP, KV_SCREENS, KV_WIDGETS, BUILD_TYPE, LOG_LEVEL, APP_VERSION

__version__ = str(APP_VERSION)

class DatabaseApp(MDApp):

    def build(self):
        self.db = None
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        Logger.setLevel(LOG_LEVEL)
        Logger.info("Main: App starting. build_type=%s, version=%s", BUILD_TYPE, __version__)
        
        resource_add_path(str(KV_DIR))
        if KV_WIDGETS.exists():
            Builder.load_file(str(KV_WIDGETS))
        if KV_SCREENS.exists():
            Builder.load_file(str(KV_SCREENS))
        Builder.load_file(str(KV_APP))

        sm = MDScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(DatabaseScreen(name='database'))
        sm.add_widget(TableScreen(name='table'))
        return sm
    
    def on_stop(self):
        if self.db and getattr(self.db, "db", None):
            self.db.db.close()


if __name__ == '__main__':
    DatabaseApp().run()
