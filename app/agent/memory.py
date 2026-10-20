import time
from threading import Lock

MAX_TURNS = 3            # past question/answer pairs sent to the model (keep small for a 4096 context)
MAX_ANSWER_CHARS = 600   # long answers are trimmed before being remembered
TTL_SECONDS = 4 * 60 * 60  # forget a chat after 4 hours of inactivity


class Memory:
    """Per-chat memory kept in server RAM. Lost on restart, which is fine for now."""

    def __init__(self):
        self._sessions = {}
        self._lock = Lock()

    def get(self, session_id, rm_id):
        with self._lock:
            s = self._sessions.get(session_id)
            expired = s and time.time() - s["updated"] > TTL_SECONDS
            if not s or expired or s["rm_id"] != rm_id:
                s = {"rm_id": rm_id, "history": [], "focus": None, "updated": time.time()}
                self._sessions[session_id] = s
            return {"history": list(s["history"]), "focus": s["focus"]}

    def save_turn(self, session_id, user_msg, answer, focus=None):
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s["history"] += [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": answer[:MAX_ANSWER_CHARS]},
            ]
            s["history"] = s["history"][-MAX_TURNS * 2:]
            if focus:
                s["focus"] = focus
            s["updated"] = time.time()

    def clear(self, session_id):
        with self._lock:
            self._sessions.pop(session_id, None)


memory = Memory()