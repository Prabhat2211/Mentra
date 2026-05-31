from __future__ import annotations

import time

from app.db import Database
from app.runtime.graph import run_workflow


def poll() -> None:
    db = Database()
    db.init()
    print("[scheduler] Started. Checking every 60 seconds for due schedules.")
    while True:
        try:
            due = db.get_due_schedules()
            for schedule in due:
                print(f"[scheduler] Running schedule: {schedule['name']} (workflow={schedule['workflow_id'][:8]}...)")
                try:
                    run_workflow(
                        workflow_id=schedule["workflow_id"],
                        user_input=schedule["input_text"] or "Scheduled run",
                        source_channel="scheduler",
                        db=db,
                    )
                    db.mark_schedule_run(schedule["id"])
                    print(f"[scheduler] Completed: {schedule['name']}")
                except Exception as exc:
                    print(f"[scheduler] Failed: {schedule['name']}: {exc}")
        except Exception as exc:
            print(f"[scheduler] Poll error: {exc}")
        time.sleep(60)


def main() -> None:
    poll()


if __name__ == "__main__":
    main()
