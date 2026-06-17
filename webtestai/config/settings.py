"""Configurações globais carregadas do arquivo .env"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env da pasta config/
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

# Garante UTF-8 no stdout/stderr (necessário no Windows com cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── API ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Browser ──────────────────────────────────────────
DEFAULT_BROWSER: str  = os.getenv("DEFAULT_BROWSER", "chromium")
BROWSER_CHANNEL: str  = os.getenv("BROWSER_CHANNEL", "")
HEADLESS: bool        = os.getenv("HEADLESS", "true").lower() == "true"
PAGE_TIMEOUT: int     = int(os.getenv("PAGE_TIMEOUT", "30"))

# ── Scraper ──────────────────────────────────────────
MAX_ELEMENTS_PER_TYPE: int = int(os.getenv("MAX_ELEMENTS_PER_TYPE", "40"))

# ── Paths ─────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── AI Model ─────────────────────────────────────────
AI_MODEL      = "gemini-2.5-flash"
AI_MAX_TOKENS = 32768
