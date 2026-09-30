#include "wire.hpp"

#include <algorithm>
#include <initializer_list>

#include "prompt.hpp"
#include "text.hpp"

static const size_t MAX_STATE_BYTES = 256000;
static const size_t MAX_QUESTIONS = 1024;
static const size_t MAX_TEXT = 8000;

static const char* DICT_LOC = "dict[str,json-or-python[json=any,python=tagged-union[list[...],dict[str,...],str,bool,int,float,none]]]";
static const char* LIST_LOC = "list[json-or-python[json=any,python=tagged-union[list[...],dict[str,...],str,bool,int,float,none]]]";
static const char* EXPECTED_TAGS = "'noul', 'choice', 'score'";
static const size_t MAX_CHOICE_OPTIONS = 26, MIN_SCORE_LEVELS = 2, MAX_SCORE_LEVELS = 10;

static std::string ctx_json(std::initializer_list<std::pair<const char*, Value>> kv) {
    Value d;
    d.kind = Value::Dict;
    for (auto& [k, v] : kv) d.dict.emplace_back(k, v);
    return pyjson::dumps(d, {-1, false, ",", ":", true});
}

// pydantic's recursion guard on JsonValue: every value 100 levels down (depth first), with its path:
// key or index, then the child's union tag ("list"/"dict"), down to the value itself.
// A limit hit on a container leaves pydantic's depth counter one higher for the rest of the request.
using DeepHit = std::pair<std::vector<Value>, const Value*>;
static thread_local int recursion_leak = 0;
static void too_deep(const Value& v, int depth, std::vector<Value>& path, std::vector<DeepHit>& out) {
    if (depth + recursion_leak >= 100) {
        out.emplace_back(path, &v);
        if (v.is_list() || v.is_dict()) ++recursion_leak;
        return;
    }
    auto child = [&](Value key, const Value& c) {
        path.push_back(std::move(key));
        bool tagged = depth + 1 + recursion_leak < 100 && (c.is_list() || c.is_dict());
        if (tagged) path.push_back(S(c.is_list() ? "list" : "dict"));
        too_deep(c, depth + 1, path, out);
        path.resize(path.size() - (tagged ? 2 : 1));
    };
    for (size_t i = 0; i < v.list.size(); ++i) child(I(i), v.list[i]);
    for (auto& kv : v.dict) child(S(kv.first), kv.second);
}

// Structured = str | dict[str, JsonValue] | list[JsonValue], optionally None
static void check_structured(const Value& v, const std::vector<Value>& loc, bool optional, Errs& errs) {
    if ((optional && v.is_null()) || v.is_str()) return;
    std::vector<DeepHit> deep;
    if (v.is_dict() || v.is_list()) {
        std::vector<Value> path;
        too_deep(v, 1, path, deep);
        if (deep.empty()) return;
    }
    auto recursion = [&](const char* member) {
        for (auto& [path, value] : deep) {
            std::vector<Value> at = L(loc, {S(member)});
            at.insert(at.end(), path.begin(), path.end());
            errs.push_back(wire_err("recursion_loop", at, "Recursion error - cyclic reference detected", *value));
        }
    };
    errs.push_back(wire_err("string_type", L(loc, {S("str")}), "Input should be a valid string", v));
    if (v.is_dict()) recursion(DICT_LOC);
    else errs.push_back(wire_err("dict_type", L(loc, {S(DICT_LOC)}), "Input should be a valid dictionary", v));
    if (v.is_list()) recursion(LIST_LOC);
    else errs.push_back(wire_err("list_type", L(loc, {S(LIST_LOC)}), "Input should be a valid list", v));
}

static const char* UNICODE_MSG = "Input should be a valid string, unable to parse raw data as a unicode string";

static void check_extras(const Value& obj, std::initializer_list<const char*> allowed, const std::vector<Value>& loc, Errs& errs) {
    for (auto& [k, v] : obj.dict) {
        bool ok = false;
        for (const char* a : allowed) ok |= k == a;
        if (!ok) errs.push_back(wire_err("extra_forbidden", L(loc, {S(k)}), "Extra inputs are not permitted", v));
    }
}

static std::string value_error_ctx() { return R"({"error":{}})"; }

