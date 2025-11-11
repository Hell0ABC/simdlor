from kivy.utils import platform

def notify(msg: str, *, duration: float = 1.5):
    # Android toast
    try:
        from kivymd.toast import toast
        toast(msg)
        return
    except Exception:
        pass

    # Modern Snackbar
    try:
        from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
        bar = MDSnackbar(MDSnackbarText(text=msg))
        bar.duration = duration
        bar.open()
        return
    except Exception:
        pass

    # If nothing worked
    try:
        from kivy.logger import Logger
        Logger.warning("NOTIFY: %s", msg)
    except Exception:
        pass
        