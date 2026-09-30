"""From optimum-intel's stateful OpenVINO export of jevos to the graph `jev` runs.

Each transform takes and returns an ov.Model and derives what it needs (answer token ids, layer
count, projection sizes, head counts) from the graph, the weights or the tokenizer. In order:

  answer_head          logits = the two answer rows ("0", "1") of the head, at `logit_index` [K]
                       instead of the whole vocabulary at every position
  explicit_mask        the additive attention mask becomes an input `attention_bias` [1,1,T,W]
                       (0 = may look, -inf = may not): several questions, states and requests
                       share one call, each seeing only its own cells
  drop_cache           no KV cache in the graph: every call is one fresh read
  last_layer_at_answers  the last layer's queries, attention, MLP, norm and head only at the answer
                       rows (its keys/values still for every token)
  fuse_projections     q/k/v and MLP gate/up read their shared input in one matmul each
  kv_io                keys/values as plain inputs (past_key.N, past_value.N) and outputs
                       (present_key.N, present_value.N): snapshots the server owns
  fold_gqa             no grouped-query expansion: the query heads that share a key/value head
                       become extra query rows of that head, the mask repeated for them (the
                       expansion copied every cell 8 times in every layer: 30% of a call resuming
                       from 4000 cells; the same arithmetic, identical outputs)

export/export_openvino.py runs them all and validates the result.
"""

import re

import numpy as np
import openvino as ov

try:
    import openvino.opset13 as ops
except ImportError:  # older layout
    import openvino.runtime.opset13 as ops


def _sdpa(model):
    return [op for op in model.get_ordered_ops() if op.get_type_name() == "ScaledDotProductAttention"]


def _layer(name):
    return int(re.search(r"\.layers\.(\d+)[./]", name).group(1))


def _param(model, name):
    return next((p for p in model.get_parameters() if p.get_friendly_name() == name), None)


def answer_head(model, rows):
    """`rows` [2, hidden] f32: the head rows of the answer tokens "0" and "1"."""
    result = model.get_results()[0]
    matmul = result.input_value(0).get_node()
    while matmul.get_type_name() != "MatMul":  # e.g. a Convert after the head's MatMul
        matmul = matmul.input_value(0).get_node()
    hidden = matmul.input_value(0)
    index = ops.parameter(ov.PartialShape([-1]), ov.Type.i64, name="logit_index")
    index.get_output_tensor(0).set_names({"logit_index"})
    picked = ops.gather(hidden, index, ops.constant(np.array(1, np.int64)))
    if hidden.get_element_type() != ov.Type.f32:
        picked = ops.convert(picked, ov.Type.f32)
    logits = ops.matmul(picked, ops.constant(np.asarray(rows, np.float32)), transpose_a=False, transpose_b=True)
    logits.get_output_tensor(0).set_names({"logits"})
    result.input(0).replace_source_output(logits.output(0))
    model.add_parameters([index])
    model.validate_nodes_and_infer_types()
    return model


def explicit_mask(model):
    sdpa = _sdpa(model)
    masks = {op.input_value(3).get_node().get_friendly_name() for op in sdpa}
    assert len(masks) == 1, f"expected one attention mask shared by the layers, found {len(masks)}"
    select = sdpa[0].input_value(3).get_node()
    assert select.get_type_name() == "Select", select.get_type_name()
    bias = ops.parameter(ov.PartialShape([-1, 1, -1, -1]), select.get_output_element_type(0), name="attention_bias")
    bias.get_output_tensor(0).set_names({"attention_bias"})
    for op in sdpa:
        op.input(3).replace_source_output(bias.output(0))
    model.add_parameters([bias])
    mask = _param(model, "attention_mask")
    if mask is not None:
        model.remove_parameter(mask)  # nothing reads it any more: the old mask subgraph is gone
    model.validate_nodes_and_infer_types()
    return model


def _from_read_value(output, depth=0):
    node = output.get_node()
    if node.get_type_name() == "ReadValue":
        return True
    return depth < 4 and any(_from_read_value(i.get_source_output(), depth + 1) for i in node.inputs())


