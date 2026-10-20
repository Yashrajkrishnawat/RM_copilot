import os
import sys
from pathlib import Path

# Tests always use the local leads.json, so they never depend on the mock LOS server running.
# Environment variables override .env, so this wins even when .env says LEADS_SOURCE=api.
os.environ["LEADS_SOURCE"] = "json"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))