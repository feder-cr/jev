---
title: "Batch decisions from files with jev decide"
description: "Answer yes/no request files without a server: jev decide, --output that never overwrites, errors and exit status, and shell loops."
parent: "Integrations"
nav_order: 7
---

# Batch decisions from files with jev decide

**`jev decide` answers one request file and exits, with no server: `./jev decide request.json`
prints the answer, and `--output answer.json` writes it to a new file that is never
overwritten.** The file holds the same body you would POST to `/v1/systemone` and gets the same
answer shape back, printed as indented JSON. A request the server would refuse prints the
server's error body on stderr and exits with status 1. For a batch you loop over files in the
shell.

The catch is cost per file. Every `jev decide` run loads the model before answering, so a loop
over ten thousand small files pays the load ten thousand times. For large batches, one file with
many questions, or one `jev serve` and a client loop, is the better shape. We have not published
a load-time measurement, so measure it on your machine before you choose.

This page is the request file and its errors, what `--output` does and does not do, shell loops
for bash and PowerShell, and when to switch to the server. Commands and file shapes are minimal
sketches to adapt; every flag shown is one of `jev decide`'s options.

## One file, one answer

```bash
./jev decide request.json
```

With `request.json` holding the README's Quickstart body (`"model": "jev-latest"`, the
double-charge text and the `billing` question), the output is the same JSON the server returns,
which in the README reads `0.94` for `billing`, with `output_tokens` 0. A `model` name that is
neither a `jev-*` alias nor the served model's name is rejected, exactly as the server does it.

The options you are most likely to touch are the same as the server's: `--threads` (all logical
CPUs by default, fewer if other heavy programs run), `--model-dir` (the `model` folder beside the
binary by default), and `--ctx`, the context limit per question in tokens, the state plus that
question (default 8,192; longer prompts are rejected, not truncated).

## Errors and the exit status

A request the server would refuse, such as a malformed file, an unknown field or a text over
the context limit, is refused by `jev decide` too: it prints the server's error body, as JSON, on
stderr and exits with status 1, so a loop can tell answers from failures by the exit status.

Keep the request file and the answer file together when you need to reproduce or audit a
decision. What else belongs in such a record is on
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
  ./jev decide --threads 8 "$f" --output "$out" \
    || echo "failed: $f" >&2
done
```

```powershell
New-Item -ItemType Directory -Force answers | Out-Null
foreach ($f in Get-ChildItem requests\*.json) {
  $out = "answers\$($f.Name)"
  if (Test-Path $out) { continue }
  .\jev.exe decide --threads 8 $f.FullName --output $out
  if ($LASTEXITCODE -ne 0) { Write-Warning "failed: $($f.Name)" }
}
```

Run one loop at a time. Two loops on one CPU compete for the same cores, and each process loads
its own copy of the model; give the one process more `--threads` instead. The same caution applies when
you time a batch, see [measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Fewer, bigger files, or a server

Because each run pays the model load, the shape of the batch matters more than the loop:

- **Many questions about one text** belong in one file. Questions in a request share the state,
  which is read once; on the reference laptop three questions take about 66 ms together against
  49 ms for one alone. A request takes up to 1,024 questions.
- **Many texts** are better served by one `jev serve` process and a client that posts them one
  after another: the model loads once and each request costs only inference, 26 to 112 ms for 30
  to 191 tokens on an Intel Core Ultra 7 255H. The client side is on
  [a Python client for local LLM decisions](python-client-for-local-llm-decisions.md).
- **A handful of files in CI**, where starting and stopping a server is one moving part too many,
  is where `jev decide` is at its best; see
  [running LLM yes/no checks in GitHub Actions](github-actions-llm-checks.md).

## What jev decide is not built for

`jev decide` changes how you call the model, not what it knows. It reads English only, answers
yes/no and `choice` questions well and `score` questions less well (they are early), and is weakest on
questions that need arithmetic or dates. A batch makes errors at scale just as easily as it makes answers, so score a
labelled sample before you trust a whole run; how to build one is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md).

## Short answers to the questions that lead here

**Can I run jevos without a server?** Yes. `jev decide` answers one request file and exits.

**Does --output overwrite an existing file?** No. It refuses, prints an error and exits with
status 1.

**What happens with a request the server would refuse?** `jev decide` prints the server's error
body, as JSON, on stderr and exits with status 1.

**Is jev decide faster than the server for many files?** No. Each run loads the model; for many
texts, run the server once and post to it.

**How many questions can one file hold?** Up to 1,024, all sharing one state.

**See also:** [LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md),
[ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md) and
[curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md).

## Sources

- Every flag, the create-only output and the exit status: `jev decide` in
  [jev](https://github.com/feder-cr/jev).
- The Quickstart example and latencies: the [jev README](https://github.com/feder-cr/jev)
  (Intel Core Ultra 7 255H, 16 threads, through the HTTP API).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The output file is create-only because an answer file is evidence.*
