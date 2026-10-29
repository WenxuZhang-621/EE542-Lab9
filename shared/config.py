"""Non-secret project defaults. Paths resolve relative to the repository."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/project.json").read_text(encoding="utf-8"))

def project_path(name: str) -> Path:
    return ROOT / CONFIG["paths"][name]