// wire.Question, a union discriminated by `type`
static void check_question(const std::string& qid, const Value& q, Errs& errs) {
    std::vector<Value> at = {S("body"), S("questions"), S(qid)};
    if (!q.is_dict()) {
        errs.push_back(wire_err("model_attributes_type", at, "Input should be a valid dictionary or object to extract fields from", q));
        return;
    }
    const Value* t = q.get("type");
    if (!t) {
        errs.push_back(wire_err("union_tag_not_found", at, "Unable to extract tag using discriminator 'type'", q, ctx_json({{"discriminator", S("'type'")}})));
        return;
    }
    std::string tag = pyjson::str(*t);
    if (!t->is_str() || (tag != "noul" && tag != "choice" && tag != "score")) {
        errs.push_back(wire_err("union_tag_invalid", at,
                                "Input tag '" + tag + "' found using 'type' does not match any of the expected tags: " + EXPECTED_TAGS, q,
                                ctx_json({{"discriminator", S("'type'")}, {"tag", S(tag)}, {"expected_tags", S(EXPECTED_TAGS)}})));
        return;
    }
    std::vector<Value> base = L(at, {S(tag)});
    size_t before = errs.size();
    if (const Value* ins = q.get("instructions")) check_structured(*ins, L(base, {S("instructions")}), true, errs);
    const Value* crit = q.get("criteria");
    std::vector<Value> cloc = L(base, {S("criteria")});
    if (tag == "noul") {
        if (crit && !crit->is_null()) {
            if (!crit->is_dict()) {
                errs.push_back(wire_err("model_attributes_type", cloc, "Input should be a valid dictionary or object to extract fields from", *crit));
            } else {
                for (const char* k : {"true", "false"})
                    if (const Value* v = crit->get(k)) check_structured(*v, L(cloc, {S(k)}), true, errs);
                check_extras(*crit, {"true", "false"}, cloc, errs);
            }
        }
    } else if (!crit) {
        errs.push_back(wire_err("missing", cloc, "Field required", q));
    } else if (tag == "choice") {
        if (!crit->is_dict()) errs.push_back(wire_err("dict_type", cloc, "Input should be a valid dictionary", *crit));
        else for (auto& [k, v] : crit->dict) check_structured(v, L(cloc, {S(k)}), true, errs);
    } else {
        if (!crit->is_list()) errs.push_back(wire_err("list_type", cloc, "Input should be a valid list", *crit));
        else for (size_t i = 0; i < crit->list.size(); ++i) check_structured(crit->list[i], L(cloc, {I(i)}), false, errs);
    }
    check_extras(q, {"type", "instructions", "criteria"}, base, errs);
    if (errs.size() != before || tag == "noul") return;
    // model validators, run once the fields are valid
    std::string problem;
    if (tag == "choice") {
        size_t count = crit->dict.size();
        bool blank = false;
        for (auto& kv : crit->dict) blank |= py_strip(kv.first).empty();
        if (blank) problem = "Choice option names must not be blank";
        else if (count < 2) problem = "A choice needs at least two options";
        else if (count > MAX_CHOICE_OPTIONS)
            problem = "A choice takes at most " + std::to_string(MAX_CHOICE_OPTIONS) + " options on this server, one answer letter each; got " +
                      std::to_string(count) + ". Split it into a coarse question and a fine one.";
    } else {
        size_t count = crit->list.size();
        if (count < MIN_SCORE_LEVELS || count > MAX_SCORE_LEVELS)
            problem = "A score takes " + std::to_string(MIN_SCORE_LEVELS) + " to " + std::to_string(MAX_SCORE_LEVELS) + " ordered levels; got " + std::to_string(count);
    }
    if (!problem.empty()) errs.push_back(wire_err("value_error", base, "Value error, " + problem, q, value_error_ctx()));
}

void check_wire(const Value& body, Errs& errs) {
    recursion_leak = 0;
    std::vector<Value> root = {S("body")};
    if (body.is_null()) { errs.push_back(wire_err("missing", root, "Field required", body)); return; }
    if (!body.is_dict()) { errs.push_back(wire_err("model_attributes_type", root, "Input should be a valid dictionary or object to extract fields from", body)); return; }
    const Value* state = body.get("state");
    if (!state) errs.push_back(wire_err("missing", {S("body"), S("state")}, "Field required", body));
    else check_structured(*state, {S("body"), S("state")}, false, errs);
    const Value* model = body.get("model");
    if (!model) errs.push_back(wire_err("missing", {S("body"), S("model")}, "Field required", body));
    else if (!model->is_str()) errs.push_back(wire_err("string_type", {S("body"), S("model")}, "Input should be a valid string", *model));
    else if (has_surrogate(model->s)) errs.push_back(wire_err("string_unicode", {S("body"), S("model")}, UNICODE_MSG, *model));
    else if (model->s.empty())
        errs.push_back(wire_err("string_too_short", {S("body"), S("model")}, "String should have at least 1 character", *model, ctx_json({{"min_length", I(1)}})));
    const Value* questions = body.get("questions");
    if (!questions) errs.push_back(wire_err("missing", {S("body"), S("questions")}, "Field required", body));
    else if (!questions->is_dict()) errs.push_back(wire_err("dict_type", {S("body"), S("questions")}, "Input should be a valid dictionary", *questions));
    else {
        size_t before = errs.size();
        for (auto& [qid, q] : questions->dict) check_question(qid, q, errs);
        if (errs.size() == before && questions->dict.empty())
            errs.push_back(wire_err("too_short", {S("body"), S("questions")}, "Dictionary should have at least 1 item after validation, not 0", *questions,
                                    ctx_json({{"field_type", S("Dictionary")}, {"min_length", I(1)}, {"actual_length", I(0)}})));
    }
    check_extras(body, {"state", "model", "questions"}, root, errs);
}

