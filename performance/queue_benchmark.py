"""Create a bounded judge batch, enqueue it, and report persisted lifecycle timings."""

import argparse
import json
import math
import time
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.app.database import Session
from backend.app.judge_client import client
from backend.app.models import Profile, Submission, User

WORKLOADS = {
    "python": ("parity-check", "python", "n=int(input())\nprint('Even' if n%2==0 else 'Odd')"),
    "c": ("parity-check", "c", "#include <stdio.h>\nint main(){long n;if(scanf(\"%ld\",&n)!=1)return 1;puts(n%2?\"Odd\":\"Even\");}"),
    "cpp": ("parity-check", "cpp", "#include <iostream>\nint main(){long n;std::cin>>n;std::cout<<(n%2?\"Odd\":\"Even\")<<'\\n';}"),
    "java": ("parity-check", "java", "import java.util.*; class Main { public static void main(String[] a){ long n=new Scanner(System.in).nextLong(); System.out.println(n%2==0?\"Even\":\"Odd\"); }}"),
    "sql": ("city-totals", "sql", "SELECT city, SUM(amount) AS total_sales FROM sales GROUP BY city ORDER BY city"),
    "pandas": ("filter-students", "python", "df[df['Age'] > 15]"),
    "numpy": ("row-centering", "python", "x - x.mean(axis=1, keepdims=True)"),
    "mapreduce": ("mapreduce-word-count", "python", "def map_line(line):\n    return [(word.lower(), 1) for word in line.split()]\n\ndef reduce_word(word, values):\n    return sum(values)"),
    "ml": ("linear-prediction", "python", "def predict(x, weights, bias):\n    return x @ weights + bias"),
}


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[min(len(values) - 1, math.ceil(len(values) * fraction) - 1)] if values else 0


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workload", choices=WORKLOADS)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--enqueue-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.count <= 50:
        raise SystemExit("Refusing an unbounded judge batch")
    problem, language, source = WORKLOADS[args.workload]
    marker = uuid4().hex[:12]
    submission_ids: list[str] = []
    with Session() as db:
        user = User(
            email=f"judge-{marker}@example.com", username=f"judge_{marker}",
            password_hash="load-test-only", profile=Profile(display_name="Judge Load Test"),
        )
        db.add(user); db.flush()
        for _ in range(args.count):
            submission_id = str(uuid4())
            db.add(Submission(
                id=submission_id, user_id=user.id, problem_slug=problem, language=language,
                source_code=source, mode="RUN",
            ))
            submission_ids.append(submission_id)
        db.commit()
    started = time.perf_counter()
    for submission_id in submission_ids:
        client.send_task("judge.evaluate", args=[submission_id])
    if args.enqueue_only:
        print(json.dumps({"workload": args.workload, "queued": len(submission_ids)}))
        return
    deadline = time.monotonic() + args.timeout
    rows: list[Submission] = []
    while time.monotonic() < deadline:
        with Session() as db:
            rows = list(db.scalars(select(Submission).where(Submission.id.in_(submission_ids))))
            if len(rows) == args.count and all(
                row.status in {"FINISHED", "SYSTEM_ERROR", "CANCELLED"} for row in rows
            ):
                break
        time.sleep(.1)
    elapsed = time.perf_counter() - started
    if len(rows) != args.count or any(row.status not in {"FINISHED", "SYSTEM_ERROR", "CANCELLED"} for row in rows):
        raise SystemExit("Judge batch did not finish within the bounded timeout")
    queue_ms = [
        (aware(row.started_at) - aware(row.created_at)).total_seconds() * 1000
        for row in rows if row.started_at is not None
    ]
    execution_ms = [row.execution_ms for row in rows if row.execution_ms is not None]
    print(json.dumps({
        "workload": args.workload, "count": args.count, "elapsed_seconds": round(elapsed, 3),
        "throughput_per_second": round(args.count / elapsed, 3),
        "queue_median_ms": round(percentile(queue_ms, .5), 2),
        "queue_p95_ms": round(percentile(queue_ms, .95), 2),
        "execution_median_ms": round(percentile(execution_ms, .5), 2),
        "verdicts": {verdict: sum(row.verdict == verdict for row in rows) for verdict in sorted({row.verdict for row in rows})},
        "attempt_counts": sorted(row.attempt_count for row in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
