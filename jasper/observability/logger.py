import json
import uuid
import os
import logging
from datetime import datetime

# Configure a file-based logger so session events are persisted without
# polluting stdout (which would break Rich Live rendering).
_log_dir = os.path.join(os.path.expanduser("~"), ".jasper", "logs")
os.makedirs(_log_dir, exist_ok=True)
_file_logger = logging.getLogger("jasper.session")
if not _file_logger.handlers:
    _handler = logging.FileHandler(os.path.join(_log_dir, "session.log"), encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _file_logger.addHandler(_handler)
    _file_logger.setLevel(logging.DEBUG)
    _file_logger.propagate = False


# --- Session Logger ---
# Provides structured logging for session replay and auditing.
# Writes ONLY to ~/.jasper/logs/session.log — never to stdout —
# so it never interferes with Rich Live terminal rendering.
class SessionLogger:
    def __init__(self):
        self.session_id = str(uuid.uuid4())

    def log(self, event_type: str, payload: dict):
        record = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "payload": payload,
        }
        _file_logger.debug(json.dumps(record))
