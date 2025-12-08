from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parents[1]
BUILD_TYPE = "debug"
LOG_LEVEL = logging.DEBUG if BUILD_TYPE == "debug" else logging.INFO

KV_DIR  = BASE_DIR / 'ui' / 'kv'
KV_APP  = KV_DIR / 'app.kv'
KV_SCREENS = KV_DIR / 'screens.kv'
KV_WIDGETS = KV_DIR / 'widgets.kv'