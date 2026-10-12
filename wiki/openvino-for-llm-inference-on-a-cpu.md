---
title: "OpenVINO for LLM inference on a CPU"
description: "What OpenVINO is, how to run a language model with it, why it is fast on a laptop CPU, how jev uses it, and when llama.cpp with GGUF fits better."
parent: "Speed"
nav_order: 13
---

# OpenVINO for LLM inference on a CPU

**OpenVINO is Intel's open-source toolkit for optimizing and running AI models; on a CPU it runs
a language model as a graph compiled for that processor, and it can compress the weights to 8
or 4 bits.** You convert a model to OpenVINO's IR format (an `.xml` file for the topology, a `.bin`
file for the weights), compile it for a device such as `CPU`, and run it through C++ libraries
with C and Python bindings. `jev` uses it to answer yes/no, choice and score questions with
jevos-v4: 28 ms for a short request and 130 ms for a long one on our reference laptop, no GPU.

The non-obvious part is that much of the speed is settled before the first request:
compilation does the device-specific work once, at load time, and 8-bit weights halve the bytes
each pass pulls from memory compared with 16-bit ones.

This page covers what OpenVINO is, the ways to run an LLM with it, why it is fast on a CPU, how
it picks threads, how jev uses it, and when llama.cpp is the better fit.

## What is OpenVINO?

Its repository calls it "an open source toolkit for optimizing and deploying AI inference",
under the Apache License 2.0. From its own pages:

- **Hardware:** CPUs (x86 and ARM), Intel integrated and discrete GPUs, Intel NPUs.
- **Model sources:** PyTorch, TensorFlow, ONNX, TensorFlow Lite, PaddlePaddle and JAX/Flax, and
  Hugging Face models through Optimum Intel.
- **Format:** OpenVINO IR. The `.xml` file "describes the model topology"; the `.bin` file
  "contains the weights and binary data".
- **Runtime:** "a set of C++ libraries with C and Python bindings". In each language you create
  a Core, compile the model for a device, create an inference request, run it, read the results.
- **CPUs in the system requirements:** Intel Core (6th to 14th generation, and Core Ultra), Xeon,
  Atom, ARM CPUs and Apple silicon, on 64-bit Windows, several Linux distributions and macOS.

## How do you run an LLM with OpenVINO?

OpenVINO's generative AI guide offers four routes:

| Route | What the docs say it is for |
|---|---|
| OpenVINO GenAI | "Suggested for production deployment for the supported use cases"; Python and C++; runs the generation loop, tokenization and scheduling |
| Optimum Intel | "Suggested for prototyping", and for production when GenAI does not cover the case; Hugging Face's interface; "Not usable for C++ applications" |
| Native OpenVINO API | possible for generative models, "although it is not recommended" |
| OpenVINO Model Server | REST endpoints for generative use cases, on CPU or GPU |

For a Hugging Face model, the short path is to export it and load the folder with GenAI
(commands from the GenAI README; we have not run them):

```bash
optimum-cli export openvino --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 --weight-format int4 --trust-remote-code TinyLlama_1_1b_v1_ov
```

```python
import openvino_genai as ov_genai
pipe = ov_genai.LLMPipeline("TinyLlama_1_1b_v1_ov", "CPU")
print(pipe.generate("What is OpenVINO?", max_new_tokens=100))
```

The model preparation guide says `--weight-format` also takes `int8`. GenAI is built around
generating text; a model that answers with a probability and writes nothing has no generation
loop to manage, the difference explained on
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## Why is OpenVINO fast for a small model on a CPU?

**Compilation, once.** `compile_model` "can potentially perform several time-consuming
device-specific optimizations and network compilations". That cost is paid at load, not per
request, and setting `cache_dir` saves the compiled model so the next start can skip most of it.
The CPU plugin fully supports dynamic shapes, but notes that "some runtime optimizations work
better when model shapes are known in advance".

**Smaller weights.** Weight compression, in OpenVINO's words, "improves inference speed by
reducing the latency of memory access when computing the operations with weights". On a CPU,
waiting for weights is often the real bottleneck, as
[what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md) explains. The
schemes themselves are on [INT8 weight quantization explained](int8-weight-quantization-explained.md).

**Precision per operation.** The CPU plugin uses u8 and i8 "for quantized operations only", and
warns that bf16 "may affect inference accuracy in LLM models".

## How many threads does OpenVINO use on a laptop?

Under its default LATENCY hint, OpenVINO decides for you: one stream, with inference threads set
to "the number of P-cores or P-cores+E-cores on one socket". Whether E-cores join depends on "the
model precision and the ratio of P-cores to E-cores"; on Intel Core Ultra processors on Windows
both kinds are used, "except in the case of large language models". Hyper-threading is off in
that scenario, and `ov::inference_num_threads` "limits the number of logical processors used for
CPU inference".

