"""One server's client-side latency on the README requests and the 999 set, for comparisons between servers
(the published Python jev, this server) run one at a time and alternated by the caller.

    python bench_servers.py LABEL URL [--rounds 20]

Prints one line: median ms of each README request, the 999 set grouped by state (median request, total),
and one question per request (median of first sights and of repeats, total), with the accuracy of both.
"""
import json
import statistics
import sys
import time
from collections import defaultdict

import requests

from bench_http_requests import REQS
from common import question_set

label, url = sys.argv[1], sys.argv[2]
rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 20
s = requests.Session()
post = lambda body: s.post(url + "/v1/systemone", json=body, timeout=3600).json()
parts = []
for name, body in REQS.items():
    for _ in range(3):
        post(body)
    ts = []
    for _ in range(rounds):
        t = time.perf_counter()
        post(body)
        ts.append((time.perf_counter() - t) * 1000)
    parts.append(f"{name} {statistics.median(ts):.1f}")
items = question_set()
groups = defaultdict(list)
for i, it in enumerate(items):
    groups[json.dumps(it["state"], sort_keys=True)].append(i)
q = lambda text: {"type": "noul", "instructions": text}
times, ok = [], 0
t0 = time.perf_counter()
for g in groups.values():
    body = {"model": "jev-latest", "state": items[g[0]]["state"], "questions": {str(i): q(items[i]["question"]) for i in g}}
    t = time.perf_counter()
    ans = post(body)["answers"]
    times.append((time.perf_counter() - t) * 1000)
    ok += sum((ans[str(i)]["noul"] > 0.5) == items[i]["answer"] for i in g)
parts.append(f"999 grouped {statistics.median(times):.0f} (total {time.perf_counter() - t0:.1f} s, acc {ok / len(items):.3f})")
first, again, seen, ok = [], [], set(), 0
t0 = time.perf_counter()
for it in items:
    key = json.dumps(it["state"], sort_keys=True)
    t = time.perf_counter()
    p = post({"model": "jev-latest", "state": it["state"], "questions": {"q": q(it["question"])}})["answers"]["q"]["noul"]
    (again if key in seen else first).append((time.perf_counter() - t) * 1000)
    seen.add(key)
    ok += (p > 0.5) == it["answer"]
parts.append(f"999 one per request: first {statistics.median(first):.0f}, repeats {statistics.median(again):.0f} "
             f"(total {time.perf_counter() - t0:.1f} s, acc {ok / len(items):.3f})")
print(f"{label:22s} | " + " | ".join(parts), flush=True)
