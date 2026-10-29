"""Run from repo root: python -m webapp.backend.run."""
import os
from dotenv import load_dotenv
import uvicorn
from shared.config import CONFIG, ROOT

def main():
    load_dotenv(ROOT / ".env")
    uvicorn.run(
        "webapp.backend.app:app",
        host=os.getenv("APP_HOST", CONFIG["services"]["host"]),
        port=int(os.getenv("APP_PORT", CONFIG["services"]["web_port"])),
    )

if __name__ == "__main__":
    main()
