"""Export jevos for `jev`: the OpenVINO model folder it serves, checked before it is kept.

    python export_openvino.py --hf HF_MODEL_DIR --gguf MODEL.gguf --name NAME --out OUT_DIR
                              [--weight-format int8] [--keep-work]

1. optimum-intel exports the HF model (stateful, weights compressed by NNCF);
2. jevos_graph.served_graph turns it into the served graph (answer head, explicit mask, no cache,
   last layer at the answers, fused projections, keys/values as inputs and outputs, no GQA copies);
3. OUT/tokenizer.gguf: the GGUF's metadata without its tensors, the vocabulary `jev` tokenizes with
   (llama.cpp's tokenizer: the Python engine's, and the HF one the model trained with);
   OUT/model.json: the name answers carry (NAME); OUT/tokenizer.json: the HF tokenizer, the tests' oracle;
4. validation: on 48 prompts, P(yes) of the served graph (one call per prompt, and all of them in
   one call as independent blocks) against optimum's own export reading its full-vocabulary logits.
   Any gap above 0.02 fails the export (exit 1) and keeps the work directory.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import gguf
import numpy as np
import openvino as ov
from safetensors.torch import load_file
from tokenizers import Tokenizer

import jevos_graph

CFG = {"INFERENCE_NUM_THREADS": 16, "PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1", "DYNAMIC_QUANTIZATION_GROUP_SIZE": 128}
WORDS = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon".split()


def sig(z):
    return 1 / (1 + math.exp(-z))


def answer_rows(hf):
    """The token ids of the answers "0" and "1", and their rows of the output layer."""
    tok = Tokenizer.from_file(str(hf / "tokenizer.json"))
    answer_ids = []
    for digit in ("0", "1"):
        ids = tok.encode(digit, add_special_tokens=False).ids
        assert len(ids) == 1, f"the answer digit {digit!r} is not one token"
        answer_ids += ids
    weights = {}
    for f in sorted(hf.glob("*.safetensors")):
        weights.update(load_file(f))
    head = weights.get("lm_head.weight", weights.get("model.embed_tokens.weight"))  # tied embeddings
    return tok, answer_ids, head[answer_ids].float().numpy()


def write_vocabulary(source_gguf, destination):
    """The GGUF's metadata (its vocabulary among it) without its tensors."""
    reader = gguf.GGUFReader(str(source_gguf))
    arch = reader.fields["general.architecture"]
    writer = gguf.GGUFWriter(str(destination), str(bytes(arch.parts[arch.data[0]]), "utf-8"))
    for name, field in reader.fields.items():
        if name in {"GGUF.version", "GGUF.tensor_count", "GGUF.kv_count", "general.architecture"}:
            continue
        vtype = field.types[0]
        if vtype == gguf.GGUFValueType.ARRAY:
            sub = field.types[-1]
            value = [str(bytes(field.parts[i]), "utf-8") for i in field.data] if sub == gguf.GGUFValueType.STRING else [field.parts[i].tolist()[0] for i in field.data]
            writer.add_key_value(name, value, vtype, sub_type=sub)
        elif vtype == gguf.GGUFValueType.STRING:
            writer.add_key_value(name, str(bytes(field.parts[field.data[0]]), "utf-8"), vtype)
        else:
            writer.add_key_value(name, field.parts[field.data[0]].tolist()[0], vtype)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()


