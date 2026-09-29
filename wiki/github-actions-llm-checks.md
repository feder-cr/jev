---
title: "Running LLM yes/no checks in GitHub Actions"
description: "An untested sketch for yes/no LLM checks in GitHub Actions: CPU runners, the GGUF and llama.cpp runtime, jev decide as a step, caching, assertions."
parent: "Integrations"
nav_order: 8
---

# Running LLM yes/no checks in GitHub Actions

**You can run local yes/no LLM checks on a standard GitHub-hosted runner, because they need a
CPU and about 1.2 GB of memory, not a GPU: download the release GGUF and the prebuilt llama.cpp
runtime, cache both, run `jev decide` on request files as a step, and fail the job when a
probability is on the wrong side of its threshold.** GitHub documents its standard Linux runners
at 4 CPUs and 16 GB of RAM for public repositories and 2 CPUs and 8 GB for private ones, which is
enough for a 619 MB model. The workflow below is an untested sketch: we have not run it, and you
should expect to adjust paths and versions.

The reason to do this in CI at all is that prompts and generated outputs change with every
commit, and a yes/no check ("does the reply still refuse to promise a refund?") catches the
regressions that string comparisons miss. The reason to do it locally rather than through a paid
judge is that it costs nothing per run and sends nothing to a third party.

This page is the workflow, what each step relies on, caching, how to write assertions that do
not flap, and what we have not measured. All snippets are minimal sketches to adapt; GitHub,
uv and GitHub CLI facts are from their docs, fetched 2026-09-29.

## The workflow

```yaml
name: llm-checks
on: [pull_request]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/checkout@v7
        with:
          repository: feder-cr/jev
          path: jev
      - name: Install uv
        uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0
      - uses: actions/cache@v4
        with:
          path: |
            jev/jevos-v2-q4_k_m.gguf
            jev/runtimes
          key: jevos-q4_k_m-llama-b11081-linux-cpu
      - name: Model and runtime
        working-directory: jev
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          uv sync
          gh release download jevos --repo feder-cr/jev -p 'jevos-v2-q4_k_m.gguf' --skip-existing
          uv run jev download --only runtime --runtime cpu
      - name: Decide
        working-directory: jev
        run: |
          mkdir -p ../answers
          for f in ../checks/*.json; do
            uv run jev decide --gguf jevos-v2-q4_k_m.gguf --device cpu --threads 4 \
              "$f" --output "../answers/$(basename "$f")"
          done
      - name: Assert
        working-directory: jev
        run: uv run python ../checks/assert_answers.py ../answers
```

Your repository holds a `checks/` folder with one request file per case and a small script that
reads the answers and exits non-zero on a failed assertion.

## What each step relies on

- **Two checkouts.** `actions/checkout` with `repository:` and `path:` puts the jev source next to
  your own, as in the action's documented example.
- **uv.** The uv docs' GitHub integration guide installs it with `astral-sh/setup-uv`, pinned to
  a commit as shown above; the README's own setup is `uv sync`.
- **The model file.** `gh release download` takes a tag, `--repo`, and `--pattern` for the assets
  to fetch; `--skip-existing` skips files already present, which is what a cache hit leaves. GitHub
  CLI is preinstalled on GitHub-hosted runners, and GitHub's docs say each step that uses it needs
  a `GH_TOKEN`.
- **The runtime.** `jev download --only runtime` fetches the official prebuilt llama.cpp for the
  platform, verifies it by sha256 and unpacks it under `runtimes/` in the working directory.
  `--runtime cpu` asks for the CPU build explicitly; left on `auto`, jev picks a GPU build (Vulkan
  on a Linux machine without an NVIDIA driver), which is not what a CPU runner needs.
- **The decision.** `jev decide` answers one request file without a server and exits.
  `--output` writes a new file and never overwrites an existing one. Details are on
  [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).
- **Threads.** `--threads 4` matches the public-repository runner; use 2 on a private one.

To verify the model file against the release's `SHA256SUMS.txt`, download that asset too and
check the GGUF's line with your usual sha256 tool. That step matters more in CI than on a laptop,
because a cached file is reused silently for as long as the cache lives.

## Caching, and what invalidates it

`actions/cache` restores the listed paths when the key matches. GitHub's docs give a default of
10 GB of cache per repository and remove entries "that have not been accessed in over 7 days", so
a model plus runtime of well under 1 GB fits, and a repository with rare pull requests will
sometimes download again. Put everything that changes the files into the key: the quantization
(`q4_k_m`), the pinned llama.cpp release (`b11081` in the current source, reported by `jev devices`
and by `/health` as `llama_cpp_release`), and the platform. When jev pins a newer release, change
the key.

## Assertions that do not flap

A check that asserts `p > 0.5` on a case the model rates at 0.52 will fail on the next innocent
change. Three habits keep CI signal useful:

- **Assert with a margin.** Expect a yes above, say, 0.8 and a no below 0.2, and keep the cases in
  between out of the blocking set.
- **Prefer reading questions.** "Does the reply mention a refund?" is stable. "Is the total in the
  reply correct?" is arithmetic, where our 999-question test put a small model at 0.584; compute
  totals in the test script instead, as
  [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) argues.
- **Report, then block.** Run the checks as non-blocking for a while, look at the distribution of
  probabilities, and promote only the stable ones. The wider method is on
  [LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md).

Rubric-style checks on generated answers (grounded, on topic, contradicts the context) follow the
patterns on [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md).

## What we have not measured

We have not timed jevos on a GitHub-hosted runner. Our latency figures, 54 ms for a 30-token
request and 220 ms for 190 tokens, are from an Intel Core Ultra 7 255H with 16 threads; a
4-CPU runner is likely slower, by an amount we do not know. We have also not timed the model load,
which every `jev decide` call pays. For more than a few dozen files, start `jev serve` in the
background in one step and post the requests to it in the next, so the model loads once.

## Short answers to the questions that lead here

**Can GitHub Actions run an LLM without a GPU?** A small one, yes. The standard runners GitHub
documents have no GPU listed, and jevos is built for the CPU.

**How big is the download?** The `q4_k_m` model file is 619 MB, plus the llama.cpp runtime.

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

- `jev download --only runtime --runtime`, the pinned release, the `runtimes/` directory,
  `jev decide` and `--output`: read from `src/jev/cli.py` and `src/jev/runtime/llama_release.py`
  of [jev](https://github.com/feder-cr/jev). Model size, memory and latencies: the README and
  the [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v2).
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
  [dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
  and [using GitHub CLI in workflows](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-github-cli),
  fetched 2026-09-29.
- [actions/checkout](https://github.com/actions/checkout),
  [gh release download](https://cli.github.com/manual/gh_release_download) and
  [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. This page is labelled untested because it is; the pieces are documented, the whole
has not been run.*