static std::string text_or_empty(const Value* v) { return v && v->truthy() ? text_of(*v) : ""; }

NativeQuestion to_native(const std::string& qid, const Value& q) {
    NativeQuestion n;
    n.id = qid;
    std::string type = q.get("type")->s;
    n.instructions = text_or_empty(q.get("instructions"));
    const Value* crit = q.get("criteria");
    auto blank = [](const Value& v) { return v.is_null() || (v.is_str() && v.s.empty()); };
    if (type == "noul") {
        n.kind = "boolean";
        if (n.instructions.empty()) n.instructions = DEFAULT_NOUL;
        if (crit && crit->is_dict()) {
            if (const Value* t = crit->get("true"); t && !blank(*t)) n.texts.emplace_back("true_description", "Yes. " + text_of(*t));
            if (const Value* f = crit->get("false"); f && !blank(*f)) n.texts.emplace_back("false_description", "No. " + text_of(*f));
        }
    } else if (type == "choice") {
        n.kind = "choice";
        if (n.instructions.empty()) n.instructions = "Which option fits the evidence best?";
        for (auto& [key, detail] : crit->dict) n.texts.emplace_back("options", blank(detail) ? key : key + ": " + text_of(detail));
    } else {
        n.kind = "score";
        if (n.instructions.empty()) n.instructions = "Which level fits the evidence best?";
        for (auto& level : crit->list) n.texts.emplace_back("levels", text_of(level));
    }
    return n;
}

void check_native(const Value& state, const std::vector<NativeQuestion>& qs, Errs& errs) {
    auto text_field = [&](const std::string& value, std::vector<Value> loc) {
        size_t n = utf8_length(py_strip(value));
        if (has_surrogate(value)) errs.push_back(app_err(std::move(loc), UNICODE_MSG, "string_unicode"));
        else if (n < 1) errs.push_back(app_err(std::move(loc), "String should have at least 1 character", "string_too_short"));
        else if (n > MAX_TEXT) errs.push_back(app_err(std::move(loc), "String should have at most 8000 characters", "string_too_long"));
    };
    for (auto& q : qs) {
        std::vector<Value> base = {S("body"), S("questions"), S(q.id), S(q.kind)};
        size_t before = errs.size();
        text_field(q.instructions, L(base, {S("instructions")}));
        size_t index = 0;
        for (auto& [field, value] : q.texts) {
            if (field == "options") text_field(value, L(base, {S("options"), I(index++), S("description")}));
            else if (field == "levels") text_field(value, L(base, {S("levels"), I(index++)}));
            else text_field(value, L(base, {S(field)}));
        }
        if (q.kind == "score" && errs.size() == before) {
            std::vector<std::string> seen;
            bool dup = false;
            for (auto& kv : q.texts) {
                std::string level = py_strip(kv.second);
                dup |= std::find(seen.begin(), seen.end(), level) != seen.end();
                seen.push_back(level);
            }
            if (dup) errs.push_back(app_err(base, "Value error, Levels must have distinct descriptions"));
        }
    }
    if (!errs.empty()) return;
    if (qs.size() > MAX_QUESTIONS) {
        errs.push_back(app_err({S("body"), S("questions")},
                               "Dictionary should have at most 1024 items after validation, not " + std::to_string(qs.size()), "too_long"));
        return;
    }
    std::vector<Value> root = {S("body")};
    if (!state.truthy() || (state.is_str() && py_strip(state.s).empty())) { errs.push_back(app_err(root, "Value error, State must not be empty")); return; }
    std::string rendered;
    try {
        rendered = pyjson::dumps(state, {-1, false, ", ", ": ", false});
    } catch (const pyjson::NanError& e) {
        errs.push_back(app_err(root, "Value error, Out of range float values are not JSON compliant: " + e.repr));
        return;
    }
    if (std::string bad = surrogate_error(rendered); !bad.empty()) { errs.push_back(app_err(root, "Value error, " + bad)); return; }
    if (rendered.size() > MAX_STATE_BYTES) { errs.push_back(app_err(root, "Value error, State exceeds 256 KB; no silent truncation")); return; }
    for (auto& q : qs)
        if (py_strip(q.id).empty() || utf8_length(q.id) > 128) {
            errs.push_back(app_err(root, "Value error, Question IDs must have 1\xE2\x80\x93" "128 nonblank characters"));
            return;
        }
}
