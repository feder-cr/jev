---
title: "Batch decisions from files with jev decide"
description: "Answer yes/no request files without a server: jev decide, --output that never overwrites, the native request with full engine output, and shell loops."
parent: "Integrations"
nav_order: 7
---

# Batch decisions from files with jev decide

**`jev decide` answers one request file and exits, with no server: `uv run jev decide --gguf
jevos-v2-q4_k_m.gguf --device cpu request.json` prints the answer, and `--output answer.json`
writes it to a new file that is never overwritten.** A file with a `model` field is the same
body you would POST to `/v1/systemone` and gets the same answer shape back. A file without
`model` is read as the engine's native request and gets the engine's full output: probabilities,
prompt hashes and timings. For a batch you loop over files in the shell.

The catch is cost per file. Every `jev decide` run loads the model before answering, so a loop
over ten thousand small files pays the load ten thousand times. For large batches, one file with
many questions, or one `jev serve` and a client loop, is the better shape. We have not published
a load-time measurement, so measure it on your machine before you choose.

This page is the two kinds of request file, what `--output` does and does not do, shell loops
for bash and PowerShell, and when to switch to the server. Commands and file shapes are minimal
sketches to adapt; every flag shown is in `src/jev/cli.py`.

## One file, one answer

```bash
uv run jev decide --gguf jevos-v2-q4_k_m.gguf --device cpu request.json
```

With `request.json` holding the README's Quickstart body (`"model": "jev-latest"`, the
double-charge text and the `billing` question), the output is the same JSON the server returns,
which in the README reads `0.9` for `billing`, with `output_tokens` 0. The request is validated
before the weights are loaded, so a malformed file fails in a moment instead of after the model
is in memory. A `model` name that is neither a `jev-*` alias nor the served model's name is also
rejected before any inference, exactly as the server does it.

The options you are most likely to touch are the same as the server's: `--threads` (set it to
your core count, fewer if other heavy programs run), `--device cpu`, and `--ctx`, the context
limit per question in tokens (default 8,192; longer inputs are rejected, not truncated).

## The native request and the full output

Leave out `model` and the file is read as the engine's own request. Questions use the type
`boolean` instead of `noul`:

```json
{
  "state": "I was charged twice for the same order.",
  "questions": {
    "billing": {"type": "boolean", "instructions": "Is this a billing problem?"}
  }
}
```

The answer is the engine's output rather than the wire format. Per question it holds the
probabilities of both answers, a `prompt_sha256` of the exact prompt that was scored, and the
number of input tokens; for the whole request, the model metadata, the count of state tokens
shared by all the questions, and a `timing` block with queue, compile and total seconds next to
the backend's own timings.

That is the file to keep when you need to reproduce or audit a decision. The prompt hash tells
you whether two runs scored the same prompt, the metadata ties the answer to a model file, and
the timings separate model time from everything else. What else belongs in such a record is on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## --output never overwrites

`--output answer.json` creates the file, and its parent folders if needed, and refuses to write
if the file already exists: the command prints `jev: ...` with the error and exits with status 1.
The code's own comment gives the reason: results are create-only, so evidence is never silently
replaced.

Two consequences for batches:

- **Reruns are safe.** Point a second run at the same output folder and nothing already written
  is lost.
- **Check first.** The existence check happens when the answer is written, after the model has
  done the work. Skip existing outputs in your loop, as below, instead of letting each one fail
  at the end.

## Loops in bash and PowerShell

```bash
mkdir -p answers
for f in requests/*.json; do
  out="answers/$(basename "$f")"
  [ -e "$out" ] && continue
  uv run jev decide --gguf jevos-v2-q4_k_m.gguf --device cpu --threads 8 "$f" --output "$out" \
    || echo "failed: $f" >&2
done
```

```powershell
New-Item -ItemType Directory -Force answers | Out-Null
foreach ($f in Get-ChildItem requests\*.json) {
  $out = "answers\$($f.Name)"
  if (Test-Path $out) { continue }
  uv run jev decide --gguf jevos-v2-q4_k_m.gguf --device cpu --threads 8 $f.FullName --output $out
  if ($LASTEXITCODE -ne 0) { Write-Warning "failed: $($f.Name)" }
}
```

Run one loop at a time. Two loops on one CPU compete for the same cores, and each process loads
its own copy of the model, about 1.2 GB of memory; give the one process more `--threads` instead. The same caution applies when
you time a batch, see [measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Fewer, bigger files, or a server

Because each run pays the model load, the shape of the batch matters more than the loop:

- **Many questions about one text** belong in one file. Questions in a request share the state,
  which is read once; on the reference laptop three questions take about 165 ms together against
  103 ms for one alone. A request takes up to 1,024 questions.
- **Many texts** are better served by one `jev serve` process and a client that posts them one
  after another: the model loads once and each request costs only inference, 54 to 220 ms for 30
  to 190 tokens on an Intel Core Ultra 7 255H. The client side is on
  [a Python client for local LLM decisions](python-client-for-local-llm-decisions.md).
- **A handful of files in CI**, where starting and stopping a server is one moving part too many,
  is where `jev decide` is at its best; see
  [running LLM yes/no checks in GitHub Actions](github-actions-llm-checks.md).

## What jev decide is not built for

`jev decide` changes how you call the model, not what it knows. It reads English only, answers
yes/no questions only (`choice` and `score` are refused), and is weakest on questions that need
arithmetic or dates. A batch makes errors at scale just as easily as it makes answers, so score a
labelled sample before you trust a whole run; how to build one is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md).

## Short answers to the questions that lead here

**Can I run jevos without a server?** Yes. `jev decide` answers one request file and exits.

**Does --output overwrite an existing file?** No. It refuses, prints an error and exits with
status 1.

**How do I get prompt hashes and timings?** Leave `model` out of the file. The engine's native
request returns its full output, including `prompt_sha256` per question and a `timing` block.

**Is jev decide faster than the server for many files?** No. Each run loads the model; for many
texts, run the server once and post to it.

**How many questions can one file hold?** Up to 1,024, all sharing one state.

**See also:** [LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md),
[ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md) and
[curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md).

## Sources

- Every flag, the validation order, the create-only output, the exit status and the native
  request and output: read from `src/jev/cli.py`, `src/jev/engine/engine.py` and
  `src/jev/engine/schema.py` of [jev](https://github.com/feder-cr/jev).
- The Quickstart example and latencies: the [jev README](https://github.com/feder-cr/jev)
  (Intel Core Ultra 7 255H, 16 threads, `jevos-q4_k_m`).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The output file is create-only because an answer file is evidence.*
