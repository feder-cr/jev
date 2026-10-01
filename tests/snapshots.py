"""The server's state snapshots, blocks and batching against an oracle that has none.

    python snapshots.py --target URL [--model-dir DIR] [--dynamic-quantization 0] [--tol 0.001]

The oracle answers every question alone, the plainest way: the same graph run from Python, the whole
prompt in one fresh call (no cached cells, no blocks, nothing else in the call), tokens from the HF
tokenizer (the GGUF one gives the same ids). Both run with the same --dynamic-quantization, 0 by
default: with activations quantized to INT8 an answer moves a little with how a call is composed (on 150
questions of one state, up to 0.044 between the oracle's own two readings, a state first or the whole
prompt), and that noise, not the logic, would decide the test. With f32 activations the server and the
oracle compute the same function, so every answer must match within --tol. Cases:
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
ap.add_argument("--dynamic-quantization", type=int, default=0, help="the server's --dynamic-quantization, which the oracle uses too")
ap.add_argument("--tol", type=float, default=0.001)
ap.add_argument("--threads", type=int, default=16, help="the oracle's OpenVINO threads")
args = ap.parse_args()

tok = Tokenizer.from_file(args.tokenizer or f"{args.model_dir}/tokenizer.json")
core = ov.Core()
cm = core.compile_model(f"{args.model_dir}/openvino_model.xml", "CPU",
                        {"INFERENCE_NUM_THREADS": args.threads, "PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1",
                         "DYNAMIC_QUANTIZATION_GROUP_SIZE": args.dynamic_quantization, "INFERENCE_PRECISION_HINT": "f32"})
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


def check(name, state, questions, got):
    worst, n = 0.0, 0
    for q, p in zip(questions, got):
        ref, n = oracle(state, q)
        worst = max(worst, abs(p - ref))
    status = "ok  " if worst <= args.tol else "FAIL"
    print(f"{status} {name:44s} max |dP| vs oracle {worst:.6f} ({len(questions)} questions, ~{n} tokens per prompt)")
    if worst > args.tol:
        failures.append(name)


served = health().get("dynamic_quantization")
if served != args.dynamic_quantization:
    sys.exit(f"the server runs --dynamic-quantization {served}, the oracle {args.dynamic_quantization}: start them alike")

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
check("a question longer than a call", story, long_question, ask(story, long_question))
check("a question longer than a call, with others", story, long_question + ["Did any order ship to lambda city?"],
      ask(story, long_question + ["Did any order ship to lambda city?"]))

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
    check(f"concurrent request {i}", states[i], ["Was the customer charged twice?"], results[i])
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
