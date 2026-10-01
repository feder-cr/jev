#include "server.hpp"

#include <chrono>
#include <cstdio>
#include <ctime>

// No Nagle delay on small responses; keep-alive connections are not closed every 100 requests.
#define CPPHTTPLIB_TCP_NODELAY true
#define CPPHTTPLIB_KEEPALIVE_MAX_COUNT 1000000
#define CPPHTTPLIB_KEEPALIVE_TIMEOUT_SECOND 60
#include "httplib.h"
#include "choice.hpp"
#include "prompt.hpp"
#include "request_tokens.hpp"
#include "score.hpp"
#include "text.hpp"
#include "wire.hpp"

static const char* ALIAS_PREFIX = "jev-";

std::string Api::systemone(const Value& body, Timing& tm) const {
    auto v0 = Clock::now();
    auto ms = [](Clock::time_point a, Clock::time_point b) { return std::chrono::duration<double, std::milli>(b - a).count(); };
    Errs errs;
    check_wire(body, errs);
    if (!errs.empty()) throw unprocessable(std::move(errs));
    const std::string& requested = body.get("model")->s;
    if (!(requested == served || requested.rfind(ALIAS_PREFIX, 0) == 0))
        throw unprocessable(app_err({S("body"), S("model")}, "Unknown model " + pyjson::str_repr(requested) + ": this server answers as " +
                                                                 pyjson::str_repr(served) + " and accepts any 'jev-*' alias"));
    const Value& state = *body.get("state");
    std::vector<NativeQuestion> qs;
    for (auto& [qid, q] : body.get("questions")->dict) qs.push_back(to_native(qid, q));
    check_native(state, qs, errs);
    if (!errs.empty()) throw unprocessable(std::move(errs));
    auto v1 = Clock::now();
    tm.validate = ms(v0, v1);
    // The model answers yes/no questions: a noul question is one, a choice one per option and phrasing
    // (choice_instructions), each asked against all the other options, a score one per level above the
    // lowest and phrasing (score_instructions).
    struct Prompt {
        size_t question;
        std::string instructions;
    };
    std::vector<Prompt> prompts;
    for (size_t k = 0; k < qs.size(); ++k) {
        if (qs[k].kind == "boolean") {
            prompts.push_back({k, qs[k].instructions});
            continue;
        }
        std::vector<std::string> described;
        for (auto& [field, text] : qs[k].texts) described.push_back(text);
        if (qs[k].kind == "choice")
            for (auto& phrasing : CHOICE_PHRASINGS)
                for (size_t i = 0; i < described.size(); ++i) prompts.push_back({k, choice_instructions(qs[k].instructions, described, i, phrasing)});
        else
            for (auto& phrasing : SCORE_PHRASINGS)
                for (size_t i = 1; i < described.size(); ++i) prompts.push_back({k, score_instructions(qs[k].instructions, described, i, phrasing)});
    }
    // Tokens on the request's own thread (the vocabulary is read-only): a request tokenizes while
    // another one runs.
    auto t0 = Clock::now();
    std::string state_text = render_state(state);
    auto too_long = [&](const NativeQuestion& q, size_t n) {
        return unprocessable(app_err({S("body")}, "Question " + q.id + ": " + std::to_string(n) + " tokens exceeds the context limit " +
                                                      std::to_string(ctx) + " (--ctx); no truncation"));
    };
    for (auto& pr : prompts)
        if (std::string bad = surrogate_error(binary_prompt(vocab.bos(), state_text, pr.instructions)); !bad.empty()) {
            // the first question whose prompt cannot be encoded, as in the Python loop; a
            // context error of an earlier question comes first there
            for (size_t i = 0; i < static_cast<size_t>(&pr - prompts.data()); ++i)
                if (size_t n = vocab.tokenize(binary_prompt(vocab.bos(), state_text, prompts[i].instructions)).size(); n > ctx)
                    throw too_long(qs[prompts[i].question], n);
            throw unprocessable(app_err({S("body")}, bad));
        }
    // Every prompt holds the whole state and is at least as long: a state over the context makes the
    // first question's prompt too long, the error the Python loop stops at, without tokenizing them all.
    if (vocab.tokenize(vocab.bos() + state_text).size() > ctx)
        throw too_long(qs[prompts[0].question], vocab.tokenize(binary_prompt(vocab.bos(), state_text, prompts[0].instructions)).size());
    std::vector<std::string> instructions;
    for (auto& pr : prompts) instructions.push_back(pr.instructions);
    RequestTokens rt = tokenize_request(vocab, state_text, instructions);
    std::vector<Job> jobs;
    for (size_t i = 0; i < prompts.size(); ++i) {
        if (rt.prompts[i].empty() || rt.prompts[i].size() > ctx) throw too_long(qs[prompts[i].question], rt.prompts[i].size());
        jobs.push_back({qs[prompts[i].question].id, std::move(rt.prompts[i])});
    }
    auto t1 = Clock::now();
    tm.tokenize = ms(t0, t1);
    // usage counts the shared state once, as the Python server does (its prefix is the state's).
    size_t compiled = 0, shared = jobs.size() > 1 ? rt.state : 0, count = jobs.size();
    for (auto& j : jobs) compiled += j.tokens.size();
    auto result = scheduler.score({std::move(rt.prefix), std::move(jobs), rt.state});
    auto t2 = Clock::now();
    tm.queue = result.queue_ms;
    tm.inference = result.run_ms;
    std::vector<std::vector<double>> answered(qs.size());  // P(yes) of each question's prompts, in order
    for (size_t i = 0; i < prompts.size(); ++i) answered[prompts[i].question].push_back(result.ps[i]);
    std::string out = "{\"model\":";
    pyjson::quote(out, served);
    out += ",\"answers\":{";
    for (size_t k = 0; k < qs.size(); ++k) {
        if (k) out += ",";
        pyjson::quote(out, qs[k].id);
        if (qs[k].kind == "boolean") {
            out += ":{\"type\":\"noul\",\"noul\":" + pyjson::float_repr(answered[k][0]) + "}";
            continue;
        }
        if (qs[k].kind == "score") {
            const std::vector<std::string>& legend = qs[k].legend;
            ScoreAnswer a = rate(answered[k], legend.size());
            out += ":{\"type\":\"score\",\"score\":" + pyjson::float_repr(a.score) + ",\"legend\":{";
            for (size_t i = 0; i < legend.size(); ++i) out += (i ? ",\"" : "\"") + std::to_string(i) + "\":" + legend[i];
            out += "},\"probabilities\":{";
            for (size_t i = 0; i < legend.size(); ++i) out += (i ? ",\"" : "\"") + std::to_string(i) + "\":" + pyjson::float_repr(a.probabilities[i]);
            out += "},\"confidence\":" + pyjson::float_repr(a.confidence) + "}";
            continue;
        }
        const std::vector<std::string>& options = qs[k].options;
        ChoiceAnswer a = choose(answered[k], options.size());
        out += ":{\"type\":\"choice\",\"choice\":";
        pyjson::quote(out, options[a.best]);
        out += ",\"probabilities\":{";
        for (size_t i = 0; i < options.size(); ++i) {
            if (i) out += ",";
            pyjson::quote(out, options[i]);
            out += ":" + pyjson::float_repr(a.probabilities[i]);
        }
        out += "},\"confidence\":" + pyjson::float_repr(a.confidence) + "}";
    }
    out += "},\"usage\":{\"input_tokens\":" + std::to_string(compiled - shared * (count - 1)) + ",\"output_tokens\":0}}";
    tm.respond = ms(t2, Clock::now());
    return out;  // pydantic writes lone surrogates of question ids as they are
}

