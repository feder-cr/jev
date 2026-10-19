# GPU serving via llama.cpp

An optional GPU backend for `jev serve`: the same `/v1/systemone` wire format, answers
computed by llama.cpp decoding a quantized GGUF instead of the OpenVINO graph. Built and
battle-tested as the default lane of a real-time demo (jev judging 10-15x/s in a browser
game loop, official 5x90s validation runs on it).

- `proxy.cpp` (~260 lines): HTTP server speaking jev's wire format. Reuses jev's own
  `wire`/`prompt`/`vocab`/`choice`/`score`/`request_tokens` sources unchanged; only the
  scoring backend differs. One llama.cpp decode per question, on top of the shared state
  prefix, with the KV cache rolled back in between — every question sees the state alone,
  the way jev's attention mask does. P(yes) is read from the raw logits:
  `sigmoid(logit("1") - logit("0"))`. (In the released weights the answer head is
  half-zero by design — `row("0") = 0` — so this equals `sigmoid(logit("1"))`.)
- `validate.py`: sends the same seeded scenario set to `jev serve` (CPU, port 8017) and
  the GPU proxy (port 8153), reports per-question decision agreement + mean |dP|, and
  measures p50/p95 for a short 1-question and a long 5-question request. Writes `results.json`.

## Receipts (RTX 4080 Laptop GPU, q4_k_m GGUF, llama.cpp b11541)

| metric | CPU `jev serve` | GPU lane | ratio |
|---|---|---|---|
| 1-question p50 | 292 ms | 22 ms | 13x |
| ~300-token state, 5 questions, p50 | 1372 ms | 73 ms | 19x |
| tokenizer parity (`usage.input_tokens`) | — | exact match on every request checked | — |
| decision agreement vs `jev serve` | — | 89% overall; 100% danger/dodge, 95-100% fire/spatial; mean \|dP\| 0.02-0.16 | — |

## Build

Get llama.cpp (pinned `b11541`, CUDA build) and the GGUF:

```bash
git clone --depth 1 --branch b11541 https://github.com/ggml-org/llama.cpp
cd llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j
# the GGUF is on Hugging Face: https://huggingface.co/feder-cr/jevos-v4 (q4_k_m quant)
```

Then, from `contrib/gpu-llama/`:

```bash
make LLAMA_DIR=/path/to/llama.cpp/build
# -> ./jev-gpu
```

## Run

```bash
./jev-gpu --model /path/to/jevos-v4-q4_k_m.gguf --port 8153
curl -s http://127.0.0.1:8153/v1/systemone -H 'Content-Type: application/json' -d '{
  "model":"jev-latest","state":"No bombs are in the air.",
  "questions":{"q":{"type":"noul","instructions":"Is a bomb dangerously close to the ship?"}}}'
```

Validate agreement + latency against a running `jev serve` on 8017:

```bash
python3 validate.py   # writes results.json
```

## Caveats

- **One client at a time.** Requests serialize on a mutex; a second concurrent client
  turns a 42 ms p50 into ~487 ms. This matches jev's `NUM_STREAMS=1` behavior on OpenVINO.
- No KV snapshots across requests: every request re-reads its state. (jev's OpenVINO
  server keeps state snapshots; that behavior is not replicated here.)
- Idle-GPU clocks: a cold GPU sits at ~210 MHz, and the first requests are 60% slower
  than warm steady state. Warm up before benchmarking.
- Quantization: numbers above are q4_k_m. Higher quants trade latency for agreement.
