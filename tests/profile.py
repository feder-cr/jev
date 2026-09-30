"""Where a request's time goes in `jev`: Server-Timing phases, median over many requests.

    python profile.py LABEL=URL [LABEL=URL ...] [--rounds 30]

Requests: the README's short/long ones, one and three questions on an order, and ten 999-set states
with all their questions (~10 per request). Columns are server phases (ms) plus `http`, the client's
time minus the server's total (sockets, HTTP parsing, JSON on the client side).
"""

import json
import statistics
import sys
import time
from collections import defaultdict

import requests

from bench_http_requests import REQS
from common import question_set

rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 30
servers = [a.split("=", 1) for a in sys.argv[1:] if "=" in a]
PHASES = ["parse", "validate", "tokenize", "queue", "inference", "respond", "total", "http"]

items = question_set()
groups = defaultdict(list)
for i, it in enumerate(items):
    groups[json.dumps(it["state"], sort_keys=True)].append(i)
reqs = dict(REQS)
for k, g in enumerate(list(groups.values())[:10]):
    reqs[f"999 state {k} ({len(g)}q)"] = {"model": "jev-latest", "state": items[g[0]]["state"],
                                           "questions": {str(i): {"type": "noul", "instructions": items[i]["question"]} for i in g}}

for label, url in servers:
    s = requests.Session()
    print(f"\n{label}: median ms over {rounds} requests")
    print(f"{'request':22s}" + "".join(f"{p:>10s}" for p in PHASES) + f"{'tokens':>8s}")
    for name, body in reqs.items():
        rows = defaultdict(list)
        for r in range(rounds + 3):
            t = time.perf_counter()
            resp = s.post(url + "/v1/systemone", json=body)
            client = (time.perf_counter() - t) * 1000
            if r < 3:
                continue
            timing = dict(part.strip().split(";dur=") for part in resp.headers["Server-Timing"].split(","))
            for k, v in timing.items():
                rows[k].append(float(v))
            rows["http"].append(client - float(timing["total"]))
        tokens = resp.json()["usage"]["input_tokens"]
        print(f"{name:22s}" + "".join(f"{statistics.median(rows[p]):10.2f}" if rows[p] else f"{'':10s}" for p in PHASES) + f"{tokens:8d}", flush=True)
