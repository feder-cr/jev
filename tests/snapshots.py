"""The server's state snapshots, blocks and batching against an oracle that has none.

    python snapshots.py --target URL [--model-dir DIR] [--tol 0.02]

The oracle answers every question alone, the plainest way: the same graph run from Python, the whole
prompt in one fresh call (no cached cells, no blocks, nothing else in the call), tokens from the HF
tokenizer (the GGUF one gives the same ids). Fewer than 5 questions: each answer within its case's
tolerance. From 5, since INT8 answers move a little with how a call is composed: no bias (the signed
mean within 3 standard errors of 0), mean |dP| within 0.01, max within 0.1. Cases:
  repeat          the same request twice: the second resumes from the first one's snapshot
  partial prefix  a state extended by one sentence: resumes from the shorter state's cells
  long state      > 2048 state tokens, 1 and 5 questions: the state is read in blocks
  many questions  more question tokens than one call takes: follow-up calls from the state's cells
  long question   one question longer than a call (the server used to hang on it): a call of its own
  concurrent      8 requests at once: the scheduler reads them together in one call
  eviction        more states than the cache keeps: the oldest goes, answers stay right
Exit status 1 on any failure.
"""

import argparse
import json
import math
import sys
import threading

import numpy as np
import openvino as ov
import requests
from tokenizers import Tokenizer

from common import MODEL_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--target", required=True)
ap.add_argument("--model-dir", default=str(MODEL_DIR))
ap.add_argument("--tokenizer", help="the HF tokenizer.json (default: the model folder's)")
ap.add_argument("--tol", type=float, default=0.02)
args = ap.parse_args()

tok = Tokenizer.from_file(args.tokenizer or f"{args.model_dir}/tokenizer.json")
core = ov.Core()
cm = core.compile_model(f"{args.model_dir}/openvino_model.xml", "CPU",
                        {"INFERENCE_NUM_THREADS": 16, "PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1", "DYNAMIC_QUANTIZATION_GROUP_SIZE": 128})
req = cm.create_infer_request()
pasts = {n: np.zeros((1, i.get_partial_shape()[1].get_length(), 0, i.get_partial_shape()[3].get_length()), np.float32)
         for i in cm.inputs for n in i.get_names() if n.startswith("past_")}
session = requests.Session()
failures = []


def render(state):
    body = state.strip() if isinstance(state, str) and "</evidence>" not in state.lower() else json.dumps(state, ensure_ascii=False, indent=1)
    return f"<evidence>\n{body}\n</evidence>"


def oracle(state, question):
    ids = tok.encode(f"<s>{render(state)}\n\nQuestion: {question.strip()}\nAnswer:", add_special_tokens=False).ids
    n = len(ids)
    out = req.infer({"input_ids": np.array([ids], np.int64), "position_ids": np.arange(n, dtype=np.int64)[None],
                     "attention_bias": np.where(np.tril(np.ones((n, n), bool)), 0, -np.inf).astype(np.float32)[None, None],
                     "logit_index": np.array([n - 1], np.int64)} | pasts)
    lg = out["logits"].reshape(2)
    return 1 / (1 + math.exp(-(float(lg[1]) - float(lg[0])))), n


def ask(state, questions, s=None):
    body = {"model": "jev-latest", "state": state, "questions": {f"q{i}": {"type": "noul", "instructions": q} for i, q in enumerate(questions)}}
    r = (s or session).post(args.target + "/v1/systemone", json=body, timeout=600)
    r.raise_for_status()
    return [r.json()["answers"][f"q{i}"]["noul"] for i in range(len(questions))]


def health():
    return session.get(args.target + "/health").json()["engine"]


