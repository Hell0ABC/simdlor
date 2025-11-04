from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
#DB_PATH = BASE_DIR / 'hospital.db'

KV_DIR  = BASE_DIR / 'ui' / 'kv'
KV_APP  = KV_DIR / 'app.kv'
KV_SCREENS = KV_DIR / 'screens.kv'
KV_WIDGETS = KV_DIR / 'widgets.kv'