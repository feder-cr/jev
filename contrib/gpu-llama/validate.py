#!/usr/bin/env python3
"""jevos GPU lane: answer-agreement validation and latency, GPU llama.cpp vs CPU OpenVINO.

Sends the same seeded scenario set to both servers, compares decisions and probabilities,
then measures p50/p95 latency for a short/1-question and a long/5-question request.
Writes results.json. Rate against the CPU server is capped at ~2 requests/second.
"""
import json
import random
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CPU = "http://127.0.0.1:8017/v1/systemone"
GPU = "http://127.0.0.1:8153/v1/systemone"

QUESTIONS = {
    "danger/hit":     {"type": "noul", "instructions": "Is the ship about to be hit by a bomb?"},
    "danger/land":    {"type": "noul", "instructions": "Is a bomb about to land on the ship?"},
    "fire/should":    {"type": "noul", "instructions": "Should the ship fire its gun right now?"},
    "fire/line":      {"type": "noul", "instructions": "Is an alien in the line of fire right now?"},
    "fire/hit":       {"type": "noul", "instructions": "Would firing now likely hit an alien?"},
    "fire/aiming":    {"type": "noul", "instructions": "Is the ship aiming at an alien right now?"},
    "spatial/bombL":  {"type": "noul", "instructions": "Is the nearest bomb to the left of the ship?"},
    "spatial/alienL": {"type": "noul", "instructions": "Is the lowest alien to the left of the ship?"},
    "dodge/choice":   {"type": "choice", "instructions": "Which way should the ship move right now?",
                       "criteria": {"left": "move left", "right": "move right"}},
}


def make_scenarios(n=120, seed=42):
    """Same generator as demo/study.py (rng seeded identically, same draw order)."""
    rng = random.Random(seed)
    scs = []
    ship_cols = [0, 1, 2, 4, 5, 6, 8, 9]
    for i in range(n):
        ship = rng.choice(ship_cols)
        alien = rng.randrange(10)
        rows_up = rng.choice([2, 3, 5, 8])
        bomb = None
        r = rng.random()
        if r < 0.40:
            bomb = (max(0, min(9, ship + rng.choice([-1, 0, 0, 1]))), rng.choice([60, 70, 80, 90]))
        elif r < 0.65:
            bomb = (max(0, min(9, ship + rng.choice([-3, -2, 2, 3]))), rng.choice([30, 45, 55]))
        elif r < 0.80:
            bomb = (rng.randrange(10), rng.choice([10, 20, 30]))
        scs.append(dict(ship=ship, alien=alien, rows=rows_up, bomb=bomb))
    return scs


def rep_col(sc):
    s = (f"Space Invaders. Your ship is in column {sc['ship']} of 10. "
         f"40 aliens remain; the lowest is at column {sc['alien']}, {sc['rows']} rows above you. ")
    if sc["bomb"]:
        s += (f"One bomb is falling at column {sc['bomb'][0]}, {sc['bomb'][1]} percent from the top"
              + (", close to your ship" if sc["bomb"][0] == sc["ship"] and sc["bomb"][1] >= 55 else "")
              + ". ")
    else:
        s += "No bombs in the air. "
    return s + "Your gun is ready."


def y_danger(sc):
    b = sc["bomb"]
    return b is not None and b[0] == sc["ship"] and b[1] >= 55


def y_fire(sc):
    return sc["alien"] == sc["ship"]


def y_bomb_left(sc):
    b = sc["bomb"]
    return b is not None and b[0] < sc["ship"]


def y_alien_left(sc):
    return sc["alien"] < sc["ship"]


def y_dodge_dir(sc):
    b = sc["bomb"]
    if b is None or abs(b[0] - sc["ship"]) > 2 or b[1] < 40:
        return 0
    return 1 if b[0] < sc["ship"] else -1 if b[0] > sc["ship"] else 0


