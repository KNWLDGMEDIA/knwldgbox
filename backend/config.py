"""
KNWLDGBox — Centralized Path Configuration

Separates read-only application files from writable user data.
In dev mode (running from source), all paths resolve relative to __file__
so existing behavior is preserved. When installed as a package,
user data is stored under XDG_DATA_HOME (Linux) or %APPDATA% (Windows).
"""

import os
import sys
from pathlib import Path


def _is_installed() -> bool:
    """Detect if we're running from a system-installed location."""
    if getattr(sys, 'frozen', False):
        return True

    app_dir = os.path.normcase(str(Path(__file__).resolve().parent))

    # If running from /opt or /usr or a Windows program-files dir, we're installed
    installed_prefixes = ["/opt/", "/usr/"]
    if os.name == 'nt':
        for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            prefix = os.environ.get(env_var)
            if prefix:
                installed_prefixes.append(prefix)
        # Per-user installs (e.g. %LOCALAPPDATA%\Programs\KNWLDGBox)
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            installed_prefixes.append(os.path.join(local_appdata, "Programs"))
        # Fallback if env vars are somehow missing
        installed_prefixes.append("C:\\Program Files")

    return any(
        app_dir.startswith(os.path.normcase(p))
        for p in installed_prefixes if p
    )


def get_app_dir() -> Path:
    """Read-only application directory (where the Python code lives)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """
    Writable per-user data directory.
    - Installed mode: ~/.local/share/knwldgbox (Linux) or %APPDATA%/knwldgbox (Windows)
    - Dev mode: same as APP_DIR (backend/) for backward compatibility
    """
    if not _is_installed():
        # Dev mode: keep everything in the backend/ folder as before
        return get_app_dir()

    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:  # Linux / macOS
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

    data_dir = base / 'knwldgbox'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ── Core directories ──────────────────────────────────────────────

APP_DIR  = get_app_dir()
DATA_DIR = get_data_dir()

# ── Mutable paths (user data / runtime artifacts) ────────────────

ENV_FILE      = DATA_DIR / '.env'
SESSION_NAME  = str(DATA_DIR / 'anon')       # Telethon appends .session automatically
ARCHIVES_DIR  = DATA_DIR / 'archives'
DOWNLOADS_DIR = DATA_DIR / 'data' / 'downloads'
GRAPHS_DIR    = DATA_DIR / 'data' / 'graphs'
MAIGRET_DIR   = DATA_DIR / 'data' / 'maigret'
TIKTOK_DIR    = DATA_DIR / 'data' / 'tiktok'

# Ensure all mutable directories exist at import time
for _d in [ARCHIVES_DIR, DOWNLOADS_DIR, GRAPHS_DIR, MAIGRET_DIR, TIKTOK_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ── Tool resolution ──────────────────────────────────────────────

_BIN_SUBDIR = 'Scripts' if os.name == 'nt' else 'bin'

# Candidate directories that may contain CLI tool shims (sherlock, maigret,
# yt-dlp, holehe, ...), most specific first:
# - backend/venv/(Scripts|bin): legacy bundled-venv layout
# - <install root>/python/Scripts: bundled standalone CPython (Windows installer)
VENV_BIN = APP_DIR / 'venv' / _BIN_SUBDIR
BUNDLED_PYTHON_BIN = APP_DIR.parent / 'python' / _BIN_SUBDIR

# Only directories that actually exist (empty in dev mode → PATH is used)
TOOL_DIRS = [p for p in (VENV_BIN, BUNDLED_PYTHON_BIN) if p.is_dir()]


def tool_path(name: str) -> str:
    """
    Resolve a CLI tool name to its full path inside a bundled environment.
    Falls back to the bare command name (system PATH lookup) in dev mode.
    On Windows, pip shims are '<name>.exe', so try that suffix first.
    """
    candidates = [f"{name}.exe", name] if os.name == 'nt' else [name]
    for directory in TOOL_DIRS:
        for candidate_name in candidates:
            candidate = directory / candidate_name
            if candidate.exists():
                return str(candidate)
    return name  # Fallback: rely on system PATH (dev mode / conda / venv activated)
