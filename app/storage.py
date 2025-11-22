import logging
import os
from functools import lru_cache
from pathlib import Path


Logger = logging.getLogger("storage")


def _log(level_method, msg, *args):
    try:
        from kivy.logger import Logger as KivyLogger  # type: ignore
    except Exception:
        level_method(msg, *args)
    else:
        getattr(KivyLogger, level_method.__name__)(msg, *args)


def _ensure_dir(path: Path) -> Path:
    """Create a directory safely, falling back to the current working dir."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except PermissionError as exc:
        _log(Logger.warning, "Storage: cannot create %s (%s), falling back to cwd", path, exc)
        fallback = Path.cwd() / "simdlor"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


@lru_cache(maxsize=1)
def internal_app_dir() -> Path:
    """Always-writable directory for the app (no extra permissions needed)."""
    base = None
    try:
        from kivy.utils import platform
    except Exception:  # pragma: no cover - kivy not available on desktop tests
        platform = None

    if platform == "android":
        try:
            from android.storage import app_storage_path  # type: ignore

            base = Path(app_storage_path())
        except Exception as exc:
            _log(Logger.warning, "Storage: app_storage_path() failed (%s)", exc)

    if base is None:
        base = Path.home()

    return _ensure_dir(base / "simdlor")


def external_shared_dir() -> Path | None:
    """Disabled external storage (avoid MANAGE_EXTERNAL_STORAGE requirement)."""
    return None


def prepare_environment() -> tuple[Path, Path | None]:
    """
    Pick stable storage locations.

    Returns (internal_dir, external_dir_if_available) and also points $HOME to
    the internal dir to keep libraries from picking an unwritable location.
    """
    internal_dir = internal_app_dir()
    os.environ.setdefault("HOME", str(internal_dir))
    # We deliberately avoid external storage to prevent permission errors.
    return internal_dir, None
