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

# A bad value should not stop the rest of the bot from starting.
def _optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError:
        print(f"{name} is not an integer. Ignoring it.")
        return None


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"{name} is not an integer. Using {default}.")
        return default
    if value < 1:
        print(f"{name} must be at least 1. Using {default}.")
        return default
    return value


def _owner_ids() -> frozenset[int]:
    raw = os.getenv("OWNER_IDS") or ""
    ids: set[int] = set()
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            ids.add(int(text))
        except ValueError:
            print(f"Skipping owner id {text!r} because it is not an integer.")
    return frozenset(ids)


def _db_path() -> Path:
    # Same root as .env, so a relative BOT_DB_PATH does not follow the shell cwd.
    raw = os.getenv("BOT_DB_PATH")
    if raw is None or not raw.strip():
        raw = "data/bot.db"
    path = Path(raw.strip())
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent.parent / path


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or ""
AI_MODEL = os.getenv("AI_MODEL") or "deepseek/deepseek-v4.1-flash"
AI_DAILY_TOKEN_BUDGET = _positive_int("AI_DAILY_TOKEN_BUDGET", 20000)
AI_REQUESTS_PER_MINUTE = _positive_int("AI_REQUESTS_PER_MINUTE", 10)
AI_HISTORY_DAYS = _positive_int("AI_HISTORY_DAYS", 7)
BOT_DB_PATH = _db_path()
OWNER_IDS = _owner_ids()
DEV_GUILD_ID = _optional_int("DEV_GUILD_ID")

PRIVACY_VOICE_CHANNEL_ID = 1564979389345562756
OVERWRITE_ROLE_ID_1 = 1564494306792964097
OVERWRITE_ROLE_ID_2 = 1564492134952738866
JOIN_ROLE_ID = 1564494948919803954
