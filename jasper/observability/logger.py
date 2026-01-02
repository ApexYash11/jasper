import json
import uuid
from datetime import datetime


# --- Session Logger ---
# Provides structured logging for session replay and auditing
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
        print(json.dumps(record))