std::string rendered_error(const ApiError& e) {
    try {
        std::string out = error_body(e);
        if (std::string bad = surrogate_error(out); !bad.empty()) out = error_body(unprocessable(app_err({S("body")}, bad)));
        return out;
    } catch (const pyjson::NanError& nan) {
        return error_body(unprocessable(app_err({S("body")}, "Out of range float values are not JSON compliant: " + nan.repr)));
    }
}

// FastAPI's reading of the body: JSON only with an application/json (or +json) content type.
static bool json_content_type(const std::string& header) {
    std::string t = ascii_lower(py_strip(header.substr(0, header.find(';'))));
    size_t slash = t.find('/');
    if (slash == std::string::npos || t.find('/', slash + 1) != std::string::npos) return false;  // email: text/plain
    std::string main = t.substr(0, slash), sub = t.substr(slash + 1);
    return main == "application" && (sub == "json" || (sub.size() >= 5 && sub.compare(sub.size() - 5, 5, "+json") == 0));
}

static std::string today_utc() {
    std::time_t t = std::time(nullptr);
    std::tm g{};
#ifdef _WIN32
    gmtime_s(&g, &t);
#else
    gmtime_r(&t, &g);
#endif
    char buf[16];
    std::strftime(buf, sizeof buf, "%Y-%m-%d", &g);
    return buf;
}

