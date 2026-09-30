"""Check a build of `jev`: the tests CI runs on every OS, and the release is made from.

    python tests/check.py [--jev dist/jev/jev] [--build-dir build] [--exact] [--record]

1. plan-calls-test: how requests are split into model calls; tokenizer.py: the token ids of 3,054 texts,
   the Python engine's wherever its std::regex pre-tokenizer could tokenize them;
2. parity with the Python server this one replaced: the 215 cases of parity.py (errors, formats and
   answers) against its responses kept in golden/jev-python-q8.json (the jevos-v2 q8_0 GGUF, the INT8
   model's precision class): formats and errors exact, P(yes) within 0.15;
3. --exact: the same cases against golden/jev.json, a verified build's own responses, with zero
   tolerance: a check of a change on the machine and OS they were recorded on (OpenVINO picks kernels by CPU,
   and the numbers differ in the last digits between OSes); --record keeps them again;
4. snapshots.py: state snapshots, blocks and batching against an oracle that has none, both with f32
   activations (--dynamic-quantization 0), so they compute the same function and every answer must match;
5. jev decide: a request file answered as the server answers it, errors on stderr with exit 1, and
   an --output file never written over;
6. /health: the SHA-256 of the model folder's files and their fingerprint, as Python's hashlib computes them.
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


def step(name, ok):
    print(f"{'ok  ' if ok else 'FAIL'} {name}", flush=True)
    if not ok:
        failed.append(name)


class Server:
    def __init__(self, jev, *args, port=8045):
        self.url = f"http://127.0.0.1:{port}"
        self.log = tempfile.TemporaryFile()
        self.proc = subprocess.Popen([str(jev), "serve", "--model-dir", str(MODEL_DIR), "--port", str(port), *args],
                                     stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(300):
            try:
                requests.get(self.url + "/health", timeout=1)
                return
            except requests.ConnectionError:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.3)
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


def parity(target, ref_file, tol):
    return run(sys.executable, "parity.py", "--ref-file", ref_file, "--target", target, "--tol", tol, "--multi-tol", tol)


def check_decide(jev, url):
    with tempfile.TemporaryDirectory() as tmp:
        request = Path(tmp) / "request.json"
        request.write_text(json.dumps(REQUEST), encoding="utf-8")
        served = requests.post(url + "/v1/systemone", json=REQUEST).json()
        out = Path(tmp) / "answers" / "answer.json"
        first = subprocess.run([str(jev), "decide", str(request), "--model-dir", str(MODEL_DIR), "--output", str(out)], capture_output=True)
        written = out.read_text(encoding="utf-8") if out.exists() else ""
        step("decide: the server's answer, as json.dumps(indent=2)", first.returncode == 0 and written == json.dumps(served, indent=2, ensure_ascii=False) + "\n")
        again = subprocess.run([str(jev), "decide", str(request), "--model-dir", str(MODEL_DIR), "--output", str(out)], capture_output=True)
        step("decide: an existing --output is not written over", again.returncode == 1 and out.read_text(encoding="utf-8") == written)
        bad = Path(tmp) / "bad.json"
        bad.write_text(json.dumps({"model": "jev-latest", "state": "x"}), encoding="utf-8")
        refused = subprocess.run([str(jev), "decide", str(bad), "--model-dir", str(MODEL_DIR)], capture_output=True, text=True)
        step("decide: an invalid request is refused on stderr, exit 1",
             refused.returncode == 1 and not refused.stdout and '"loc":["body","questions"]' in refused.stderr)


def check_health(url):
    health = requests.get(url + "/health").json()
    files = {n: hashlib.sha256((MODEL_DIR / n).read_bytes()).hexdigest() for n in ("model.json", "openvino_model.bin", "openvino_model.xml", "tokenizer.gguf")}
    fingerprint = hashlib.sha256("".join(f"{files[n]}  {n}\n" for n in sorted(files)).encode()).hexdigest()
    step("health: the model files' SHA-256 and fingerprint", health.get("model_files") == files and health.get("fingerprint") == fingerprint)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jev", type=Path, default=ROOT / "dist" / "jev" / f"jev{EXE}")
    ap.add_argument("--build-dir", type=Path, default=ROOT / "build")
    ap.add_argument("--exact", action="store_true", help="also compare with golden/jev.json at zero tolerance")
    ap.add_argument("--record", action="store_true", help="keep this build's responses as golden/jev.json")
    args = ap.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    golden = HERE / "golden"

    step("plan-calls-test", run(args.build_dir / f"plan-calls-test{EXE}"))
    step("tokenizer: the recorded token ids", run(sys.executable, "tokenizer.py", "--test", args.build_dir / f"tokenizer-test{EXE}"))
    with Server(args.jev, "--name", "jevos-v2-q8_0", "--warmup", "0") as s:
        step("parity with the Python server (jevos-v2 q8_0, P within 0.15)", parity(s.url, golden / "jev-python-q8.json", "0.15"))
    with Server(args.jev, "--warmup", "0") as s:
        if args.record:
            step("record golden/jev.json", run(sys.executable, "parity.py", "--ref", s.url, "--record", golden / "jev.json"))
        elif args.exact:
            step("parity with a verified build (zero tolerance)", parity(s.url, golden / "jev.json", "0"))
        check_decide(args.jev, s.url)
        check_health(s.url)
    with Server(args.jev, "--warmup", "0", "--dynamic-quantization", "0") as s:
        step("snapshots, blocks, batching vs the plain oracle", run(sys.executable, "snapshots.py", "--target", s.url, "--model-dir", MODEL_DIR,
                                                                   "--dynamic-quantization", "0"))
    print(f"=== FAILED: {', '.join(failed)}" if failed else "=== every check passed", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
