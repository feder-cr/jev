"""Throughput and latency with several clients at once (the scheduler reads waiting requests together).

    python bench_concurrent.py URL [--clients 1,4,8] [--requests 200] [--short]

Each client sends one-question requests from the 999 set (its own slice, so states differ between
clients). Prints requests/s, median and p90 latency per client count, and how many requests the
server read together with others.
"""

import statistics
import sys
import threading
import time

import requests

from common import question_set

url = sys.argv[1]
clients = [int(x) for x in (sys.argv[sys.argv.index("--clients") + 1] if "--clients" in sys.argv else "1,4,8").split(",")]
total = int(sys.argv[sys.argv.index("--requests") + 1]) if "--requests" in sys.argv else 200
items = question_set()
if "--short" in sys.argv:  # the README's short request, with a different question per request
    items = [{"state": "Help! My payouts have been failing for 3 days.", "question": f"Does this convey urgency, case {i}?"} for i in range(999)]


def batched():
    return requests.get(url + "/health").json().get("engine", {}).get("batched_requests", 0)  # the Python server has no such counter


for n in clients:
    lat, lock = [], threading.Lock()
    per = total // n

    def worker(c):
        s = requests.Session()
        for k in range(per):
            it = items[(c * 97 + k * 13) % len(items)]
            body = {"model": "jev-latest", "state": it["state"], "questions": {"q": {"type": "noul", "instructions": it["question"]}}}
            t = time.perf_counter()
            s.post(url + "/v1/systemone", json=body).raise_for_status()
            with lock:
                lat.append((time.perf_counter() - t) * 1000)

    b0 = batched()
    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(c,)) for c in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    lat.sort()
    print(f"{n} clients: {len(lat) / wall:5.2f} requests/s | latency median {statistics.median(lat):6.1f} ms, p90 {lat[int(len(lat) * 0.9)]:6.1f} ms"
          f" | read together: {batched() - b0}", flush=True)
