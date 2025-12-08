import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from app.storage import internal_app_dir

try:
    from kivy.logger import Logger as KivyLogger  # type: ignore
except Exception:  # pragma: no cover - desktop fallback
    KivyLogger = None

Logger = logging.getLogger("file_picker")
if not Logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))
    Logger.addHandler(handler)
Logger.setLevel(logging.INFO)


def _log(level_method, msg, *args):
    level_map = {
        logging.Logger.debug: "debug",
        logging.Logger.info: "info",
        logging.Logger.warning: "warning",
        logging.Logger.error: "error",
        logging.Logger.exception: "exception",
    }
    level_name = level_map.get(level_method)
    
    if level_name:
        if KivyLogger:
            getattr(KivyLogger, level_name)(msg, *args)
        else:
            level_method(msg, *args)


def is_android() -> bool:
    try:
        from kivy.utils import platform  # type: ignore
    except Exception:  # pragma: no cover - desktop fallback
        return False
    return platform == "android"


@dataclass
class PickResult:
    path: Path | None
    error: str | None = None
    cancelled: bool = False


class AndroidDatabasePicker:
    """
    SAF-based database picker for Android 11+.

    Uses ACTION_OPEN_DOCUMENT to let the user pick a file from Downloads or
    any other shared storage location, then copies it into our internal
    app directory so the DB can be opened without elevated permissions.
    """

    REQUEST_CODE = 42

    def __init__(self) -> None:
        if not is_android():
            raise RuntimeError("AndroidDatabasePicker can only be used on Android")
        self._callback: Callable[[PickResult], None] | None = None

    def pick(self, callback: Callable[[PickResult], None]) -> None:
        """
        Launch the Android file picker. The callback receives PickResult.
        """
        from android import activity  # type: ignore
        from jnius import autoclass  # type: ignore

        self._callback = callback
        activity.bind(on_activity_result=self._on_activity_result)

        Intent = autoclass("android.content.Intent")
        intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.setType("*/*")
        mime_types: Sequence[str] = (
            "application/x-sqlite3",
            "application/octet-stream",
            "application/vnd.sqlite3",
        )
        intent.putExtra(Intent.EXTRA_MIME_TYPES, list(mime_types))
        intent.addFlags(
            Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
        )

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        _log(Logger.info, "FilePicker: launching SAF chooser (request=%s)", self.REQUEST_CODE)
        PythonActivity.mActivity.startActivityForResult(intent, self.REQUEST_CODE)

    def _on_activity_result(self, request_code, result_code, intent):
        from android import activity  # type: ignore
        from jnius import autoclass  # type: ignore

        if request_code != self.REQUEST_CODE:
            return

        activity.unbind(on_activity_result=self._on_activity_result)
        callback = self._callback
        self._callback = None
        if callback is None:
            return

        Activity = autoclass("android.app.Activity")
        if intent is None or result_code != Activity.RESULT_OK:
            _log(Logger.info, "FilePicker: user cancelled or no intent returned")
            callback(PickResult(path=None, cancelled=True))
            return

        uri = intent.getData()
        try:
            path = self._copy_to_internal(uri)
            callback(PickResult(path=path))
        except Exception as exc:  # pragma: no cover - runtime-only
            _log(Logger.exception, "FilePicker: failed to import file (%s)", exc)
            callback(PickResult(path=None, error=str(exc)))

    def _copy_to_internal(self, uri) -> Path:
        """
        Persist read permission and copy the selected document to a stable path.
        """
        from jnius import autoclass, jarray  # type: ignore

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        OpenableColumns = autoclass("android.provider.OpenableColumns")
        BufferedInputStream = autoclass("java.io.BufferedInputStream")

        activity = PythonActivity.mActivity
        cr = activity.getContentResolver()

        flags = Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
        cr.takePersistableUriPermission(uri, flags)

        display_name = self._get_display_name(cr, uri, OpenableColumns)
        if not display_name:
            display_name = f"imported-{int(time.time())}.db"
        elif not display_name.lower().endswith(".db"):
            display_name = f"{display_name}.db"

        target = internal_app_dir() / display_name
        _log(Logger.info, "FilePicker: copying %s to %s", display_name, target)

        stream = BufferedInputStream(cr.openInputStream(uri))
        buffer = jarray("b", 64 * 1024)
        with open(target, "wb") as dst:
            while True:
                read = stream.read(buffer)
                if read == -1:
                    break
                dst.write(bytes(buffer[:read]))
        stream.close()
        return target

    @staticmethod
    def _get_display_name(cr, uri, OpenableColumns) -> str | None:
        cursor = cr.query(uri, None, None, None, None)
        if cursor is None:
            return None
        try:
            name_idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if name_idx == -1:
                return None
            if not cursor.moveToFirst():
                return None
            return cursor.getString(name_idx)
        finally:
            cursor.close()
