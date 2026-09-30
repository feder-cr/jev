"""The tokenizer against the token ids it gave before: `jev` must keep the Python engine's tokens.

    python tests/tokenizer.py [--test build/tokenizer-test]      check (exit 1 on any difference)
    python tests/tokenizer.py --reference                        record, from a build without the patch
    python tests/tokenizer.py --complete                         complete the record, from a patched build

The texts are tokenizer_corpus.py's; golden/tokens.json holds a SHA-256 of each text's token ids. They were
recorded from llama.cpp's own std::regex pre-tokenizer (MSVC, Windows), the one the Python engine ran, for
every text it could tokenize. On long single words it cannot: MSVC's std::regex gives up (error_complexity)
and libstdc++'s overflows the stack, which is why `jev` builds llama.cpp with a pre-tokenizer that does not
recurse (third_party/llama-minicpm5-split.patch). For those texts ("split_only") the record is that
pre-tokenizer's ids, which must stay the same on every OS; for all the others it must match std::regex.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from common import MODEL_DIR
from tokenizer_corpus import corpus

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden" / "tokens.json"


def tokenize(test, texts):
    """One entry per text: the SHA-256 of its token ids, or None when the tokenizer refused it."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        for t in texts:
            f.write(json.dumps(t) + "\n")
    try:
        out = subprocess.run([str(test), str(MODEL_DIR / "tokenizer.gguf"), f.name], capture_output=True, check=True).stdout
    finally:
        Path(f.name).unlink()
    lines = out.decode().split("\n")[:-1]
    assert len(lines) == len(texts), (len(lines), len(texts))
    return [None if line.startswith("error: ") else hashlib.sha256(line.encode()).hexdigest() for line in lines]


def shown(text):
    return f"{text[:60]!r}{'...' if len(text) > 60 else ''} ({len(text)} characters)"


def main():
    exe = ".exe" if platform.system() == "Windows" else ""
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=Path, default=HERE.parent / "build" / f"tokenizer-test{exe}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--reference", action="store_true")
    mode.add_argument("--complete", action="store_true")
    args = ap.parse_args()
    texts = corpus()
    got = tokenize(args.test, texts)
    if args.reference:
        GOLDEN.write_text(json.dumps({"digests": got, "split_only": []}, indent=0) + "\n", encoding="utf-8")
        print(f"kept {sum(d is not None for d in got)} of {len(texts)} texts; std::regex refused {sum(d is None for d in got)}")
        return
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(golden["digests"]) == len(texts), "the corpus changed: record again"
    bad = [i for i, (g, d) in enumerate(zip(golden["digests"], got)) if d is None or (g is not None and g != d)]
    for i in bad[:10]:
        print(f"FAIL text {i}: {shown(texts[i])}: {'refused' if got[i] is None else 'other token ids'}")
    if args.complete and not bad:
        for i, g in enumerate(golden["digests"]):
            if g is None:
                golden["digests"][i] = got[i]
                golden["split_only"].append(i)
        GOLDEN.write_text(json.dumps(golden, indent=0) + "\n", encoding="utf-8")
        print(f"completed: {len(golden['split_only'])} texts std::regex refused now hold this build's ids")
    elif not args.complete:
        missing = [i for i, g in enumerate(golden["digests"]) if g is None]
        if missing:
            print(f"FAIL {len(missing)} texts have no recorded ids: run --complete")
            bad += missing
    print(f"{len(texts) - len(bad)}/{len(texts)} texts give the recorded token ids")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
