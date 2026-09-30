"""What the tests read from outside this folder, in one place; environment variables set it.

    JEV_MODEL_DIR      the served model folder (default: dist/jev/model, where scripts/build.py's folder
                       expects it); its tokenizer.json, the HF tokenizer, is tests/snapshots.py's oracle
    JEV_QUESTION_SET   the 999 hand-written questions (state, question, answer per item), for the
                       benchmarks' accuracy; not in this repository
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_DIR = Path(os.environ.get("JEV_MODEL_DIR", HERE.parent / "dist" / "jev" / "model"))
HF_TOKENIZER = MODEL_DIR / "tokenizer.json"


def question_set():
    path = os.environ.get("JEV_QUESTION_SET")
    if not path:
        sys.exit("set JEV_QUESTION_SET to the 999-question set (a JSON list of state, question, answer)")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