def drop_cache(model):
    for op in model.get_ordered_ops():
        if op.get_type_name() == "Concat" and op.get_input_size() == 2 and _from_read_value(op.input_value(0)):
            new = op.input_value(1)
            for target in list(op.output(0).get_target_inputs()):
                if target.get_node().get_type_name() != "Assign":
                    target.replace_source_output(new)
    for sink in list(model.get_sinks()):
        model.remove_sink(sink)
    # a ReadValue still reachable (the empty cache's shape feeds position arithmetic) becomes that
    # empty cache as a constant: the CPU plugin wants every ReadValue paired with an Assign
    for op in model.get_ordered_ops():
        if op.get_type_name() == "ReadValue":
            ps = op.get_output_partial_shape(0)
            dims = [d.get_length() if d.is_static else (1 if i == 0 else 0) for i, d in enumerate(ps)]
            empty = ops.constant(np.zeros(dims, dtype=op.get_output_element_type(0).to_dtype()))
            for target in list(op.output(0).get_target_inputs()):
                target.replace_source_output(empty.output(0))
    # beam_idx picked the cache's rows per beam (Gather); on the empty cache of batch 1 that is the
    # constant itself, whose shape still feeds the position arithmetic
    beams = _param(model, "beam_idx")
    if beams is not None:
        live = {op.get_friendly_name() for op in model.get_ordered_ops()}  # the old cache's Gathers are dead
        for use in list(beams.output(0).get_target_inputs()):
            gather = use.get_node()
            if gather.get_friendly_name() not in live:
                continue
            assert gather.get_type_name() == "Gather" and use.get_index() == 1, gather.get_type_name()
            assert gather.input_value(0).get_node().get_type_name() == "Constant", gather.input_value(0).get_node().get_type_name()
            for target in list(gather.output(0).get_target_inputs()):
                target.replace_source_output(gather.input_value(0))
        model.remove_parameter(beams)
    model.validate_nodes_and_infer_types()
    assert not any(op.get_type_name() in ("ReadValue", "Assign") for op in model.get_ops())
    return model


def last_layer_at_answers(model):
    index = _param(model, "logit_index").output(0)
    last = _sdpa(model)[-1]
    n = _layer(last.get_friendly_name())
    by = {op.get_friendly_name(): op for op in model.get_ops()}
    head_gather = next(op for op in model.get_ops() if op.get_type_name() == "Gather" and op.input_value(1) == index)
    for slot in (0, 3):  # the queries and the mask rows of the answer tokens only
        src = last.input_value(slot)
        last.input(slot).replace_source_output(ops.gather(src, index, ops.constant(np.array(2, np.int64))).output(0))
    residual_add = by[f"__module.model.layers.{n}/aten::add/Add"]
    h = residual_add.input_value(0)
    assert f"layers.{n - 1}/aten::add/Add_1" in h.get_node().get_friendly_name(), h.get_node().get_friendly_name()
    residual_add.input(0).replace_source_output(ops.gather(h, index, ops.constant(np.array(1, np.int64))).output(0))
    for target in list(head_gather.output(0).get_target_inputs()):  # the head now receives exactly those rows
        target.replace_source_output(head_gather.input_value(0))
    model.validate_nodes_and_infer_types()
    return model


def _compressed(matmul):
    """(u8 weights, u8 zero points, f16 scales) behind a compressed matmul's weight input."""
    conv = matmul.input_value(1).get_node()
    mul = conv.input_value(0).get_node()
    sub = mul.input_value(0).get_node()
    scale = mul.input_value(1).get_node()
    w = sub.input_value(0).get_node().input_value(0).get_node()
    zp = sub.input_value(1).get_node().input_value(0).get_node()
    kinds = [n.get_type_name() for n in (conv, mul, sub, scale, w, zp)]
    assert kinds == ["Convert", "Multiply", "Subtract", "Constant", "Constant", "Constant"], kinds
    return w.get_data(), zp.get_data(), scale.get_data()


def _fuse(mms):
    x = mms[0].input_value(0)
    assert all(m.input_value(0) == x for m in mms)
    ws, zps, scs = zip(*(_compressed(m) for m in mms))
    dec = ops.multiply(ops.subtract(ops.convert(ops.constant(np.concatenate(ws, 0)), ov.Type.f16),
                                    ops.convert(ops.constant(np.concatenate(zps, 0)), ov.Type.f16)),
                       ops.constant(np.concatenate(scs, 0)))
    fused = ops.matmul(x, ops.convert(dec, ov.Type.f32), transpose_a=False, transpose_b=True)
    split = ops.variadic_split(fused, ops.constant(np.array(-1, np.int64)), ops.constant(np.array([w.shape[0] for w in ws], np.int64)))
    for k, m in enumerate(mms):
        for target in list(m.output(0).get_target_inputs()):
            target.replace_source_output(split.output(k))