def validate(core, out, optimum, tok, answer_ids):
    """The largest |dP| against optimum's export: one prompt per call, and all prompts in one call."""
    served = core.compile_model(out / "openvino_model.xml", "CPU", CFG).create_infer_request()
    reference_model = core.compile_model(optimum / "openvino_model.xml", "CPU", CFG)
    reference = reference_model.create_infer_request()
    pasts = {n: np.zeros((1, i.get_partial_shape()[1].get_length(), 0, i.get_partial_shape()[3].get_length()), np.float32)
             for i in served.model_inputs for n in i.get_names() if n.startswith("past_")}
    prompts = []
    for i in range(48):
        state = " ".join(f"Record {i}-{j}: {WORDS[(i + j) % 20]} reported {(i * j) % 17} issues." for j in range(1 + i % 12))
        prompts.append(tok.encode(f"<s><evidence>\n{state}\n</evidence>\n\nQuestion: Did {WORDS[i % 20]} report issues?\nAnswer:",
                                  add_special_tokens=False).ids)

    def ref_p(ids):
        reference.reset_state()
        n = len(ids)
        out = reference.infer({"input_ids": np.array([ids], np.int64), "attention_mask": np.ones((1, n), np.int64),
                               "position_ids": np.arange(n, dtype=np.int64)[None], "beam_idx": np.zeros(1, np.int32)})
        last = out[reference_model.output(0)][0, -1]
        return sig(float(last[answer_ids[1]]) - float(last[answer_ids[0]]))

    def served_ps(blocks):
        """One call over independent prompts (each its own causal block)."""
        T = sum(map(len, blocks))
        ids, pos, bias, idx, at = [], [], np.full((1, 1, T, T), -np.inf, np.float32), [], 0
        for b in blocks:
            n = len(b)
            ids += b
            pos += range(n)
            bias[0, 0, at:at + n, at:at + n] = np.where(np.tril(np.ones((n, n), bool)), 0, -np.inf)
            at += n
            idx.append(at - 1)
        feed = {"input_ids": np.array([ids], np.int64), "position_ids": np.array([pos], np.int64), "attention_bias": bias,
                "logit_index": np.array(idx, np.int64)} | pasts
        lg = served.infer(feed)["logits"].reshape(-1, 2)
        return [sig(float(x[1]) - float(x[0])) for x in lg]

    ref = [ref_p(p) for p in prompts]
    alone = [served_ps([p])[0] for p in prompts]
    together = served_ps(prompts)
    return max(abs(a - b) for a, b in zip(ref, alone)), max(abs(a - b) for a, b in zip(ref, together)), len(prompts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf", required=True, type=Path)
    ap.add_argument("--gguf", required=True, type=Path)
    ap.add_argument("--name", required=True, help="the model's name in answers, e.g. jevos-v2")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--weight-format", default="int8")
    ap.add_argument("--keep-work", action="store_true")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="jevos-export-"))
    optimum = work / "optimum"
    cli = Path(sys.executable).with_name("optimum-cli.exe" if sys.platform == "win32" else "optimum-cli")
    print(f"1/4 optimum export ({args.weight_format}) -> {optimum}", flush=True)
    subprocess.run([str(cli), "export", "openvino", "--model", str(args.hf), "--task", "text-generation-with-past",
                    "--weight-format", args.weight_format, str(optimum)], check=True)
    tok, answer_ids, rows = answer_rows(args.hf)

    print("2/4 served graph", flush=True)
    core = ov.Core()
    model = jevos_graph.served_graph(core.read_model(optimum / "openvino_model.xml"), rows)
    args.out.mkdir(parents=True, exist_ok=True)
    ov.save_model(model, args.out / "openvino_model.xml")

    print("3/4 vocabulary and name", flush=True)
    write_vocabulary(args.gguf, args.out / "tokenizer.gguf")
    shutil.copy2(args.hf / "tokenizer.json", args.out / "tokenizer.json")  # the tests' oracle tokenizes with it
    (args.out / "model.json").write_text(json.dumps({"name": args.name}) + "\n", encoding="utf-8")

    print("4/4 validation", flush=True)
    gap_alone, gap_together, count = validate(core, args.out, optimum, tok, answer_ids)
    print(f"   max |dP| vs optimum's export: one prompt per call {gap_alone:.4f}, all {count} in one call {gap_together:.4f}")
    if max(gap_alone, gap_together) > 0.02:
        print(f"validation FAILED; work directory kept: {work}")
        sys.exit(1)
    if args.keep_work:
        print(f"work directory kept: {work}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    print(f"exported {args.out}")


if __name__ == "__main__":
    main()
