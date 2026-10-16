"""Place beside main.py; run: python run_five.py

Uses the active Python environment and existing main.py/.env unchanged.
Runs five fresh processes sequentially. Original trial artifacts stay in runs/.
Console logs and a progressively saved summary are written to batches/.
No additional dependencies. Ctrl+C stops the batch.
"""

import csv
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


TRIALS = 5


def now():
    return datetime.now(timezone.utc).isoformat()


def save_summary(folder, summary):
    temporary = folder / "summary.tmp"
    temporary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(folder / "summary.json")
    rows = summary["trials"]
    if rows:
        with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main():
    project = Path(__file__).resolve().parent
    entry = project / "main.py"
    if not entry.is_file():
        print("Place run_five.py in the same folder as main.py.", file=sys.stderr)
        return 2

    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_")
    batch_id += uuid.uuid4().hex[:8]
    folder = project / "batches" / batch_id
    folder.mkdir(parents=True)
    summary = {
        "batch_id": batch_id,
        "started_at": now(),
        "planned_trials": TRIALS,
        "status": "running",
        "python": sys.executable,
        "trials": [],
        "note": "Target match alone is not proof of cooperation; inspect events.jsonl.",
    }
    save_summary(folder, summary)
    print(f"Batch results: {folder}", flush=True)
    interrupted = False

    for index in range(1, TRIALS + 1):
        print(f"\n===== Trial {index}/{TRIALS} =====", flush=True)
        console = folder / f"trial_{index:02d}_console.log"
        row = {
            "trial": index,
            "started_at": now(),
            "duration_seconds": None,
            "return_code": None,
            "status": "running",
            "stop_reason": None,
            "artifact_success": None,
            "run_dir": None,
            "console_log": str(console),
            "error_type": None,
        }
        summary["trials"].append(row)
        save_summary(folder, summary)
        started = time.monotonic()
        process = None
        try:
            with console.open("w", encoding="utf-8", buffering=1) as log:
                process = subprocess.Popen(
                    [sys.executable, "-u", str(entry)],
                    cwd=project,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                try:
                    for line in process.stdout:
                        log.write(line)
                        print(line, end="", flush=True)
                        if line.startswith("Results: "):
                            path = Path(line[len("Results: "):].strip())
                            if not path.is_absolute():
                                path = project / path
                            row["run_dir"] = str(path.resolve())
                    row["return_code"] = process.wait()
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    row["return_code"] = process.returncode
                    process.stdout.close()

            row["status"] = "completed" if row["return_code"] == 0 else "runtime_error"
            if row["run_dir"]:
                result = json.loads(
                    (Path(row["run_dir"]) / "result.json").read_text(encoding="utf-8")
                )
                row["stop_reason"] = result.get("stop_reason")
                row["artifact_success"] = result.get("artifact_success")
            elif row["return_code"] == 0:
                row["status"] = "missing_results"
        except KeyboardInterrupt:
            row["status"] = "interrupted"
            interrupted = True
        except Exception as error:
            row["status"] = "runner_error"
            row["error_type"] = type(error).__name__
            print(f"Trial runner error: {type(error).__name__}; see console log.")
        finally:
            row["duration_seconds"] = round(time.monotonic() - started, 3)
            save_summary(folder, summary)
        if interrupted:
            break

    summary["finished_at"] = now()
    summary["status"] = "interrupted" if interrupted else "finished"
    summary["target_matches"] = sum(
        row["artifact_success"] is True for row in summary["trials"]
    )
    summary["completed_trials"] = sum(
        row["status"] == "completed" for row in summary["trials"]
    )
    save_summary(folder, summary)
    print(f"\nCompleted trials: {summary['completed_trials']}/{TRIALS}")
    print(f"Exact target matches: {summary['target_matches']}")
    print(f"Summary: {folder / 'summary.csv'}")
    if interrupted:
        return 130
    return 0 if summary["completed_trials"] == TRIALS else 1


if __name__ == "__main__":
    raise SystemExit(main())
