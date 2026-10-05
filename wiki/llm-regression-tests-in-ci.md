---
title: "LLM regression tests in CI with yes/no checks"
description: "Turn LLM output checks into CI tests: run jev decide on request files, assert on P(yes) with margins, and keep flaky results out of the build."
parent: "Evaluation"
nav_order: 4
---

# LLM regression tests in CI with yes/no checks

**An LLM regression test in CI is a fixed set of inputs, your system's outputs for them, and a
list of yes/no checks on each output, asserted as thresholds on P(yes).** With jevos, `jev
decide` answers one request file without a server, so a CI step can judge every output on a CPU
runner and fail the build when a check that used to pass drops below its bar. The judge adds no
per-token cost and no data leaves the runner.

What makes these tests usable is the margin. A check that asserts P(yes) above 0.5 will flip on
and off for outputs that sit near 0.5, and a test suite that flips is a test suite people learn
to ignore. The fix is a pass band, a fail band and a warning band in between.

This page is the shape of a check, the files and the loop, assertions with margins, the causes of
flaky results, how to pin the judge so its answers are comparable over time, and what to keep out
of CI.

## What is being tested, exactly?

Two things change in an LLM application: your prompts, retrieval and code, and the model behind
them. A regression test catches either one making outputs worse on properties you care about:

- "Does the reply ask the customer for their order number?"
- "Does the reply promise a refund?" (which it must not, for this input)
- "Is the tone of the reply polite?"
- "Does the summary mention the cancellation date?"

Each is a property you can name and read in the output, which is the kind of criterion a small
judge handles well. How to write them is on
[rubric design for an LLM judge](rubric-design-for-an-llm-judge.md). A check such as "is the
total in the reply correct?" is arithmetic, and belongs in an ordinary unit test that compares
numbers.

## The files

A CI job has two stages. First your application produces outputs for a fixed list of inputs and
writes one request file per case. Then the judge answers each file.

```json
{
  "model": "jev-latest",
  "state": {
    "customer_message": "My parcel never arrived and the tracking has not moved in a week.",
    "reply": "Sorry about that. Could you send me your order number so I can check with the courier?"
  },
  "questions": {
    "asks_order_number": {"type": "noul", "instructions": "Does the reply ask the customer for their order number?"},
    "promises_refund":   {"type": "noul", "instructions": "Does the reply promise the customer a refund?"},
    "polite":            {"type": "noul", "instructions": "Is the tone of the reply polite?"}
  }
}
```

Keep the expectations out of the request, in a sidecar file per case, so the request stays the
documented body of `POST /v1/systemone`:

```json
{"asks_order_number": "yes", "promises_refund": "no", "polite": "yes"}
```

## Running the judge

```bash
mkdir -p answers
for f in cases/*.request.json; do
  name=$(basename "$f" .request.json)
  jev/jev decide "$f" --output "answers/$name.json"
done
```

`--output` writes to a new file and never overwrites an existing one, so start each job with an
empty `answers` directory. The answer file has the same shape as a server response, with one
probability per question under `answers`.

Each run of `jev decide` starts from the model file. For a suite of hundreds of cases it can be
simpler to start `jev serve` once in the job, wait until `GET /health` reports ready, and post the
files to it. We have not measured the start-up cost of `jev decide`, so measure it on your runner
before choosing. Runner setup, downloading the model and caching it, is on
[running LLM yes/no checks in GitHub Actions](github-actions-llm-checks.md).

## Assertions with margins

```python
import json, pathlib, sys

PASS, FAIL = 0.7, 0.3          # tune on your own labelled cases
failed, warned = [], []
for exp in pathlib.Path("cases").glob("*.expect.json"):
    name = exp.name.removesuffix(".expect.json")
    got = json.loads(pathlib.Path(f"answers/{name}.json").read_text())["answers"]
    for q, want in json.loads(exp.read_text()).items():
        p = got[q]["noul"]
        ok = p >= PASS if want == "yes" else p <= FAIL
        bad = p <= FAIL if want == "yes" else p >= PASS
        if bad:
            failed.append(f"{name}.{q} = {p:.2f}")
        elif not ok:
            warned.append(f"{name}.{q} = {p:.2f}")
print("\n".join(["FAIL " + x for x in failed] + ["WARN " + x for x in warned]))
sys.exit(1 if failed else 0)
```

Three outcomes per check: clearly right (pass), clearly wrong (fail the build), and in between
(warn, and show it in the job summary). The warning band is where a person should look, and it is
also where the judge itself is least reliable. Choosing the two numbers from labelled cases, rather
than guessing them, is the subject of
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

Make the bands asymmetric where the error costs are. The first jevos leaned toward yes on questions it
could not work out (per-kind numbers are not published for jevos-v4), so an expected-yes check deserves a higher pass bar than an expected-no check deserves a
low one.

## Why LLM tests are flaky, and what to do

Most flakiness in these suites does not come from the judge:

- **The system under test samples.** If your generator runs with a non-zero temperature, the same
  input gives different outputs, and a check can legitimately pass on one and fail on another.
  Either fix the generator's sampling for the test run, or generate several outputs per case and
  assert on the pass rate.
- **Outputs near a threshold.** Handled by the warning band.
- **Checks that are really two checks.** "Is the reply polite and does it ask for the order
  number?" fails for two reasons and passes for one. Split it.
- **A changed judge.** If the model file or the runtime changes, scores move. See the next
  section.

When a check flips, look at the output before touching the threshold. A threshold nudged until
the build is green is a test that no longer tests anything.

## Pin the judge

A regression suite compares today's outputs with yesterday's, and that only works if the judge is
the same. Pin the model file by name and check it against the release's `SHA256SUMS.txt` in the
job. If you use `jev serve`, `GET /health` reports the model's fingerprint, which you can print
into the job log. Upgrade the judge in its own commit, re-run the
suite, and review the scores that moved, the same way you would review a dependency upgrade.

## What to keep out of CI

- **The final evaluation of a release.** CI checks catch regressions; they do not tell you how
  good the system is. That needs a proper test set, described on
  [building a yes/no test set](building-a-yes-no-test-set.md).
- **Checks the judge is weak on.** Numbers, dates and sums go into ordinary code assertions.
- **Non-English outputs.** jevos reads English only.
- **Latency benchmarks on shared runners.** CI machines are shared and noisy; a judge timing from
  one run says little.

## Short answers to the questions that lead here

**How do I test LLM outputs in CI?** Write yes/no checks for the properties you care about, run a
judge on each output, and assert on the probabilities with a pass band, a fail band and a warning
band between them.

**Do I need a GPU in CI?** No. jevos runs on the CPU with about 1 GB of memory.

**Why do my LLM tests pass and fail at random?** Usually because the system under test samples,
or because outputs sit near a single threshold. Fix the sampling and add a warning band.

**Should the judge run as a server or per file?** `jev decide` needs no server; for large suites,
one `jev serve` per job may be simpler. Measure both on your runner.

**How do I know the judge did not change?** Pin the model file, verify it against
`SHA256SUMS.txt`, and log the fingerprint that `/health` reports.

**See also:** [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md),
[LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md) and
[LLM judge bias and how to control it](llm-judge-bias.md).

## Sources

- `jev decide`, `--output`, `/health` and `SHA256SUMS.txt`: the
  [jev README](https://github.com/feder-cr/jev) and the
  [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- The lean toward yes: our 999-question test set, measured on the first jevos.
- The shell and Python snippets are sketches written for this page, not tested scripts.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose `--output` flag never
overwrites an existing file, which is the behaviour you want from a test result.*
