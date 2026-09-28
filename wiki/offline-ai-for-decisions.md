---
title: "Offline AI for decisions: no network needed"
description: "After a one-time download, jevos answers yes/no questions with no network. What to fetch, how to carry it into an air-gapped network, how to verify it."
parent: "Local and private AI"
nav_order: 5
---

# Offline AI for decisions: no network needed

**Once the model file, the llama.cpp runtime and the Python dependencies are on the machine,
jevos needs no network to answer: `jev serve` and `jev decide` read local files and talk to
nobody.** The one-time download can happen on a connected machine, the files can be carried
into an air-gapped network, and each one can be checked against a published sha256 before it
is trusted. After that the decisions keep working with the cable unplugged.

The part people forget is the verification. An offline machine cannot re-download a file that
arrived corrupted or was swapped along the way, so the checksum is the only link between what
you run and what was published.

This page is what needs the network and when, what runs without it, how to move everything into
an isolated network, how to verify the files, and what being offline does not give you.

## What needs the network, and when?

Three downloads, all before the first decision:

| What | How | Size or note |
|---|---|---|
| Python dependencies | `uv sync` in a clone of the repo | resolved from the project's lock file |
| llama.cpp runtime | `uv run jev download --only runtime` | official prebuilt package, unpacked under `runtimes/` |
| Model file | from the [release page](https://github.com/feder-cr/jev/releases/tag/jevos) | `jevos-q4_k_m.gguf`, 619 MB |

The runtime step picks the package for the platform it runs on, from a llama.cpp release pinned
in the source, and checks each archive against a sha256 written in the code before unpacking
it. Nothing is compiled, which matters offline: there is no compiler toolchain to carry over.

## What runs with no network at all?

Everything that makes a decision. `jev serve` loads the model file you name with `--gguf` and
the runtime already under `runtimes/`; if either is missing it stops with an error telling you
to run `jev download`, rather than fetching anything. `jev decide` does the same for a single
request file. The server listens on `127.0.0.1:8017` by default, so the calls that follow go
over the loopback interface and never touch a network card.

The model answers from the text you send and nothing else. It has no lookup, no retrieval and
no call home, so there is no feature that quietly degrades when the connection disappears.
The whole mechanism is on [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Moving it into an air-gapped network

The pattern is to build the complete directory on a connected machine of the same operating
system and processor architecture, then carry it across.

1. On the connected machine, clone the repo, run `uv sync`, then
   `uv run jev download --only runtime`. The runtime package is chosen for that machine's
   platform, which is why the two machines should match.
2. Download `jevos-q4_k_m.gguf` and `SHA256SUMS.txt` from the release into the same directory.
3. Verify the model file there (next section), then copy the project directory, including the
   environment `uv sync` created and the `runtimes/` folder, onto the transfer medium.
4. On the isolated machine, verify the model file again after the copy, then start the server.
5. Test the whole sequence once with the network disabled before you depend on it. Tooling that
   tries to reach a package index on start-up is easier to find in a rehearsal than in an
   incident.

If your security process requires building the runtime yourself, the source accepts a
`JEV_LLAMA_DIR` environment variable pointing at a llama.cpp build of the same pinned commit;
the trade-offs of prebuilt against self-built are on
[using llama.cpp prebuilt binaries instead of building](llama-cpp-prebuilt-binaries.md).

## How do you verify the files?

`SHA256SUMS.txt` lists one line per release file: the hash, a space, and the file name with a
`*` in front, which is the format `sha256sum` writes and reads. On Linux, from the directory
holding the files:

```bash
sha256sum --check --ignore-missing SHA256SUMS.txt
```

`--check` reads the hashes from the file and checks each listed file; `--ignore-missing` skips
release files you did not download, such as the other quantization.

On Windows, PowerShell's `Get-FileHash` computes SHA256 by default:

```powershell
Get-FileHash .\jevos-q4_k_m.gguf
```

Compare the `Hash` it prints with the line for that file in `SHA256SUMS.txt`. The sums file
writes hashes in lower case and the Microsoft examples show upper case; the letters differ, the
hash does not.

Then check what the server actually loaded. `GET /health` reports the sha256 of the model file,
the llama.cpp release and a fingerprint of the whole setup. Writing that fingerprint into every
decision log ties each answer to a verified file, as described on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## What offline does not give you

- **Security by itself.** An isolated machine still needs access control. If the server binds
  to a network interface inside the enclave, set `JEV_API_KEY` so every call except `/health`
  needs a Bearer token.
- **Updates.** A new model or runtime has to come in the same way, verified the same way, and
  tested on your own labelled cases before it replaces the old one.
- **A fallback.** Offline there is no hosted model to escalate uncertain cases to. The
  uncertain middle goes to a person, or waits. If you plan an escalation path like the one on
  [a model cascade: small model first](model-cascade-small-model-first.md), it needs a
  connected side.
- **More capability.** The model is the same one: English only, yes/no only, 0.815 on 2,000
  questions about unseen business policies against 0.927 for the hosted Jev. Offline changes
  where it runs, not what it knows.

## Short answers to the questions that lead here

**Can an LLM run completely offline?** Yes, once its files are on the machine. jevos needs the
network only to download the dependencies, the runtime and the model.

**Does jevos phone home?** The serve and decide commands read local files and answer on
`127.0.0.1`; the downloads happen only when you run `jev download` or fetch the release.

**How do I check the model file is genuine?** Compare its sha256 with `SHA256SUMS.txt` from
the release, using `sha256sum --check` or `Get-FileHash`, then confirm the hash `/health`
reports.

**Can I copy the setup between machines?** Between machines of the same operating system and
architecture, yes: the runtime package is platform-specific.

**Does it need a GPU offline?** No. It is built for `--device cpu`.

**See also:** [self-hosted AI for decisions](self-hosted-ai-for-decisions.md),
[edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md) and
[what is GGUF](what-is-gguf.md).

## Sources

- Commands, endpoints and file sizes: the [jev README](https://github.com/feder-cr/jev). The
  format of `SHA256SUMS.txt` is read from the file on the jevos release.
- Pinned runtime, sha256 checks, `runtimes/`, `JEV_LLAMA_DIR`, and the error on a missing model
  file: read from `src/jev/runtime/llama_release.py`, `src/jev/loader.py` and
  `src/jev/engine/backend.py`.
- `sha256sum` options: [sha256sum(1) on man7.org](https://man7.org/linux/man-pages/man1/sha256sum.1.html),
  fetched 2026-09-29.
- `Get-FileHash` and its SHA256 default: [Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose release ships a sums file next
to the model so the check above is one command.*
