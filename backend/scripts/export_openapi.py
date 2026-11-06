"""Write the OpenAPI document to backend/openapi.json (the frontend's API contract)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

OUTPUT = Path(__file__).resolve().parents[1] / "openapi.json"

if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUTPUT}")
