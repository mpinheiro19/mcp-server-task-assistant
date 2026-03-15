import os
from pathlib import Path

CODES_ROOT = Path(os.getenv("ASSISTANT_FLOW_ROOT", "/home/mpinheiro19/Codes"))
COPILOT_ROOT = CODES_ROOT / "copilot-assistants"
PRDS_DIR = COPILOT_ROOT / "prds"
SPECS_DIR = COPILOT_ROOT / "specs"
PLANS_DIR = COPILOT_ROOT / "plans"
INDEX_FILE = COPILOT_ROOT / "index.md"
COPILOT_INSTRUCTIONS = COPILOT_ROOT / "copilot-instructions.md"
SPEC_ASSISTANT_DIR = COPILOT_ROOT / "spec-driven-assistant"
