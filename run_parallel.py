"""Run N independent arena trials, with at most 5 active at once.

Place beside main.py and run: python run_parallel.py
Uses the active Python interpreter and existing .env/configuration.
No extra dependencies. API retries remain configured in agents.py.
Ctrl+C stops active trials and cancels queued trials; completed logs remain.
"""
import asyncio
import csv
import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TOTAL_TRIALS = 30
MAX_PARALLEL = 10


def now():
    return datetime.now(timezone.utc).isoformat()


def save(folder, summary):
    rows = summary['trials']
    summary['completed_trials'] = sum(r['status'] == 'completed' for r in rows)
    summary['target_matches'] = sum(r['artifact_success'] is True for r in rows)
    tmp = folder / 'summary.tmp'
    tmp.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(folder / 'summary.json')
    with (folder / 'summary.csv').open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


async def stop_process(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def run_batch(project, folder, summary):
    semaphore = asyncio.Semaphore(MAX_PARALLEL)

    async def trial(row):
        async with semaphore:
            index = row['trial']
            row.update(status='running', started_at=now())
            save(folder, summary)
            print(f"[Trial {index:02d}/{TOTAL_TRIALS}] START", flush=True)
            started = time.monotonic()
            process = None
            try:
                with Path(row['console_log']).open('w', encoding='utf-8', buffering=1) as log:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, '-u', str(project / 'main.py'),
                        cwd=str(project), stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        start_new_session=(os.name == 'posix'),
                        limit=1024 * 1024,
                    )
                    while True:
                        raw = await process.stdout.readline()
                        if not raw:
                            break
                        line = raw.decode('utf-8', errors='replace')
                        log.write(line)
                        print(f'[Trial {index:02d}] {line}', end='', flush=True)
                        if line.startswith('Results: '):
                            path = Path(line[len('Results: '):].strip())
                            row['run_dir'] = str((project / path).resolve())
                    row['return_code'] = await process.wait()
                row['status'] = 'completed' if row['return_code'] == 0 else 'runtime_error'
                if row['run_dir']:
                    result = json.loads((Path(row['run_dir']) / 'result.json').read_text(encoding='utf-8'))
                    row['stop_reason'] = result.get('stop_reason')
                    row['artifact_success'] = result.get('artifact_success')
                elif row['return_code'] == 0:
                    row['status'] = 'missing_results'
            except asyncio.CancelledError:
                row['status'] = 'interrupted'
                raise
            except Exception as error:
                row['status'] = 'runner_error'
                row['error_type'] = type(error).__name__
                print(f'[Trial {index:02d}] Runner error: {type(error).__name__}', flush=True)
            finally:
                if process is not None:
                    await stop_process(process)
                    row['return_code'] = process.returncode
                row['duration_seconds'] = round(time.monotonic() - started, 3)
                row['finished_at'] = now()
                save(folder, summary)
                print(f"[Trial {index:02d}] {row['status']} | target_match={row['artifact_success']}", flush=True)

    tasks = [asyncio.create_task(trial(row)) for row in summary['trials']]
    try:
        await asyncio.gather(*tasks)
        summary['status'] = 'finished'
    except asyncio.CancelledError:
        summary['status'] = 'interrupted'
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        for row in summary['trials']:
            if row['status'] == 'queued':
                row['status'] = 'cancelled'
        summary['finished_at'] = now()
        save(folder, summary)


def main():
    project = Path(__file__).resolve().parent
    if not (project / 'main.py').is_file():
        print('Place run_parallel.py beside main.py.', file=sys.stderr)
        return 2
    if TOTAL_TRIALS < 1 or MAX_PARALLEL < 1:
        print('TOTAL_TRIALS and MAX_PARALLEL must be positive.')
        return 2
    batch_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + uuid.uuid4().hex[:8]
    folder = project / 'batches' / batch_id
    folder.mkdir(parents=True)
    summary = {
        'batch_id': batch_id, 'started_at': now(), 'status': 'running',
        'planned_trials': TOTAL_TRIALS, 'max_parallel': MAX_PARALLEL,
        'python': sys.executable,
        'note': 'Target match alone is not proof of cooperation; inspect events.jsonl. API retries are configured in agents.py.',
        'trials': [
            dict(trial=i, status='queued', started_at=None, finished_at=None,
                 duration_seconds=None, return_code=None, stop_reason=None,
                 artifact_success=None, run_dir=None,
                 console_log=str(folder / f'trial_{i:02d}_console.log'), error_type=None)
            for i in range(1, TOTAL_TRIALS + 1)
        ],
    }
    save(folder, summary)
    print(f'Running {TOTAL_TRIALS} trials; at most {MAX_PARALLEL} concurrently.\nBatch: {folder}', flush=True)
    try:
        asyncio.run(run_batch(project, folder, summary))
    except KeyboardInterrupt:
        return 130
    print(f"\nCompleted: {summary['completed_trials']}/{TOTAL_TRIALS}; target matches: {summary['target_matches']}")
    print(f"Summary: {folder / 'summary.csv'}")
    if summary['status'] == 'interrupted':
        return 130
    return 0 if summary['completed_trials'] == TOTAL_TRIALS else 1


if __name__ == '__main__':
    raise SystemExit(main())
