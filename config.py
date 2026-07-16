"""Central configuration. Real config, not hardcoded values scattered across agents."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
SKILLS_FILE = ROOT / "skills" / "learned_rules.json"
RUNS_DIR = ROOT / "runs"

# --- LLM (OpenAI-compatible: works with OpenAI or OpenRouter) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_ENABLED = bool(OPENAI_API_KEY)  # falls back to rule-based logic when False

# --- Demo reference date. Age/expiry is computed relative to this. ---
RUN_DATE = os.getenv("RUN_DATE", "2026-07-17")

# --- Risk model constants (deterministic, auditable) ---
# Condition degrades the effective safe window. Grounded in the seed learned rule R-001.
CONDITION_FACTOR = {"Excellent": 1.1, "Good": 1.0, "Fair": 0.6, "Poor": 0.4}

# Urgency tiers by hours until unsafe to distribute.
def urgency_tier(hours: float) -> str:
    if hours <= 24:
        return "CRITICAL"
    if hours <= 48:
        return "HIGH"
    if hours <= 72:
        return "MEDIUM"
    return "LOW"

# A lot is "at risk" if it cannot clear through current network velocity before it
# goes unsafe, OR it has <= this many days of safe window left.
AT_RISK_DAYS_BUFFER = 1.5
