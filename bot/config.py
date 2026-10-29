import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TOKEN = os.getenv("TOKEN")

PRIVACY_VOICE_CHANNEL_ID = 1564979389345562756
OVERWRITE_ROLE_ID_1 = 1564494306792964097
OVERWRITE_ROLE_ID_2 = 1564492134952738866
JOIN_ROLE_ID = 1564494948919803954
