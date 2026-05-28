from __future__ import annotations

from app.db import Database
from app.templates.registry import seed_default_workflows


def bootstrap() -> None:
    db = Database()
    db.init()
    seed_default_workflows(db)


if __name__ == "__main__":
    bootstrap()
    print("Initialized Yuno AI orchestration database.")
