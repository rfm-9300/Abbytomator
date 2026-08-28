from __future__ import annotations

import os
from pathlib import Path

_brew_lib = Path("/opt/homebrew/lib")
if _brew_lib.is_dir():
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if str(_brew_lib) not in current.split(os.pathsep):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            f"{_brew_lib}{os.pathsep}{current}" if current else str(_brew_lib)
        )

from dotenv import load_dotenv

ROOT = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[2]))
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = (ROOT / DATA_DIR).resolve()
else:
    DATA_DIR = DATA_DIR.resolve()

DB_PATH = DATA_DIR / "abbitomator.db"
REPORTS_DIR = DATA_DIR / "reports"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

WEB_DIST = Path(os.environ.get("WEB_DIST", ROOT / "web" / "dist"))
SEED_IF_EMPTY = os.environ.get("SEED_IF_EMPTY", "1").strip().lower() not in {"0", "false", "no"}

CLIENT_SLUG = "stuart-mitchell"
ACCOUNT_MANAGER = "Abby"


def dashboard_credentials() -> tuple[str, str]:
    user = os.environ.get("DASHBOARD_USER", "").strip()
    password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
    return user, password


def _env_file_value(name: str) -> str:
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'").strip('"')
    return os.environ.get(name, "").strip()


def openrouter_api_key() -> str:
    return _env_file_value("OPENROUTER_API_KEY")


def openrouter_model() -> str:
    return _env_file_value("OPENROUTER_MODEL") or "openai/gpt-4o"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
