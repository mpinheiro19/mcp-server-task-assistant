import logging
import os
from pathlib import Path

CODES_ROOT = Path(os.getenv("ASSISTANT_FLOW_ROOT", Path.home() / "Codes"))
PROJECT_ROOT = Path(os.getenv("ASSISTANT_PROJECT_ROOT", Path.cwd()))
COPILOT_ROOT = CODES_ROOT / "copilot-assistants"
PRDS_DIR = COPILOT_ROOT / "prds"
SPECS_DIR = COPILOT_ROOT / "specs"
PLANS_DIR = COPILOT_ROOT / "plans"
ELICITATIONS_DIR = COPILOT_ROOT / "elicitations"
ELICITATION_MAX_DEPTH = int(os.getenv("ELICITATION_MAX_DEPTH", "3"))
INDEX_FILE = COPILOT_ROOT / "index.md"
COPILOT_INSTRUCTIONS = COPILOT_ROOT / "copilot-instructions.md"
SPEC_ASSISTANT_DIR = COPILOT_ROOT / "spec-driven-assistant"

logger = logging.getLogger(__name__)


def log_config() -> None:
    """Emit the resolved configuration paths at INFO level."""
    logger.info(
        "config codes_root=%s copilot_root=%s prds=%s specs=%s plans=%s "
        "elicitations=%s index=%s elicitation_max_depth=%d",
        CODES_ROOT,
        COPILOT_ROOT,
        PRDS_DIR,
        SPECS_DIR,
        PLANS_DIR,
        ELICITATIONS_DIR,
        INDEX_FILE,
        ELICITATION_MAX_DEPTH,
    )
