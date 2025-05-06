import logging
import json
from datetime import datetime
from pathlib import Path

BUG_LOG_PATH = Path("logs/bug_log.json")

def log_bug(error: Exception, context: dict = None):
    BUG_LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "error": str(error),
        "context": context or {}
    }
    with open(BUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logging.getLogger(__name__).error(f"버그 리포트 기록됨: {entry}") 