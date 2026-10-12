---
title: "Download a GGUF model from Hugging Face"
description: "Download one GGUF file or a folder from a Hugging Face repo with hf download or curl, pick a quantization, check the SHA-256, then run it in llama.cpp."
parent: "llama.cpp and GGUF"
nav_order: 9
---

# Download a GGUF model from Hugging Face

**To download one GGUF file from a Hugging Face repo, install the `hf` command line tool and run
`hf download <user>/<repo> <file>.gguf --local-dir .`; for a folder, add `--include "folder/*"`
instead of a file name.** Without the tool, every file has a direct address,
`https://huggingface.co/<user>/<repo>/resolve/main/<file>`, which curl downloads with `-L`. Then
compare the file's SHA-256 with a hash you trust and give the path to llama.cpp with `-m`. For
jevos the first step is `hf download feder-cr/jev jevos-v4-q4_k_m.gguf --local-dir .`.

The step people skip is the middle one. A GGUF file is the whole model, weights, tokenizer and
template, so its hash is the model's identity, as explained on
[what is GGUF](what-is-gguf.md). Checking it once after the download is what lets you say later
which model produced an answer.

This page is the one-file download, folders and patterns, the plain URL, choosing a
quantization, the hash check and the first run in llama.cpp, with feder-cr/jev as the example.

## How do I download a single GGUF file?

Install the CLI. The huggingface_hub CLI guide recommends a standalone installer (a PowerShell
one-liner on Windows, in the same guide) and notes that the CLI also ships with the Python
package:

```bash
curl -LsSf https://hf.co/cli/install.sh | bash      # macOS and Linux
pip install -U huggingface_hub                     # or with Python
```

Then name the repo and the file:

```bash
hf download feder-cr/jev jevos-v4-q4_k_m.gguf --local-dir .
```

Three details from the guide are worth knowing before the first run:

- **Where the file lands.** Without `--local-dir` it goes into the shared cache under `HF_HOME`,
  and the command prints the path on its last line. With `--local-dir` it lands in that folder
  in the repo's own layout, next to a `.cache/huggingface/` folder of metadata that stops a
  second run from downloading an unchanged file again.
- **Tokens.** Private or gated repos need a token, saved with `hf auth login`. feder-cr/jev is
  public.
- **Pinning.** `--revision` takes a branch, a tag or a commit hash, and the download guide warns
  that a commit hash must be the full-length one, not the 7-character short form.

## How do I download a folder or several files?

List the files after the repo name, or filter with `--include` and `--exclude` patterns. Adding
`--dry-run` lists what would be downloaded and how big it is, before any byte moves.

feder-cr/jev holds the `model/` folder that the `jev` binary runs (the same files as
`jevos-v4-openvino-int8.zip` in the GitHub release) and the two GGUF files. To put the model next
to the binary, unpack the binary archive from the release first (it creates `jev/`), then:

```bash
hf download feder-cr/jev --include "model/*" --local-dir jev
cd jev && ./jev serve
```

The files land in `jev/model/`, where the binary looks by default; on Windows the second line is
`cd jev` and `jev.exe serve`. The `model/` folder is the 8-bit OpenVINO build for `jev`, not a
GGUF, so it is not the thing to give llama.cpp.

## Can I download a GGUF without the hf tool?

Yes. Every file in a repo has a resolve URL; `hf_hub_url` in huggingface_hub builds that pattern,
and its documented example returns
`https://huggingface.co/julien-c/EsperBERTo-small/resolve/main/pytorch_model.bin`. For jevos:

```bash
curl -fL -C - -o jevos-v4-q4_k_m.gguf \
  https://huggingface.co/feder-cr/jev/resolve/main/jevos-v4-q4_k_m.gguf
```

`-L` is the flag that matters. The Hub docs explain that file contents are served from separate
storage and CDN hosts and that downloads follow HTTP redirects from huggingface.co to them; curl
only follows a redirect with `-L`. `-C -` lets curl work out where to resume an interrupted
transfer, useful for a 619,289,312-byte file, and `-f` makes an HTTP error fail instead of saving
an error page under the model's name.

Two more things. Replace `main` with a full commit hash to pin the exact version. And behind a
proxy, allowlisting huggingface.co alone is not enough, because the bytes come from those other
hosts; the Hub docs list them and publish them as JSON at
`https://huggingface.co/.well-known/meta.json`.

## Which quantization should I pick?

A GGUF repo often carries several quantizations of one model, named in the file name by
convention and recorded inside the file, where the Hub's GGUF viewer shows the metadata and
tensor types on the model page without a download. Fewer bits per weight means a smaller file:
the Hub's table puts Q4_K at 4.5 bits per weight. When you ask llama.cpp to fetch a repo without
naming a quantization, its server README says it picks Q4_K_M by default. What each name means is
on [GGUF quantization types explained](gguf-quantization-types-explained.md).

For jevos there are two files: `jevos-v4-q4_k_m.gguf` at 619,289,312 bytes and
`jevos-v4-q8_0.gguf` at 942,872,288. Start with q4_k_m. Whether the larger file answers better
has not been measured on one question set, so the reasons to move up, and how to test it on your
own questions, are on
[Q4_K_M vs Q8_0: speed and size for a small model](q4-k-m-vs-q8-0-speed-and-size.md).