def ask(url, state, questions):
    payload = {"model": "jev-latest", "state": state, "questions": questions}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    scs = make_scenarios(120)
    print(f"n={len(scs)} scenarios; sending the {len(QUESTIONS)}-question batch to both servers")

    cpu_rows, gpu_rows = [], []
    t0 = time.time()
    for i, sc in enumerate(scs):
        state = rep_col(sc)
        gpu = ask(GPU, state, QUESTIONS)["answers"]
        gpu_rows.append((sc, gpu))
        time.sleep(0.3)
        cpu = ask(CPU, state, QUESTIONS)["answers"]
        cpu_rows.append((sc, cpu))
        time.sleep(0.2)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(scs)} done ({time.time()-t0:.0f}s)")

    # agreement
    per_q = {}
    noul_dps = {}
    choice_agree = []
    for (sc, gpu), (_, cpu) in zip(gpu_rows, cpu_rows):
        for qname in QUESTIONS:
            g, c = gpu[qname], cpu[qname]
            if qname == "dodge/choice":
                lab = y_dodge_dir(sc)
                if lab != 0:
                    gg = g["probabilities"]["right"] > 0.5
                    cc = c["probabilities"]["right"] > 0.5
                    want = lab > 0
                    choice_agree.append((gg == want, cc == want, gg == cc))
            else:
                gg, cc = g["noul"], c["noul"]
                d = abs(gg - cc)
                noul_dps.setdefault(qname, []).append(d)
                key = qname.split("/")[0] if not qname.startswith("spatial/") else qname
                lab = {"danger": y_danger, "fire": y_fire,
                       "spatial/bombL": y_bomb_left, "spatial/alienL": y_alien_left}[key](sc)
                per_q.setdefault(qname, []).append(((gg > 0.5) == lab, (cc > 0.5) == lab))

    results = {"scenarios": len(scs), "per_question": {}}
    print(f"\n{'question':16s} {'agree%':>8s} {'cpu_acc':>8s} {'gpu_acc':>8s} {'mean|dP|':>9s} {'p95|dP|':>8s}")
    tot_agree = tot_n = 0
    for qname in QUESTIONS:
        if qname == "dodge/choice":
            n = len(choice_agree)
            agree = sum(1 for _, _, same in choice_agree if same)
            cpu_ok = sum(1 for _, ok, _ in choice_agree if ok)
            gpu_ok = sum(1 for ok, _, _ in choice_agree if ok)
            print(f"{qname:16s} {100*agree/n:7.1f}% {100*cpu_ok/n:7.1f}% {100*gpu_ok/n:7.1f}%")
            results["per_question"][qname] = dict(n=n, agree=round(agree/n, 4))
            tot_agree += agree; tot_n += n
            continue
        rows = per_q[qname]
        n = len(rows)
        agree = sum(1 for g, c in rows if g == c)
        cpu_ok = sum(1 for _, c in rows if c)
        gpu_ok = sum(1 for g, _ in rows if g)
        dps = noul_dps[qname]
        dps_sorted = sorted(dps)
        p95 = dps_sorted[int(0.95 * (n - 1))]
        print(f"{qname:16s} {100*agree/n:7.1f}% {100*cpu_ok/n:7.1f}% {100*gpu_ok/n:7.1f}% "
              f"{statistics.mean(dps):9.4f} {p95:8.4f}")
        results["per_question"][qname] = dict(n=n, agree=round(agree/n, 4), cpu_acc=round(cpu_ok/n, 4),
                                              gpu_acc=round(gpu_ok/n, 4), mean_dp=round(statistics.mean(dps), 4),
                                              p95_dp=round(p95, 4), max_dp=round(max(dps), 4))
        tot_agree += agree; tot_n += n
    print(f"{'OVERALL':16s} {100*tot_agree/tot_n:7.1f}%")
    results["overall_agree"] = round(tot_agree / tot_n, 4)

    # ------------------------------------------------------------------ latency
    def pctl(xs, p):
        xs = sorted(xs)
        return xs[int(p / 100 * (len(xs) - 1))]

    def timed(url, state, questions, runs=30):
        xs = []
        for i in range(runs):
            t = time.perf_counter()
            ask(url, state, questions)
            xs.append((time.perf_counter() - t) * 1000)
            if url == CPU:
                time.sleep(0.5)  # ~2 req/s cap against the CPU server
            else:
                time.sleep(0.05)
        return xs

    short_q = {"danger/hit": QUESTIONS["danger/hit"]}
    long_state = ("Refund policy section 4: " +
                  "Items reported missing within thirty days of delivery are refunded to the original payment method. " * 9 +
                  "The customer says the box arrived empty and this is the second time. ")
    long_qs = {
        "refund": {"type": "noul", "instructions": "Should this customer get a refund?"},
        "policy": {"type": "noul", "instructions": "Does the report arrive within the policy window?"},
        "repeat": {"type": "noul", "instructions": "Is this the customer's first complaint?"},
        "team": {"type": "choice", "instructions": "Which team should handle this message?",
                 "criteria": {"billing": "payments, refunds", "shipping": "deliveries, parcels", "tech": "a product that does not work"}},
        "anger": {"type": "score", "instructions": "How angry is the customer?", "criteria": ["calm", "annoyed", "angry", "furious"]},
    }

    lat = {}
    for name, state, qs in [("short/1q", rep_col(scs[0]), short_q), ("long/5q", long_state, long_qs)]:
        for label, url in [("cpu", CPU), ("gpu", GPU)]:
            xs = timed(url, state, qs)
            lat[f"{name}"] = lat.get(f"{name}", {})
            lat[f"{name}"][label] = dict(p50_ms=round(pctl(xs, 50), 1), p95_ms=round(pctl(xs, 95), 1),
                                         mean_ms=round(statistics.mean(xs), 1), n=len(xs))
            print(f"{name} {label}: p50={pctl(xs,50):.1f}ms p95={pctl(xs,95):.1f}ms (n={len(xs)})")
    results["latency"] = lat

    with open("results.json", "w") as f:
        json.dump(results, f, indent=1)
    print("\nwrote results.json")


if __name__ == "__main__":
    main()