jev exposes the choice as `--threads`: all logical CPUs by default, fewer if other heavy apps
are running. We measured with 16 threads on a 16-thread Intel Core Ultra 7 255H. To tune it,
change one value at a time and compare medians, as on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## How does jev use OpenVINO?

`jev` is one native binary shipped with OpenVINO's libraries: no Python, no GPU. It runs
jevos-v4 with 8-bit weights from a model folder, `model` beside the binary unless `--model-dir`
says otherwise. That folder holds the IR pair, `openvino_model.xml` and `openvino_model.bin`, and
a tokenizer.

```bash
tar -xzf jev-linux-x64.tar.gz          # Windows: unzip jev-windows-x64.zip
cd jev
unzip ../jevos-v4-openvino-int8.zip     # creates model/
./jev serve --threads 8                 # Windows: jev.exe serve; listens on 127.0.0.1:8017
```

Measured on the reference laptop (Intel Core Ultra 7 255H, 16 threads; median of 10
requests through the HTTP API after 3 warm-up requests; measured with jevos-v3, which has the
same size and speed as jevos-v4):

| Request | Time |
|---|---|
| short, text read from scratch | 28 ms |
| long, text read from scratch | 130 ms |
| long, same text asked again | 22 ms |

Memory is about 1 GB with the model loaded, up to 1.4 GB with the text cache full. `/health`
reports the SHA-256 of each model file and a fingerprint of them all, so a logged answer can be
tied to the exact IR files, as described on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

Being straight about the limit: this is one laptop with an Intel CPU; we have published no
measurements on other processors.

## OpenVINO or llama.cpp: which should you use for jevos?

The release ships both; the choice is about the layer above the model.

- **`jev` (OpenVINO)** when you want the decision endpoint ready: yes/no, choice and score
  questions in TypeSafe Jev's wire format, several questions sharing one text, and the
  latencies above.
- **A GGUF file in llama.cpp** (`jevos-v4-q4_k_m.gguf`, 619,289,312 bytes, or
  `jevos-v4-q8_0.gguf`, 942,872,288 bytes) when your stack already runs llama.cpp or a tool built
  on it, or when you want a GPU: our game races ran the q4_k_m file in llama.cpp on a laptop GPU,
  not the CPU binary. You then write the prompt and the reading of P(yes) yourself, the gap
  listed on [jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md).

We have not timed the GGUF files on the reference CPU with the same method, so there is no
measured speed comparison of the two runtimes for jevos.

## Short answers to the questions that lead here

**Is OpenVINO free and open source?** Yes. The toolkit is under the Apache License 2.0.

**Does OpenVINO need an Intel GPU?** No. GPUs and NPUs are optional devices; jev uses only the
CPU.

**Does OpenVINO run on AMD or Apple processors?** Its README says CPU (x86, ARM); the system
requirements list Intel CPUs, ARM CPUs and Apple silicon and do not name AMD. jev ships a macOS
arm64 build; we have published no AMD measurements.

**Can I run a Hugging Face LLM with OpenVINO?** Yes: export it with `optimum-cli export openvino`,
with `--weight-format int8` or `int4` if you want compressed weights, then load it with OpenVINO
GenAI or Optimum Intel.

**Is OpenVINO faster than llama.cpp?** It depends on the model, the CPU and the work; we have not
compared the two on jevos with one method.

**See also:** [CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[Q4_K_M vs Q8_0: speed and size](q4-k-m-vs-q8-0-speed-and-size.md).

## Sources

- Our own facts and measurements: the [jev README](https://github.com/feder-cr/jev) and the
  [jevos-v4 release](https://github.com/feder-cr/jev/releases/tag/jevos-v4); GGUF byte sizes from
  [the Hugging Face model page](https://huggingface.co/feder-cr/jev); the game races, 2026-10-09.
- All fetched 2026-10-12:
  [OpenVINO README](https://github.com/openvinotoolkit/openvino);
  [IR format](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/documentation/openvino-ir-format.rst);
  [running inference](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/running-inference.rst);
  [generative AI workflow](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow-generative.rst)
  and [model preparation](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow-generative/genai-model-preparation.rst);
  [OpenVINO GenAI README](https://github.com/openvinotoolkit/openvino.genai) (the code);
  [model caching](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/running-inference/optimize-inference/optimizing-latency/model-caching-overview.rst);
  [CPU device](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/running-inference/inference-devices-and-modes/cpu-device.rst);
  [performance hints](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/running-inference/optimize-inference/high-level-performance-hints.rst)
  and [thread scheduling](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/running-inference/inference-devices-and-modes/cpu-device/performance-hint-and-thread-scheduling.rst);
  [system requirements](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/about-openvino/release-notes-openvino/system-requirements.rst);
  [weight compression](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/model-optimization-guide/weight-compression.rst).

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships the same model as
OpenVINO IR files and as GGUF, and has timed only the first on a CPU.*