def check(name, state, questions, got, tol=None):
    tol = tol or args.tol
    d, n = [], 0
    for q, p in zip(questions, got):
        ref, n = oracle(state, q)
        d.append(p - ref)
    worst = max(abs(v) for v in d)
    if len(d) >= 5:
        # Several questions: INT8 feels how a call is composed (a state from a snapshot or read with the
        # questions, which questions share a call). On the 150-question case the oracle's own two readings,
        # the whole prompt or the state first and the question from its cells, are up to 0.044 apart (mean
        # 0.006, unbiased): a tail of noise. A wrong mask, position or cell shows as a bias or a mean instead.
        # The bias is judged against the sample's own standard error: a shift of every answer fails however
        # few they are (their spread is small), noise alone passes however many.
        signed, mean = sum(d) / len(d), sum(abs(v) for v in d) / len(d)
        se = math.sqrt(sum((v - signed) ** 2 for v in d) / (len(d) - 1) / len(d))
        good = abs(signed) <= 3 * se and mean <= 0.01 and worst <= 0.1
        print(f"{'ok  ' if good else 'FAIL'} {name:44s} signed mean {signed:+.4f} (3 s.e. {3 * se:.4f}), mean |dP| {mean:.4f}, "
              f"max {worst:.4f} vs oracle ({len(d)} questions, ~{n} tokens per prompt)")
        if not good:
            failures.append(name)
        return
    status = "ok  " if worst <= tol else "FAIL"
    print(f"{status} {name:44s} max |dP| vs oracle {worst:.4f} (tol {tol}, ~{n} tokens per prompt)")
    if worst > tol:
        failures.append(name)


WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon".split()
story = " ".join(f"Order {1000 + i} shipped to {WORDS[i % 20]} city with {i % 7} items." for i in range(40))

# repeat
h0 = health()["state_snapshots"]
a = ask(story, ["Did any order ship to lambda city?"])
b = ask(story, ["Did any order ship to lambda city?"])
check("repeat: first (fresh)", story, ["Did any order ship to lambda city?"], a)
check("repeat: second (from its snapshot)", story, ["Did any order ship to lambda city?"], b)
h1 = health()["state_snapshots"]
if h1["hits"] <= h0["hits"]:
    failures.append("repeat: no snapshot hit counted")
    print("FAIL repeat: the second request did not resume from a snapshot", h0, h1)

# partial prefix: the shorter state's cells, then the added sentence
longer = story + " One more order shipped late."
check("partial prefix (state extended)", longer, ["Did an order ship late?"], ask(longer, ["Did an order ship late?"]))

# long state: read in blocks
huge = " ".join(f"Log line {i}: service {WORDS[i % 20]} answered in {i % 97} ms." for i in range(420))
check("long state, 1 question", huge, ["Did service kappa answer?"], ask(huge, ["Did service kappa answer?"]))
qs5 = [f"Did service {w} answer in under 50 ms?" for w in WORDS[:5]]
check("long state, 5 questions", huge, qs5, ask(huge, qs5))

# many questions: more question tokens than one call takes
many = [f"Is order {1000 + i} one of the orders listed, and did it ship to {WORDS[i % 20]} city?" for i in range(150)]
check("many questions (follow-up calls)", story, many, ask(story, many))

# a question longer than a call (2710 tokens, within the 8000 characters a text may have): a call of its own
codes = " ".join(str(10000 + 7 * i) for i in range(900))
long_question = [f"Is code 10700 among these codes: {codes}?"]
check("a question longer than a call", story, long_question, ask(story, long_question), tol=0.03)
check("a question longer than a call, with others", story, long_question + ["Did any order ship to lambda city?"],
      ask(story, long_question + ["Did any order ship to lambda city?"]), tol=0.03)

# concurrent requests: batched by the scheduler
batched_before = health().get("batched_requests", 0)
states = [f"Ticket {i}: the customer in {WORDS[i]} city says the invoice {i * 7} was charged twice." for i in range(8)]
results = [None] * 8


def client(i):
    results[i] = ask(states[i], ["Was the customer charged twice?"], requests.Session())


threads = [threading.Thread(target=client, args=(i,)) for i in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
for i in range(8):
    check(f"concurrent request {i}", states[i], ["Was the customer charged twice?"], results[i], tol=0.03)
print(f"     requests read together with others: {health().get('batched_requests', 0) - batched_before}")

# eviction: more states than kept, then the first again
keep_max = health()["state_snapshots"]["max"]
first = f"Warehouse report 0. " + story
for i in range(keep_max + 4):
    ask(f"Warehouse report {i}. " + story, ["Is this a warehouse report?"])
check("after eviction, the oldest state again", first, ["Is this a warehouse report?"], ask(first, ["Is this a warehouse report?"]))
snap = health()["state_snapshots"]
if snap["kept"] > keep_max:
    failures.append("eviction")
    print("FAIL more snapshots kept than the maximum", snap)
print("snapshot counters:", snap)
print("\nall snapshot checks passed" if not failures else f"\n{len(failures)} failed: {failures}")
sys.exit(1 if failures else 0)