## How do I check the SHA-256 of a downloaded GGUF?

Three ways, quickest first:

1. **Against the Hub.** `hf cache verify feder-cr/jev --local-dir .` checks local files against
   their checksums on the Hub and exits with a non-zero status on a mismatch. By default it warns
   about missing files, which is expected when you took one GGUF out of a repo.
2. **Against the release.** The Hugging Face files have the same SHA-256 as `SHA256SUMS.txt` in
   the GitHub release, a second host to compare with.
3. **By eye.** A large file's page on the Hub shows a "SHA256:" line.

For the second way, compute the hash and compare it with the file's line in `SHA256SUMS.txt`:

```bash
sha256sum jevos-v4-q4_k_m.gguf          # Linux
Get-FileHash .\jevos-v4-q4_k_m.gguf     # Windows PowerShell, SHA256 by default
```

Keep the hash after the check: it is the field that identifies the model in logs. The air-gapped
version of this routine is on [offline AI for decisions](offline-ai-for-decisions.md).

## How do I run the downloaded GGUF with llama.cpp?

Point llama.cpp at the file:

```bash
llama-server -m jevos-v4-q4_k_m.gguf
```

llama.cpp can also download from the Hub itself: `-hf <user>/<model>[:quant]` names the repo
(the quantization is optional and case-insensitive), and `-hff <file>` names an exact file. The
Hugging Face guide says those downloads go to llama.cpp's own cache, set by `LLAMA_CACHE`. We
show the two-step route because the file and its hash are then in front of you. Check the port
for the release you run: the server README fetched 2026-10-12 says `127.0.0.1:9931` by default,
while the Hugging Face guide's example calls `localhost:8080`. This file on llama.cpp, on a laptop
GPU, is what played our [Snake race against a cloud API](snake-ai-local-model-vs-cloud-api.md).

Being straight about what you get: the Hugging Face guide presents llama-server as an OpenAI-style
chat completions endpoint, not jev's decision API. Yes/no, choice and score answers with
probabilities in Jev's wire format come from the `jev` binary, which runs `model/` on the CPU and
does not read GGUF files. Building a P(yes) on llama-server yourself is on
[jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md), and getting a runtime without
compiling is on [using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md).

## Short answers to the questions that lead here

**How do I download only one file from a Hugging Face repo?** Run `hf download <repo> <file>
--local-dir .`, or fetch the resolve URL with `curl -L`.

**Where does hf download put the files?** In the cache under `HF_HOME` unless you pass
`--local-dir`. The last line it prints is the path.

**Do I need a Hugging Face account to download a GGUF?** Not for a public repo. Private and gated
repos need a token from `hf auth login`.

**Q4_K_M or Q8_0?** Q4_K_M is smaller, and llama.cpp takes it by default when `-hf` names no
quantization. For jevos, the two files have not been compared on one question set.

**Can jev run a GGUF file?** No. `jev` runs the OpenVINO `model/` folder; the GGUF files are for
llama.cpp and tools built on it.

**See also:** [llama.cpp on Windows without compiling](llama-cpp-on-windows.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[GGUF vs safetensors](gguf-vs-safetensors.md).

## Sources

- Our own facts: the files in feder-cr/jev, their sizes and matching `SHA256SUMS.txt`, and the
  `jev` commands, from the [jev README](https://github.com/feder-cr/jev) and
  [feder-cr/jev on Hugging Face](https://huggingface.co/feder-cr/jev) (file page fetched
  2026-10-12).
- [huggingface_hub CLI guide](https://huggingface.co/docs/huggingface_hub/guides/cli), fetched
  2026-10-12: installers, `hf download`, patterns, `--local-dir`, `--revision`, tokens,
  `hf cache verify`.
- [huggingface_hub download guide](https://huggingface.co/docs/huggingface_hub/guides/download)
  and [file download reference](https://huggingface.co/docs/huggingface_hub/package_reference/file_download),
  fetched 2026-10-12: full commit hashes, `--dry-run`, `hf_hub_url`.
- [Hub docs: downloading models](https://huggingface.co/docs/hub/models-downloading),
  [GGUF](https://huggingface.co/docs/hub/gguf) and
  [GGUF usage with llama.cpp](https://huggingface.co/docs/hub/gguf-llamacpp), fetched 2026-10-12:
  redirects and proxy hosts, the viewer, Q4_K bits per weight, `LLAMA_CACHE`, the port example.
- [llama-server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
  fetched 2026-10-12: `-m`, `-hf`, `-hff`, the default quantization and address.
- [curl man page](https://curl.se/docs/manpage.html),
  [Get-FileHash](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash)
  and [GNU sha2 utilities](https://www.gnu.org/software/coreutils/manual/html_node/sha2-utilities.html),
  fetched 2026-10-12.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose model sits on the Hub as one
folder for its own binary and two GGUF files for everything built on llama.cpp.*
