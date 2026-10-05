---
title: "Running LLM yes/no checks in GitHub Actions"
description: "An untested sketch for yes/no LLM checks in GitHub Actions: CPU runners, the jev binary and model, jev decide as a step, caching, assertions."
parent: "Integrations"
nav_order: 8
---

# Running LLM yes/no checks in GitHub Actions

**You can run local yes/no LLM checks on a standard GitHub-hosted runner, because they need a
CPU, not a GPU: download the jev binary and its model from the release, cache them, run
`jev decide` on request files as a step, and fail the job when a probability is on the wrong
side of its threshold.** GitHub documents its standard Linux runners at 4 CPUs and 16 GB of RAM
for public repositories and 2 CPUs and 8 GB for private ones, and jev runs on x86-64
Linux. The workflow below is an untested sketch: we have not run it, and you
should expect to adjust paths and versions.

The reason to do this in CI at all is that prompts and generated outputs change with every
commit, and a yes/no check ("does the reply still refuse to promise a refund?") catches the
regressions that string comparisons miss. The reason to do it locally rather than through a paid
judge is that it costs nothing per run and sends nothing to a third party.

This page is the workflow, what each step relies on, caching, how to write assertions that do
not flap, and what we have not measured. All snippets are minimal sketches to adapt; GitHub
and GitHub CLI facts are from their docs, fetched 2026-09-29.

## The workflow

```yaml
name: llm-checks
on: [pull_request]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/cache@v4
        with:
          path: jev
          key: jevos-v4-openvino-int8-linux-x64
      - name: Binary and model
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ ! -x jev/jev ]; then
            gh release download jevos-v4 --repo feder-cr/jev \
              -p 'jev-linux-x64.tar.gz' -p 'jevos-v4-openvino-int8.zip'
            tar -xzf jev-linux-x64.tar.gz
            (cd jev && unzip ../jevos-v4-openvino-int8.zip)
          fi
      - name: Decide
        run: |
          mkdir -p answers
          for f in checks/*.json; do
            jev/jev decide --threads 4 "$f" --output "answers/$(basename "$f")"
          done
      - name: Assert
        run: python3 checks/assert_answers.py answers
```

Your repository holds a `checks/` folder with one request file per case and a small script that
reads the answers and exits non-zero on a failed assertion.

## What each step relies on

- **One checkout.** Only your own repository is checked out. jev is one native binary, so the
  job installs no Python packages for it; the Linux build needs glibc 2.35 or later, which
  Ubuntu 22.04 and later runners have.
- **The release assets.** `gh release download` takes a tag, `--repo`, and `--pattern` for the
  assets to fetch; the `if` skips the download when a cache hit has restored the `jev/` folder.
  GitHub CLI is preinstalled on GitHub-hosted runners, and GitHub's docs say each step that uses
  it needs a `GH_TOKEN`.
- **The layout.** The tar file unpacks a `jev/` folder with the binary, OpenVINO's libraries and
  the licenses. The model zip, unpacked inside it, creates `jev/model`, where jev looks by
  default; `--model-dir` points it elsewhere.
- **The decision.** `jev decide` answers one request file without a server and exits.
  `--output` writes a new file and never overwrites an existing one. A request the server would
  refuse prints the error body on stderr and exits 1, which fails the step. Details are on
  [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).
- **Threads.** `--threads 4` matches the public-repository runner; use 2 on a private one.

To verify the downloads against the release's `SHA256SUMS.txt`, download that asset too and
check the lines of the two archives with your usual sha256 tool. That step matters more in CI than on a laptop,
because a cached file is reused silently for as long as the cache lives.

## Caching, and what invalidates it

`actions/cache` restores the listed paths when the key matches. GitHub's docs give a default of
10 GB of cache per repository and remove entries "that have not been accessed in over 7 days", so
the `jev/` folder with its model fits, and a repository with rare pull requests will
sometimes download again. Put everything that changes the files into the key: the release
(`jevos-v4`), the model format (`openvino-int8`) and the platform. When you move to a newer
release, change the key.

## Assertions that do not flap

A check that asserts `p > 0.5` on a case the model rates at 0.52 will fail on the next innocent
change. Three habits keep CI signal useful:

- **Assert with a margin.** Expect a yes above, say, 0.8 and a no below 0.2, and keep the cases in
  between out of the blocking set.
- **Prefer reading questions.** "Does the reply mention a refund?" is stable. "Is the total in the
  reply correct?" is arithmetic, where the first jevos scored 0.584 on our 999-question test (per-kind numbers for jevos-v4 are not published); compute
  totals in the test script instead, as
  [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) argues.
- **Report, then block.** Run the checks as non-blocking for a while, look at the distribution of
  probabilities, and promote only the stable ones. The wider method is on
  [LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md).

Rubric-style checks on generated answers (grounded, on topic, contradicts the context) follow the
patterns on [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md).

## What we have not measured

We have not timed jevos on a GitHub-hosted runner. Our latency figures, 28 ms for a short
request and 130 ms for a long one, are from an Intel Core Ultra 7 255H with 16 threads; a
4-CPU runner is likely slower, by an amount we do not know. We have also not timed the model load,
which every `jev decide` call pays. For more than a few dozen files, start `jev serve` in the
background in one step and post the requests to it in the next, so the model loads once.

## Short answers to the questions that lead here

**Can GitHub Actions run an LLM without a GPU?** A small one, yes. The standard runners GitHub
documents have no GPU listed, and jevos is built for the CPU.

**What does the job download?** Two release assets: `jev-linux-x64.tar.gz`, with the binary
and its libraries, and `jevos-v4-openvino-int8.zip`, the model.

**Does it need secrets?** Only `GITHUB_TOKEN` for `gh`, which GitHub provides. Nothing is sent to
a model provider.

**Is the workflow above tested?** No. It is a sketch built from the documented behaviour of each
piece; adapt it and run it on a branch first.

**Should I use jev decide or jev serve in CI?** `jev decide` for a handful of files; a background
`jev serve` when there are many.

**See also:** [building a yes/no test set for your own data](building-a-yes-no-test-set.md),
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md) and
[llama.cpp prebuilt binaries instead of building](llama-cpp-prebuilt-binaries.md).

## Sources

- The release assets and their layout, `jev decide` and `--output`: the
  [jev README](https://github.com/feder-cr/jev) and the
  [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v4). Latencies: the README.
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
  [dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
  and [using GitHub CLI in workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-github-cli),
  fetched 2026-09-29.
- [actions/checkout](https://github.com/actions/checkout),
  and [gh release download](https://cli.github.com/manual/gh_release_download), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. This page is labelled untested because it is; the pieces are documented, the whole
has not been run.*
