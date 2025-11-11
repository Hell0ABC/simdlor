from pathlib import Path

APP_VERSION = '0.2.0'
BASE_DIR = Path(__file__).resolve().parents[1]

KV_DIR  = BASE_DIR / 'ui' / 'kv'
KV_APP  = KV_DIR / 'app.kv'
KV_SCREENS = KV_DIR / 'screens.kv'
KV_WIDGETS = KV_DIR / 'widgets.kv'