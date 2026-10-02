"""Check a build of `jev`: the tests CI runs on every OS, and the release is made from.

    python tests/check.py [--jev dist/jev/jev] [--build-dir build] [--exact] [--record] [--threads N]

1. plan-calls-test: how requests are split into model calls; choice-test, score-test: a choice's and a score's
   distribution; tokenizer.py: the token ids of 3,054 texts,
   the Python engine's wherever its std::regex pre-tokenizer could tokenize them;
2. parity with the Python server this one replaced: the 215 cases of parity.py (errors, formats and
   answers; parity.py's EXTENSIONS, answered here where it refused them, left out) against its responses kept in golden/jev-python-q8.json (the q8_0 GGUF of the released model, the INT8
   model's precision class): formats and errors exact, P(yes) within 0.15;
3. --exact: the same cases against golden/jev.json, a verified build's own responses, with zero
   tolerance: a check of a change on the machine and OS they were recorded on (OpenVINO picks kernels by CPU,
   and the numbers differ in the last digits between OSes); --record keeps them again;
4. snapshots.py: state snapshots, blocks and batching against an oracle that has none, both with f32
   activations (--dynamic-quantization 0), so they compute the same function and every answer must match;
   and, on that server, a request whose prompts share runs (a choice's options, a score's thresholds) read
   as a prefix tree: every answer the same as its prompt asked alone;
5. jev decide: a request file answered as the server answers it, errors on stderr with exit 1, and
   an --output file never written over; a choice: the same numbers as its options' yes/no questions,
   normalized, in Jev's shape; a score: the same numbers as its thresholds' yes/no questions, in Jev's shape;
6. /health: the SHA-256 of the model folder's files and their fingerprint, as Python's hashlib computes them;
7. jev serve on a port another server holds: refused, with exit 1 and a reason, never a second listener.
Exit status 1 when any step fails. The model folder is JEV_MODEL_DIR (tests/common.py).
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

from common import MODEL_DIR

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXE = ".exe" if platform.system() == "Windows" else ""
REQUEST = {"model": "jev-latest",
           "state": {"item": "wireless mouse", "customer_message": "The box arrived empty. This is the second time!"},
           "questions": {"upset": {"type": "noul", "instructions": "Is the customer upset?"},
                         "wrong_item": {"type": "noul", "instructions": "Does the customer say they received the wrong item?"}}}
failed = []
TIMEOUT = 600  # seconds for any one request: a hang fails the checks instead of holding the runner
THREADS = []  # --threads N: passed to every jev it starts, and to snapshots.py's oracle (default: their own)


def step(name, ok):
    print(f"{'ok  ' if ok else 'FAIL'} {name}", flush=True)
    if not ok:
        failed.append(name)


class Server:
    START_SECONDS = 300

    def __init__(self, jev, *args, port=8045):
        self.url = f"http://127.0.0.1:{port}"
        try:  # something already answering here would be tested in place of this build
            requests.get(self.url + "/health", timeout=2)
            sys.exit(f"port {port} is in use by another server: stop it, the checks start their own")
        except requests.ConnectionError:
            pass
        self.log = tempfile.TemporaryFile()
        env = {k: v for k, v in os.environ.items() if k != "JEV_API_KEY"}  # the checks send no key
        self.proc = subprocess.Popen([str(jev), "serve", "--model-dir", str(MODEL_DIR), "--port", str(port), *THREADS, *args],
                                     stdout=self.log, stderr=subprocess.STDOUT, env=env)
        deadline = time.monotonic() + self.START_SECONDS
        while time.monotonic() < deadline and self.proc.poll() is None:
            try:
                requests.get(self.url + "/health", timeout=1)
                return
            except requests.ConnectionError:
                time.sleep(0.3)
        self.proc.kill()
        self.proc.wait()
        self.log.seek(0)
        sys.exit(f"jev serve did not start:\n{self.log.read().decode(errors='replace')}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.proc.kill()
        self.proc.wait()


def run(*args):
    print("     $", " ".join(str(a) for a in args), flush=True)
    return subprocess.run([str(a) for a in args], cwd=HERE).returncode == 0


def parity(target, ref_file, tol, *extra):
    return run(sys.executable, "parity.py", "--ref-file", ref_file, "--target", target, "--tol", tol, "--multi-tol", tol, *extra)


def check_decide(jev, url):
    with tempfile.TemporaryDirectory() as tmp:
        request = Path(tmp) / "request.json"
        request.write_text(json.dumps(REQUEST), encoding="utf-8")
        served = requests.post(url + "/v1/systemone", json=REQUEST, timeout=TIMEOUT).json()
        out = Path(tmp) / "answers" / "answer.json"
        first = subprocess.run([str(jev), "decide", str(request), "--model-dir", str(MODEL_DIR), *THREADS, "--output", str(out)], capture_output=True)
        written = out.read_text(encoding="utf-8") if out.exists() else ""
        step("decide: the server's answer, as json.dumps(indent=2)", first.returncode == 0 and written == json.dumps(served, indent=2, ensure_ascii=False) + "\n")
        again = subprocess.run([str(jev), "decide", str(request), "--model-dir", str(MODEL_DIR), *THREADS, "--output", str(out)], capture_output=True)
        step("decide: an existing --output is not written over", again.returncode == 1 and out.read_text(encoding="utf-8") == written)
        bad = Path(tmp) / "bad.json"
        bad.write_text(json.dumps({"model": "jev-latest", "state": "x"}), encoding="utf-8")
        refused = subprocess.run([str(jev), "decide", str(bad), "--model-dir", str(MODEL_DIR), *THREADS], capture_output=True, text=True)
        step("decide: an invalid request is refused on stderr, exit 1",
             refused.returncode == 1 and not refused.stdout and '"loc":["body","questions"]' in refused.stderr)


def check_port_taken(jev, port):
    """A second server on a port in use refuses to start, and says why."""
    second = subprocess.run([str(jev), "serve", "--model-dir", str(MODEL_DIR), "--port", str(port), "--warmup", "0"],
                            capture_output=True, text=True, timeout=300)
    step("serve: a port in use is refused, exit 1", second.returncode == 1 and "cannot listen" in second.stderr)


CHOICE = {"billing": "payments, invoices, refunds", "shipping": "deliveries, missing or damaged parcels", "tech": "a product that does not work"}
CHOICE_INSTRUCTIONS = "Which team should handle this message?"
PHRASING = "Among the candidates, is it this one?"


def resume_from_snapshot(url, state):
    """Ask once about `state`, so that the requests compared next all resume from its snapshot (with INT8
    activations an answer moves slightly with how its call is composed)."""
    requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": {
        "q": {"type": "noul", "instructions": "Is this a message?"}}}, timeout=TIMEOUT)


def check_choice(url):
    """A choice is its options' yes/no answers (src/prompt.hpp choice_instructions), normalized: the same
    prompts asked as noul questions in the same order give the same numbers."""
    state, upset = REQUEST["state"], {"type": "noul", "instructions": "Is the customer upset?"}
    resume_from_snapshot(url, state)
    options = [f"{k}: {v}" for k, v in CHOICE.items()]
    listed = "\n".join(f"- {o}" for o in options)
    as_noul = {f"o{i}": {"type": "noul", "instructions": f"{CHOICE_INSTRUCTIONS}\nCandidates:\n{listed}\n{PHRASING}\nCandidate: {o}"}
               for i, o in enumerate(options)}
    choice = requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": {
        "team": {"type": "choice", "instructions": CHOICE_INSTRUCTIONS, "criteria": CHOICE}, "upset": upset}}, timeout=TIMEOUT)
    noul = requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": {**as_noul, "upset": upset}}, timeout=TIMEOUT)
    ok = choice.status_code == 200 and noul.status_code == 200
    if ok:
        a, ps = choice.json()["answers"]["team"], [noul.json()["answers"][f"o{i}"]["noul"] for i in range(len(options))]
        expected = [x / sum(ps) for x in ps]
        got = list(a["probabilities"].values())
        best = max(range(len(got)), key=got.__getitem__)
        ok = (list(a) == ["type", "choice", "probabilities", "confidence"] and list(a["probabilities"]) == list(CHOICE)
              and all(abs(g - e) < 1e-12 for g, e in zip(got, expected)) and a["choice"] == list(CHOICE)[best]
              and abs(a["confidence"] - (got[best] - 1 / 3) / (1 - 1 / 3)) < 1e-12
              and choice.json()["answers"]["upset"] == noul.json()["answers"]["upset"])
    step("choice: its options' yes/no answers, normalized, in Jev's shape", ok)


LEVELS = ["calm", "annoyed", {"level": "angry", "note": "raises their voice"}, "furious"]
SCORE_INSTRUCTIONS = "How angry is the customer?"
SCORE_PHRASING = "Is the answer at the following level or higher?"


def check_score(url):
    """A score is its thresholds' yes/no answers (src/prompt.hpp score_instructions), P(>= k) made
    non-increasing: the same prompts asked as noul questions give the same numbers; the levels come back
    as sent in `legend`."""
    state = REQUEST["state"]
    resume_from_snapshot(url, state)
    named = [json.dumps(l, sort_keys=True, separators=(",", ":")) if isinstance(l, dict) else l for l in LEVELS]
    scale = " < ".join(named)
    as_noul = {f"k{k}": {"type": "noul", "instructions": f"{SCORE_INSTRUCTIONS}\nScale from lowest to highest: {scale}\n{SCORE_PHRASING}\nLevel: {named[k]}"}
               for k in range(1, len(LEVELS))}
    score = requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": {
        "anger": {"type": "score", "instructions": SCORE_INSTRUCTIONS, "criteria": LEVELS}}}, timeout=TIMEOUT)
    noul = requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": as_noul}, timeout=TIMEOUT)
    ok = score.status_code == 200 and noul.status_code == 200
    if ok:
        a = score.json()["answers"]["anger"]
        ge = [noul.json()["answers"][f"k{k}"]["noul"] for k in range(1, len(LEVELS))]
        pools = []  # pool adjacent violators: P(>= k) non-increasing
        for v in ge:
            pools.append([v, 1])
            while len(pools) > 1 and pools[-2][0] / pools[-2][1] < pools[-1][0] / pools[-1][1]:
                s, c = pools.pop()
                pools[-1][0] += s
                pools[-1][1] += c
        g = [1.0] + [s / c for s, c in pools for _ in range(c)] + [0.0]
        expected = [g[i] - g[i + 1] for i in range(len(LEVELS))]
        got = [a["probabilities"][str(i)] for i in range(len(LEVELS))]
        mode = max(range(len(got)), key=got.__getitem__)
        mid = (len(LEVELS) - 1) / 2
        confidence = 1 - sum(p * abs(i - mode) for i, p in enumerate(got)) / (sum(abs(i - mid) for i in range(len(LEVELS))) / len(LEVELS))
        ok = (list(a) == ["type", "score", "legend", "probabilities", "confidence"]
              and a["legend"] == {str(i): l for i, l in enumerate(LEVELS)} and list(a["probabilities"]) == [str(i) for i in range(len(LEVELS))]
              and all(abs(x - e) < 1e-12 for x, e in zip(got, expected))
              and abs(a["score"] - sum(i * p for i, p in enumerate(got))) < 1e-12
              and abs(a["confidence"] - min(max(confidence, 0.0), 1.0)) < 1e-12)
    step("score: its thresholds' yes/no answers, in Jev's shape", ok)


def check_shared_reads(url):
    """With f32 activations, prompts read as a prefix tree in one call (src/tree.hpp) answer as each
    prompt asked in a request of its own: a 10-option choice, 2 yes/no questions and a 4-level score."""
    state = {**REQUEST["state"], "order": 31337}
    team = {**CHOICE, "returns": "sending a product back", "account": "login, password, profile", "sales": "questions before buying",
            "warranty": "repairs under guarantee", "fraud": "suspicious orders or payments", "feedback": "praise or suggestions",
            "legal": "privacy, data requests"}
    options = [f"{k}: {v}" for k, v in team.items()]
    listed = "\n".join(f"- {o}" for o in options)
    named = [json.dumps(l, sort_keys=True, separators=(",", ":")) if isinstance(l, dict) else l for l in LEVELS]
    scale = " < ".join(named)
    prompts = [f"{CHOICE_INSTRUCTIONS}\nCandidates:\n{listed}\n{PHRASING}\nCandidate: {o}" for o in options]
    prompts += ["Is the customer upset?", "Does the customer ask for a refund?"]
    prompts += [f"{SCORE_INSTRUCTIONS}\nScale from lowest to highest: {scale}\n{SCORE_PHRASING}\nLevel: {named[k]}" for k in range(1, len(LEVELS))]
    ask = lambda qs: requests.post(url + "/v1/systemone", json={"model": "jev-latest", "state": state, "questions": qs}, timeout=TIMEOUT)
    together = ask({f"p{i}": {"type": "noul", "instructions": t} for i, t in enumerate(prompts)})
    ok = together.status_code == 200
    worst = 0.0
    for i, t in enumerate(prompts):
        alone = ask({"q": {"type": "noul", "instructions": t}})
        ok = ok and alone.status_code == 200
        if ok:
            worst = max(worst, abs(together.json()["answers"][f"p{i}"]["noul"] - alone.json()["answers"]["q"]["noul"]))
    print(f"     {len(prompts)} prompts in one request vs each alone: max |dP| {worst:.6f}", flush=True)
    step("shared reads: a choice, yes/no questions and a score in one call answer as each prompt alone", ok and worst < 1e-4)


def check_health(url):
    health = requests.get(url + "/health", timeout=TIMEOUT).json()
    files = {n: hashlib.sha256((MODEL_DIR / n).read_bytes()).hexdigest() for n in ("model.json", "openvino_model.bin", "openvino_model.xml", "tokenizer.gguf")}
    fingerprint = hashlib.sha256("".join(f"{files[n]}  {n}\n" for n in sorted(files)).encode()).hexdigest()
    step("health: the model files' SHA-256 and fingerprint", health.get("model_files") == files and health.get("fingerprint") == fingerprint)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", type=Path, default=ROOT / "dist" / "jev" / f"jev{EXE}")
    ap.add_argument("--build-dir", type=Path, default=ROOT / "build")
    ap.add_argument("--exact", action="store_true", help="also compare with golden/jev.json at zero tolerance")
    ap.add_argument("--record", action="store_true", help="keep this build's responses as golden/jev.json")
    ap.add_argument("--threads", type=int, help="threads for every jev started and for the snapshot oracle (to share the machine)")
    args = ap.parse_args()
    if args.threads:
        THREADS.extend(["--threads", str(args.threads)])
    args.jev, args.build_dir = args.jev.resolve(), args.build_dir.resolve()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    golden = HERE / "golden"

    step("plan-calls-test", run(args.build_dir / f"plan-calls-test{EXE}"))
    step("choice-test", run(args.build_dir / f"choice-test{EXE}"))
    step("score-test", run(args.build_dir / f"score-test{EXE}"))
    step("tokenizer: the recorded token ids", run(sys.executable, "tokenizer.py", "--test", args.build_dir / f"tokenizer-test{EXE}"))
    reference = json.loads((golden / "jev-python-q8.json").read_text(encoding="utf-8"))["served"]  # the name it answered with
    with Server(args.jev, "--name", reference, "--warmup", "0") as s:
        step("parity with the Python server (the q8_0 GGUF of the same model, P within 0.15)", parity(s.url, golden / "jev-python-q8.json", "0.15", "--skip-extensions"))
    with Server(args.jev, "--warmup", "0") as s:
        if args.record:
            step("record golden/jev.json", run(sys.executable, "parity.py", "--ref", s.url, "--record", golden / "jev.json"))
        elif args.exact:
            step("parity with a verified build (zero tolerance)", parity(s.url, golden / "jev.json", "0"))
        check_decide(args.jev, s.url)
        check_choice(s.url)
        check_score(s.url)
        check_health(s.url)
        check_port_taken(args.jev, 8045)
    with Server(args.jev, "--warmup", "0", "--dynamic-quantization", "0") as s:
        step("snapshots, blocks, batching vs the plain oracle", run(sys.executable, "snapshots.py", "--target", s.url, "--model-dir", MODEL_DIR,
                                                                   "--dynamic-quantization", "0", *THREADS))
        check_shared_reads(s.url)
    print(f"=== FAILED: {', '.join(failed)}" if failed else "=== every check passed", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
