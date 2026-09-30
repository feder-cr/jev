"""The 999 questions asked the way a client asks them: every question on a state in one request.

    python bench_multi.py LABEL=URL [LABEL=URL ...] [--direct URL]

The 999 set has 100 states with ~10 questions each: one request per state. For every server:
accuracy, median and total request time, and, against --direct (every question alone, one request
each: the unshared answer), the mean and largest |dP| and the answers that change side.
"""

import json
import statistics
import sys
import time
from collections import defaultdict

import requests

from common import question_set

items = question_set()
groups = defaultdict(list)
for i, it in enumerate(items):
    groups[json.dumps(it["state"], sort_keys=True)].append(i)
groups = list(groups.values())

args = [a for a in sys.argv[1:] if not a.startswith("--")]
direct_url = sys.argv[sys.argv.index("--direct") + 1] if "--direct" in sys.argv else None
servers = [a.split("=", 1) for a in args if a != direct_url]


def q(text):
    return {"type": "noul", "instructions": text}


direct = None
if direct_url:
    s = requests.Session()
    direct = [None] * len(items)
    for i, it in enumerate(items):
        body = {"model": "jev-latest", "state": it["state"], "questions": {"q": q(it["question"])}}
        direct[i] = s.post(direct_url + "/v1/systemone", json=body).json()["answers"]["q"]["noul"]
    acc = sum((p > 0.5) == it["answer"] for p, it in zip(direct, items)) / len(items)
    print(f"{'direct':14s} accuracy {acc:.3f} (one question per request)")

for label, url in servers:
    s = requests.Session()
    ps, times = [None] * len(items), []
    for _ in range(3):  # warm-up
        s.post(url + "/v1/systemone", json={"model": "jev-latest", "state": items[groups[0][0]]["state"],
                                            "questions": {str(i): q(items[i]["question"]) for i in groups[0]}})
    for g in groups:
        body = {"model": "jev-latest", "state": items[g[0]]["state"], "questions": {str(i): q(items[i]["question"]) for i in g}}
        t = time.perf_counter()
        ans = s.post(url + "/v1/systemone", json=body).json()["answers"]
        times.append((time.perf_counter() - t) * 1000)
        for i in g:
            ps[i] = ans[str(i)]["noul"]
    acc = sum((p > 0.5) == it["answer"] for p, it in zip(ps, items)) / len(items)
    line = f"{label:14s} accuracy {acc:.3f} | request median {statistics.median(times):6.1f} ms, total {sum(times) / 1000:5.1f} s"
    if direct:
        d = [abs(a - b) for a, b in zip(ps, direct)]
        flips = sum((a > 0.5) != (b > 0.5) for a, b in zip(ps, direct))
        line += f" | vs direct: mean |dP| {statistics.mean(d):.4f}, max {max(d):.4f}, {flips} flips"
    print(line, flush=True)