bool serve(const Api& api, const ServeOptions& o) {
    const std::string& host = o.host;
    const int port = o.port;
    const std::string started_date = today_utc(), api_key = o.api_key;

    httplib::Server http;
    auto authorized = [&](const httplib::Request& req, httplib::Response& res) {
        if (api_key.empty()) return true;
        if (req.get_header_value("Authorization") == "Bearer " + api_key) return true;
        res.status = 401;
        res.set_header("WWW-Authenticate", "Bearer");
        res.set_content(ojson{{"detail", "Missing or invalid API key"}}.dump(), "application/json");
        return false;
    };
    http.Post("/v1/systemone", [&](const httplib::Request& req, httplib::Response& res) {
        auto t0 = Clock::now();
        auto internal_error = [&] { res.status = 500; res.set_content("Internal Server Error", "text/plain; charset=utf-8"); };
        // FastAPI: the body is read (and decoded, if JSON) before the API key is checked.
        Value body;  // null: no body
        if (!req.body.empty()) {
            if (json_content_type(req.get_header_value("Content-Type"))) {
                try {
                    body = pyjson::loads(req.body);
                } catch (const pyjson::DecodeError& e) {
                    std::string msg;
                    pyjson::quote(msg, e.msg);
                    res.status = 422;
                    res.set_content("{\"detail\":[{\"type\":\"json_invalid\",\"loc\":[\"body\"," + std::to_string(e.pos) +
                                        "],\"msg\":\"JSON decode error\",\"input\":{},\"ctx\":{\"error\":" + msg + "}}]}",
                                    "application/json");
                    return;
                } catch (const pyjson::BodyError&) {
                    res.status = 400;
                    res.set_content(R"({"detail":"There was an error parsing the body"})", "application/json");
                    return;
                }
            } else {
                // raw bytes: the wire model refuses them, and echoing them decodes them
                if (std::string bad = pyjson::utf8_error(req.body); !bad.empty()) {
                    res.status = 422;
                    res.set_content(error_body(unprocessable(app_err({S("body")}, bad))), "application/json");
                    return;
                }
                body = Value::str(req.body);
            }
        }
        if (!authorized(req, res)) return;
        try {
            Timing tm;
            tm.parse = std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
            std::string out = api.systemone(body, tm);
            double total_ms = std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
            char timing[256];
            std::snprintf(timing, sizeof timing,
                          "parse;dur=%.2f, validate;dur=%.2f, tokenize;dur=%.2f, queue;dur=%.2f, inference;dur=%.1f, respond;dur=%.2f, total;dur=%.1f",
                          tm.parse, tm.validate, tm.tokenize, tm.queue, tm.inference, tm.respond, total_ms);
            res.set_header("Server-Timing", timing);
            res.set_content(out, "application/json");
        } catch (const ApiError& e) {
            if (e.status == 500) return internal_error();
            res.status = e.status;
            res.set_content(rendered_error(e), "application/json");
        } catch (const std::exception& e) {
            std::fprintf(stderr, "jev: %s\n", e.what());
            internal_error();
        }
    });
    http.Get("/v1/models", [&](const httplib::Request& req, httplib::Response& res) {
        if (!authorized(req, res)) return;
        ojson models = ojson::array({
            {{"name", api.served}, {"description", "Typed decisions read from the option logits of a local model; no text is generated."}, {"release_date", started_date}},
            {{"name", std::string(ALIAS_PREFIX) + "latest"}, {"description", "Compatibility alias: answered by " + api.served + " on this server, not by TypeSafe's Jev."}, {"release_date", started_date}}});
        res.set_content(ojson{{"models", models}}.dump(), "application/json");
    });
    http.Get("/health", [&](const httplib::Request&, httplib::Response& res) {
        res.set_content(ojson{{"status", "ready"}, {"model", api.served}, {"model_files", api.files["model_files"]},
                              {"fingerprint", api.files["fingerprint"]}, {"engine", api.model.describe()}}.dump(),
                        "application/json");
    });
    // Starlette: a known path with another method is a 405, anything else a 404, both JSON.
    auto not_allowed = [](const char* allow) {
        return [allow](const httplib::Request&, httplib::Response& res) {
            res.status = 405;
            res.set_header("Allow", allow);
            res.set_content(R"({"detail":"Method Not Allowed"})", "application/json");
        };
    };
    for (const char* path : {"/v1/models", "/health"}) {
        http.Post(path, not_allowed("GET"));
        http.Put(path, not_allowed("GET"));
        http.Delete(path, not_allowed("GET"));
        http.Patch(path, not_allowed("GET"));
    }
    http.Get("/v1/systemone", not_allowed("POST"));
    http.Put("/v1/systemone", not_allowed("POST"));
    http.Delete("/v1/systemone", not_allowed("POST"));
    http.Patch("/v1/systemone", not_allowed("POST"));
    http.set_error_handler([](const httplib::Request&, httplib::Response& res) {
        if (!res.body.empty()) return httplib::Server::HandlerResponse::Unhandled;
        res.set_content(res.status == 404 ? R"({"detail":"Not Found"})" : R"({"detail":"Error"})", "application/json");
        return httplib::Server::HandlerResponse::Handled;
    });
    // One server per port. httplib's default socket options (SO_REUSEPORT on Linux and macOS, SO_REUSEADDR on
    // Windows) let a second server bind the port too, and the system then splits the requests between them.
    // Here SO_REUSEADDR on POSIX only: a restart may take a port still in TIME_WAIT, a running server keeps it.
    http.set_socket_options([](socket_t sock) {
#ifndef _WIN32
        int yes = 1;
        setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
#else
        (void)sock;
#endif
    });
    // The port first: "listening" only once it is ours, and a clear refusal when it is not.
    if (!http.bind_to_port(host, port)) {
        std::fprintf(stderr, "jev: cannot listen on http://%s:%d: the port is in use or the address is not this machine's\n",
                     host.c_str(), port);
        return false;
    }
    std::fprintf(stderr, "jev: listening on http://%s:%d\n", host.c_str(), port);
    return http.listen_after_bind();
}
