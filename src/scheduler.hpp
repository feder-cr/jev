#pragma once
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <deque>
#include <exception>
#include <future>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

#include "model.hpp"

using Clock = std::chrono::steady_clock;

// The model's only user. One thread runs every model call, from one queue: waiting requests first,
// several in one call while they fit a budget of tokens, and in idle time the
// warm-up of prompt lengths (kernels built per shape cost 3-10 ms the first time a length runs).
// A request arriving during a warm-up call waits for that one call; the warm-up starts only after
// IDLE_GRACE without requests, so steady traffic, which warms its own lengths, is not interrupted.
class Scheduler {
public:
    struct Result {
        std::vector<double> ps;
        double queue_ms = 0, run_ms = 0;
    };

    // warm_up_to: longest prompt length warmed while idle (at most Model::WARM_TOKENS, 0 = none);
    // batch_tokens: most tokens of requests read together (at most Model::CALL_TOKENS, 0 = one at a time)
    Scheduler(Model& model, size_t warm_up_to, size_t batch_tokens)
        : model_(model), warm_to_(std::min(warm_up_to, Model::WARM_TOKENS)), budget_(std::min(batch_tokens, Model::CALL_TOKENS)) {
        worker_ = std::thread([this] { loop(); });
    }
    ~Scheduler() {
        {
            std::lock_guard<std::mutex> g(mu_);
            stop_ = true;
        }
        cv_.notify_all();
        worker_.join();
    }
    Scheduler(const Scheduler&) = delete;
    Scheduler& operator=(const Scheduler&) = delete;

    // Blocks until the request is answered; rethrows the model's error.
    Result score(ScoreRequest req) {
        auto task = std::make_shared<Task>();
        task->req = std::move(req);
        task->queued = Clock::now();
        auto done = task->done.get_future();
        {
            std::lock_guard<std::mutex> g(mu_);
            queue_.push_back(task);
        }
        cv_.notify_one();
        return done.get();
    }

private:
    static constexpr std::chrono::milliseconds IDLE_GRACE{500};
    struct Task {
        ScoreRequest req;
        std::promise<Result> done;
        Clock::time_point queued;
    };

    void loop() {
        size_t next_warm = 1;
        auto last = Clock::now(), warm_start = last;
        while (true) {
            std::vector<std::shared_ptr<Task>> batch;
            {
                std::unique_lock<std::mutex> lk(mu_);
                while (!stop_ && queue_.empty()) {
                    if (next_warm > warm_to_) { cv_.wait(lk); continue; }
                    auto idle = Clock::now() - last;
                    if (idle >= IDLE_GRACE) break;
                    cv_.wait_for(lk, IDLE_GRACE - idle);
                }
                if (stop_) return;
                size_t used = 0;
                while (!queue_.empty()) {
                    size_t t = queue_.front()->req.tokens();
                    if (!batch.empty() && (budget_ == 0 || used + t > budget_)) break;
                    batch.push_back(queue_.front());
                    queue_.pop_front();
                    used += t;
                }
            }
            if (batch.empty()) {  // idle: the next length no call has run yet
                while (next_warm <= warm_to_ && model_.is_warm(next_warm)) ++next_warm;
                if (next_warm > warm_to_) continue;
                try {
                    model_.warm_length(next_warm++);
                } catch (const std::exception& e) {
                    std::fprintf(stderr, "jev: warm-up stopped at prompt length %zu: %s\n", next_warm - 1, e.what());
                    next_warm = warm_to_ + 1;
                }
                if (next_warm > warm_to_) {
                    std::printf("warmed prompt lengths 1-%zu in %.0f s\n", warm_to_, std::chrono::duration<double>(Clock::now() - warm_start).count());
                    std::fflush(stdout);
                }
                continue;
            }
            auto t0 = Clock::now();
            std::vector<const ScoreRequest*> reqs;
            for (auto& t : batch) reqs.push_back(&t->req);
            try {
                auto outs = model_.score_batch(reqs);
                double run_ms = std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
                for (size_t i = 0; i < batch.size(); ++i)
                    batch[i]->done.set_value({std::move(outs[i]), std::chrono::duration<double, std::milli>(t0 - batch[i]->queued).count(), run_ms});
            } catch (...) {
                for (auto& t : batch) t->done.set_exception(std::current_exception());
            }
            last = Clock::now();
        }
    }

    Model& model_;
    size_t warm_to_, budget_;
    std::mutex mu_;
    std::condition_variable cv_;
    std::deque<std::shared_ptr<Task>> queue_;
    bool stop_ = false;
    std::thread worker_;
};