def fuse_projections(model):
    by = {op.get_friendly_name(): op for op in model.get_ops()}
    for n in sorted({_layer(op.get_friendly_name()) for op in _sdpa(model)}):
        p = f"__module.model.layers.{n}"
        _fuse([by[f"{p}.self_attn.{x}_proj/ov_ext::linear/MatMul"] for x in ("q", "k", "v")])
        _fuse([by[f"{p}.mlp.{x}_proj/ov_ext::linear/MatMul"] for x in ("gate", "up")])
    model.validate_nodes_and_infer_types()
    return model


def _expansion(node):
    """Reshape <- Broadcast <- Unsqueeze: the grouped-query expansion of new keys or values."""
    assert node.get_type_name() == "Reshape", node.get_type_name()
    b = node.input_value(0).get_node()
    assert b.get_type_name() == "Broadcast", b.get_type_name()
    u = b.input_value(0).get_node()
    assert u.get_type_name() == "Unsqueeze", u.get_type_name()
    return b, u


def kv_io(model):
    params, results = [], []
    for op in _sdpa(model):
        n = _layer(op.get_friendly_name())
        q_heads = op.get_input_partial_shape(0)[1].get_length()
        for slot, kind in ((1, "key"), (2, "value")):
            bcast, unsq = _expansion(op.input_value(slot).get_node())
            new = unsq.input_value(0)
            kv_heads, head_dim = new.get_partial_shape()[1].get_length(), new.get_partial_shape()[3].get_length()
            past = ops.parameter([1, kv_heads, -1, head_dim], new.get_element_type(), name=f"past_{kind}.{n}")
            past.get_output_tensor(0).set_names({f"past_{kind}.{n}"})
            joined = ops.concat([past.output(0), new], 2)
            unsq.input(0).replace_source_output(joined.output(0))
            # the expansion's target shape came from the new tokens' count: take it from the joined cells
            group = np.array([1, 1, q_heads // kv_heads, 1, 1], np.int64)
            target = ops.multiply(ops.shape_of(unsq.output(0), ov.Type.i64), ops.constant(group))
            bcast.input(1).replace_source_output(target.output(0))
            res = ops.result(new)
            res.get_output_tensor(0).set_names({f"present_{kind}.{n}"})
            params.append(past)
            results.append(res)
    model.add_parameters(params)
    model.add_results(results)
    model.validate_nodes_and_infer_types()
    return model


def fold_gqa(model):
    masks = {}  # one repeated mask per mask source: layers 1-16 share the call's, the last layer has its own rows
    for op in _sdpa(model):
        q = op.input_value(0)
        q_heads, head_dim = q.get_partial_shape()[1].get_length(), q.get_partial_shape()[3].get_length()
        for slot in (1, 2):
            _, unsq = _expansion(op.input_value(slot).get_node())
            op.input(slot).replace_source_output(unsq.input_value(0))  # the joined cells, [1, kv heads, W, dim]
        kv_heads = op.get_input_partial_shape(1)[1].get_length()
        group = q_heads // kv_heads
        assert group * kv_heads == q_heads, (q_heads, kv_heads)
        # [1, q heads, T, dim] -> [1, kv heads, group * T, dim]: head g*group + r, token t -> row r*T + t of head g
        op.input(0).replace_source_output(ops.reshape(q, ops.constant(np.array([0, kv_heads, -1, head_dim], np.int64)), True).output(0))
        mask = op.input_value(3)
        key = (mask.get_node().get_friendly_name(), mask.get_index())
        if key not in masks:
            masks[key] = ops.tile(mask, ops.constant(np.array([1, 1, group, 1], np.int64)))  # row r*T + t sees what token t sees
        op.input(3).replace_source_output(masks[key].output(0))
        targets = list(op.output(0).get_target_inputs())
        back = ops.reshape(op.output(0), ops.constant(np.array([0, q_heads, -1, head_dim], np.int64)), True)
        for target in targets:
            target.replace_source_output(back.output(0))
    model.validate_nodes_and_infer_types()
    for op in _sdpa(model):  # keys and values straight from the joined cells, never expanded
        assert all(op.input_value(s).get_node().get_type_name() == "Concat" for s in (1, 2)), op.get_friendly_name()
    return model


def served_graph(model, rows):
    """All of it, in order: the optimum export in, the graph `jev` runs out."""
    for step in (lambda m: answer_head(m, rows), explicit_mask, drop_cache, last_layer_at_answers, fuse_projections, kv_io, fold_gqa):
        model = step(model)
    return model
