import importlib
import sys
import types


def _ensure_module(name: str, *, package: bool = False):
    module = sys.modules.get(name)
    if module is not None:
        return module

    module = types.ModuleType(name)
    if package:
        module.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = module

    if "." in name:
        parent_name, attr = name.rsplit(".", 1)
        parent = _ensure_module(parent_name, package=True)
        setattr(parent, attr, module)

    return module


def _install_kivy_stubs():
    _ensure_module("kivy", package=True)
    _ensure_module("kivy.uix", package=True)

    widget_module = _ensure_module("kivy.uix.widget")

    class Widget:
        def __init__(self, *args, **kwargs):
            self.children = []
            self.ids = {}
            self.manager = kwargs.get("manager")

        def add_widget(self, widget):
            self.children.append(widget)

    widget_module.Widget = Widget

    boxlayout_module = _ensure_module("kivy.uix.boxlayout")

    class BoxLayout(Widget):
        pass

    boxlayout_module.BoxLayout = BoxLayout

    scroll_module = _ensure_module("kivy.uix.scrollview")

    class ScrollView(Widget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.do_scroll_x = kwargs.get("do_scroll_x", True)
            self.do_scroll_y = kwargs.get("do_scroll_y", True)
            self.bar_width = kwargs.get("bar_width")
            self.size_hint = kwargs.get("size_hint")
            self.height = kwargs.get("height")

    scroll_module.ScrollView = ScrollView

    props_module = _ensure_module("kivy.properties")

    def _property(default=None, **_):
        return default

    props_module.BooleanProperty = _property
    props_module.ListProperty = _property
    props_module.StringProperty = _property

    metrics_module = _ensure_module("kivy.metrics")

    def dp(value):
        return value

    metrics_module.dp = dp

    lang_module = _ensure_module("kivy.lang")

    class _Builder:
        @staticmethod
        def load_file(*_args, **_kwargs):
            return None

    lang_module.Builder = _Builder

    resources_module = _ensure_module("kivy.resources")

    def resource_add_path(*_args, **_kwargs):
        return None

    resources_module.resource_add_path = resource_add_path


def _install_kivymd_stubs():
    _ensure_module("kivymd", package=True)
    _ensure_module("kivymd.uix", package=True)

    if "kivy.uix.widget" not in sys.modules:
        importlib.import_module("kivy.uix.widget")
    Widget = sys.modules["kivy.uix.widget"].Widget

    app_module = _ensure_module("kivymd.app")

    if not hasattr(app_module, "MDApp"):
        class _MDAppStub:
            _running_app = None

            def __init__(self, **kwargs):
                self.theme_cls = types.SimpleNamespace(theme_style="Light", primary_palette="Blue")
                _MDAppStub._running_app = self

            @classmethod
            def get_running_app(cls):
                return cls._running_app

            def run(self):
                return None

        app_module.MDApp = _MDAppStub

    MDApp = app_module.MDApp

    label_module = _ensure_module("kivymd.uix.label")

    if not hasattr(label_module, "MDLabel"):
        class MDLabel(Widget):
            def __init__(self, text="", **kwargs):
                super().__init__(**kwargs)
                self.text = text

        label_module.MDLabel = MDLabel

    screen_module = _ensure_module("kivymd.uix.screen")

    if not hasattr(screen_module, "MDScreen"):
        class MDScreen(Widget):
            def __init__(self, *args, **kwargs):
                manager = kwargs.pop("manager", None)
                name = kwargs.pop("name", None)
                super().__init__(*args, **kwargs)
                self.manager = manager
                self.name = name

            def get_running_app(self):
                return MDApp.get_running_app()

        screen_module.MDScreen = MDScreen

    screen_manager_module = _ensure_module("kivymd.uix.screenmanager")

    if not hasattr(screen_manager_module, "MDScreenManager"):
        class MDScreenManager:
            def __init__(self):
                self.screens = []
                self.current = None

            def add_widget(self, screen):
                screen.manager = self
                self.screens.append(screen)

        screen_manager_module.MDScreenManager = MDScreenManager

    dialog_module = _ensure_module("kivymd.uix.dialog")

    class _DialogPart(Widget):
        def __init__(self, *args, **kwargs):
            self.orientation = kwargs.pop("orientation", None)
            self.spacing = kwargs.pop("spacing", None)
            self.padding = kwargs.pop("padding", None)
            super().__init__(**kwargs)
            self.children = list(args)

    if not hasattr(dialog_module, "MDDialog"):
        class MDDialog(_DialogPart):
            def __init__(self, *children, **kwargs):
                super().__init__(*children, **kwargs)
                self.children = list(children)
                self.open_count = 0
                self.dismiss_count = 0

            def open(self):
                self.open_count += 1

            def dismiss(self, *_):
                self.dismiss_count += 1

        dialog_module.MDDialog = MDDialog

    if not hasattr(dialog_module, "MDDialogButtonContainer"):
        class MDDialogButtonContainer(_DialogPart):
            pass

        dialog_module.MDDialogButtonContainer = MDDialogButtonContainer

    if not hasattr(dialog_module, "MDDialogContentContainer"):
        class MDDialogContentContainer(_DialogPart):
            pass

        dialog_module.MDDialogContentContainer = MDDialogContentContainer

    if not hasattr(dialog_module, "MDDialogHeadlineText"):
        class MDDialogHeadlineText(_DialogPart):
            def __init__(self, text="", **kwargs):
                super().__init__(**kwargs)
                self.text = text

        dialog_module.MDDialogHeadlineText = MDDialogHeadlineText

    button_module = _ensure_module("kivymd.uix.button")

    if not hasattr(button_module, "MDButton"):
        class MDButton(Widget):
            def __init__(self, *children, on_release=None, **kwargs):
                style = kwargs.pop("style", None)
                super().__init__(**kwargs)
                self.children = list(children)
                self.on_release = on_release
                self.style = style

            def trigger_release(self):
                if callable(self.on_release):
                    self.on_release(self)

        button_module.MDButton = MDButton

    if not hasattr(button_module, "MDButtonText"):
        class MDButtonText(Widget):
            def __init__(self, text="", **kwargs):
                super().__init__(**kwargs)
                self.text = text

        button_module.MDButtonText = MDButtonText

    textfield_module = _ensure_module("kivymd.uix.textfield")

    if not hasattr(textfield_module, "MDTextField"):
        class MDTextField(Widget):
            def __init__(self, text="", multiline=False, **kwargs):
                super().__init__(**kwargs)
                self.text = text
                self.multiline = multiline

        textfield_module.MDTextField = MDTextField

    menu_module = _ensure_module("kivymd.uix.menu")

    if not hasattr(menu_module, "MDDropdownMenu"):
        class MDDropdownMenu:
            def __init__(self, caller=None, items=None, width_mult=1, **kwargs):
                self.caller = caller
                self.items = items or []
                self.width_mult = width_mult
                self.kwargs = kwargs
                self.was_opened = False

            def open(self):
                self.was_opened = True

            def dismiss(self):
                self.was_opened = False

        menu_module.MDDropdownMenu = MDDropdownMenu

    selection_module = _ensure_module("kivymd.uix.selectioncontrol")

    if not hasattr(selection_module, "MDSwitch"):
        class MDSwitch(Widget):
            def __init__(self, active=False, **kwargs):
                super().__init__(**kwargs)
                self.active = active

        selection_module.MDSwitch = MDSwitch

    filemanager_module = _ensure_module("kivymd.uix.filemanager")

    if not hasattr(filemanager_module, "MDFileManager"):
        class MDFileManager:
            def __init__(self, select_path=None, exit_manager=None, **kwargs):
                self.select_path = select_path
                self.exit_manager = exit_manager
                self.kwargs = kwargs
                self.shown_directory = None
                self.closed = False

            def show(self, directory):
                self.shown_directory = directory

            def close(self, *_):
                self.closed = True

        filemanager_module.MDFileManager = MDFileManager

    toast_module = _ensure_module("kivymd.toast")

    if not hasattr(toast_module, "toast"):
        def toast(message):
            toast_module.last_message = message

        toast_module.toast = toast
        toast_module.last_message = None


try:
    import kivy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    _install_kivy_stubs()

try:
    import kivymd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pass

_install_kivymd_stubs()
