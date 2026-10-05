---
title: "Offline AI for decisions: no network needed"
description: "After a one-time download, jevos answers yes/no questions with no network. What to fetch, how to carry it into an air-gapped network, how to verify it."
parent: "Local and private AI"
nav_order: 5
---

# Offline AI for decisions: no network needed

**Once the `jev` folder, with its binary, OpenVINO's libraries and the model, is on the machine,
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

Two downloads, both before the first decision, both from the
[release page](https://github.com/feder-cr/jev/releases/tag/jevos-v4):

| What | How | Size or note |
|---|---|---|
| jev binary | `jev-linux-x64.tar.gz`, `jev-windows-x64.zip` or `jev-macos-arm64.tar.gz` | a `jev/` folder with the binary, OpenVINO's libraries and the licenses |
| Model | `jevos-v4-openvino-int8.zip` | unpacked into the `jev` folder as `jev/model` |

Both are prebuilt archives. Nothing is compiled and nothing is installed, which matters
offline: there is no Python environment, package manager or compiler toolchain to carry over.

## What runs with no network at all?

Everything that makes a decision. `jev serve` loads the model from the `model` folder beside
the binary, or from the folder you name with `--model-dir`, and fetches nothing. `jev decide`
does the same for a single request file. The server listens on `127.0.0.1:8017` by default, so the calls that follow go
over the loopback interface and never touch a network card.

The model answers from the text you send and nothing else. It has no lookup, no retrieval and
no call home, so there is no feature that quietly degrades when the connection disappears.
The whole mechanism is on [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Moving it into an air-gapped network

The pattern is to download the release files on a connected machine, verify them, then carry
them across.

1. On the connected machine, download the archive for the isolated machine's platform
   (`jev-linux-x64.tar.gz`, `jev-windows-x64.zip` or `jev-macos-arm64.tar.gz`). Each archive is
   built for one operating system and processor architecture.
2. Download `jevos-v4-openvino-int8.zip` and `SHA256SUMS.txt` from the release into the same
   directory.
3. Verify the files there (next section), then copy them onto the transfer medium.
4. On the isolated machine, verify the files again after the copy, unpack the archive, unzip
   the model into the `jev` folder, then start the server.
5. Test the whole sequence once with the network disabled before you depend on it. A wrong
   archive or a missing file is easier to find in a rehearsal than in an incident.

If your security process requires building the binary yourself, the source is in the
[jev repository](https://github.com/feder-cr/jev). Do the build on the connected side and carry
the result across like the release archives; an isolated machine should use the release archives.

## How do you verify the files?

`SHA256SUMS.txt` lists one line per release file: the hash, a space, and the file name with a
`*` in front, which is the format `sha256sum` writes and reads. On Linux, from the directory
holding the files:

```bash
sha256sum --check --ignore-missing SHA256SUMS.txt
```

`--check` reads the hashes from the file and checks each listed file; `--ignore-missing` skips
release files you did not download, such as the GGUF files.

On Windows, PowerShell's `Get-FileHash` computes SHA256 by default:

```powershell
Get-FileHash .\jevos-v4-openvino-int8.zip
```

Compare the `Hash` it prints with the line for that file in `SHA256SUMS.txt`. The sums file
writes hashes in lower case and the Microsoft examples show upper case; the letters differ, the
hash does not.

Then check what the server actually loaded. `GET /health` reports the SHA-256 of each model file
and a fingerprint of them all. Writing that fingerprint into every
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
- **More capability.** The model is the same one: English only, yes/no, multiple choice and early scores; on the
  admission policy task it scored 0.95 on yes/no rules against 1.00 for the hosted Jev. Offline changes
  where it runs, not what it knows.

## Short answers to the questions that lead here

**Can an LLM run completely offline?** Yes, once its files are on the machine. jevos needs the
network only to download the binary and the model.

**Does jevos phone home?** The serve and decide commands read local files and answer on
`127.0.0.1`; the only downloads are the release files you fetch yourself.

**How do I check the model file is genuine?** Compare its sha256 with `SHA256SUMS.txt` from
the release, using `sha256sum --check` or `Get-FileHash`, then confirm the hashes `/health`
reports.

**Can I copy the setup between machines?** Between machines of the same operating system and
architecture, yes: each release archive is built for one platform.

**Does it need a GPU offline?** No. It runs on the CPU only.

**See also:** [self-hosted AI for decisions](self-hosted-ai-for-decisions.md),
[edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md) and
[what is GGUF](what-is-gguf.md).

## Sources

- Commands, endpoints and the build from source: the [jev README](https://github.com/feder-cr/jev).
  The format of `SHA256SUMS.txt` is read from the file on the jevos release.
- Release archives and what they contain: the
  [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- `sha256sum` options: [sha256sum(1) on man7.org](https://man7.org/linux/man-pages/man1/sha256sum.1.html),
  fetched 2026-09-29.
- `Get-FileHash` and its SHA256 default: [Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose release ships a sums file next
to the model so the check above is one command.*
