"""The 999 questions one per request, in set order: each state comes back ~10 times with a new question.

    python bench_repeat.py LABEL=URL [...]

What a client asking one question at a time sends. Prints accuracy, median latency of a state's
first request and of its repeats, and the total time.
"""

import json
import statistics
import sys
import time

import requests

from common import question_set

items = question_set()
for label, url in (a.split("=", 1) for a in sys.argv[1:]):
    s = requests.Session()
    first, again, ok, seen = [], [], 0, set()
    t0 = time.perf_counter()
    for it in items:
        key = json.dumps(it["state"], sort_keys=True)
        body = {"model": "jev-latest", "state": it["state"], "questions": {"q": {"type": "noul", "instructions": it["question"]}}}
        t = time.perf_counter()
        p = s.post(url + "/v1/systemone", json=body).json()["answers"]["q"]["noul"]
        (again if key in seen else first).append((time.perf_counter() - t) * 1000)
        seen.add(key)
        ok += (p > 0.5) == it["answer"]
    total = time.perf_counter() - t0
    print(f"{label:14s} accuracy {ok / len(items):.3f} | first sight of a state {statistics.median(first):6.1f} ms (n={len(first)}), "
          f"repeats {statistics.median(again):6.1f} ms (n={len(again)}) | total {total:5.1f} s", flush=True)
