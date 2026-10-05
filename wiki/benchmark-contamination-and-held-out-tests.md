---
title: "Benchmark contamination and truly held-out tests"
description: "Why published test questions leak into model training data, how contamination inflates scores, how to detect it, and how to keep a private test set clean."
parent: "Evaluation"
nav_order: 12
---

# Benchmark contamination and truly held-out tests

**Benchmark contamination is when the questions of a test, or close copies of them, were part of
the data a model learned from, so its score measures memory as well as ability.** It happens
because published benchmarks live on the public web, and web text is what large models are
trained on. The only test you can fully trust is one that has never been published, that was
made after the model, and that you have not used to make choices. For an application, that means
a private set of your own cases.

Contamination is not only exact copies. A test written in the same style, from the same sources,
by the same process as the training material is partly familiar to the model even if no question
was copied, and it inflates scores the same way, only less visibly.

This page is how test questions leak, what the leak does to a score, three ways to detect it,
the softer problem of tests that are too similar, and the rules for keeping a private set clean.

## How does a test question end up in training data?

Mostly by being public. A benchmark is released as a file in a repository, discussed in papers,
quoted in blog posts, and answered in forums. Crawls of the web pick up all of it, and a model
trained on a large crawl may have seen a question, its answer, and people arguing about the
answer. Nobody needs to cheat for this to happen.

Benchmark authors know it. The BIG-bench repository asks that task files carry a canary string,
and its README says the purpose is to prevent benchmark tasks from leaking into web-scraped
training data: a model builder who filters documents containing the canary keeps the tasks out.
It only works if the canary survives every copy and every builder filters for it.

## What contamination does to a score

It makes the score optimistic, by an amount you cannot see from the score. A clear measurement
comes from the GSM1k study: its authors wrote a new set of grade-school maths problems in the style
and difficulty of the public GSM8k benchmark, and found accuracy drops of up to 8% for leading
models on the new set. They also found a correlation (Spearman r-squared 0.36) between how likely a
model was to generate GSM8k examples and how much worse it did on GSM1k, which points at partial
memorisation. They also report that frontier models showed minimal signs of overfitting and that
all models generalised meaningfully to the new problems, so contamination shaves points rather
than turning a weak model into a strong one.

The same shape appears without any public benchmark involved. On the first jevos, a test split made
the same way as the material the model learned from scored about ten points higher than questions
written independently afterwards. That measurement, and why excluding whole topics did not close
the gap, is on
[our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md).

## Three ways to detect it

**Overlap search.** If you have the training corpus, search it for the test questions: long
sequences of words (n-grams) shared between a test item and any training document are a strong
sign of a copy. It catches verbatim and near-verbatim leaks, misses paraphrases, and needs access to
the corpus, which you do not have for most models.

**Ordering tests.** Oren and colleagues, in "Proving Test Set Contamination in Black Box Language
Models", use the idea that without contamination every ordering of a benchmark's examples should be
equally likely to the model. A model that has seen the benchmark in its canonical order assigns that
order a noticeably higher likelihood than shuffled ones. The method needs only the model's
probabilities, and they report it detecting contamination in models as small as 1.4 billion
parameters and test sets as small as 1,000 examples.

**A fresh set in the same style.** The GSM1k approach: write new questions that match the old
benchmark's style and difficulty, and compare. It is the most direct test, and the most expensive,
and it is the one that also catches the softer problem below.

## The softer problem: tests that are too similar

A test can be clean of copies and still be familiar. If the test and the training material share
templates, text formats, the same kind of author, or the same balance of hard and easy cases, the
model can do well on the test by having learned those regularities. Overlap search will not flag
it; only a test made by a different process will. That is the gap our held-out split showed, and
it is the reason a test written after the model, by other means, is worth more than a larger test
that was cut from the same source. The same argument applies to generated tests, whose templates
have a style of their own, as discussed on
[generating test questions with answers computed by code](generating-test-questions-with-code.md).

## Keeping a private test set clean

1. **Do not publish it.** Not in a repository, not in a blog post, not in a bug report. Publish the
   method and the numbers; keep the questions. Our own 999 hand-written questions stay unpublished for this
   reason.
2. **Watch where it travels.** A test set pasted into a hosted service goes wherever that service's
   data terms allow. Read them. Evaluating with a local model, such as jevos on a CPU, keeps the set
   on your own machine.
3. **Add a canary of your own.** A unique string in every file makes accidental copies findable by
   search later.
4. **Separate development from test.** Choose thresholds, prompts and models on a development set;
   run the test set only to report. How to set up both is on
   [building a yes/no test set for your own data](building-a-yes-no-test-set.md).
5. **Rotate.** After a test has been run many times during development, it has quietly become a
   development set. Retire it and make a new one, ideally by a different person or process.
6. **Date it.** Record when the set was made relative to the model. A set written after the model
   was released cannot have been in its training data.

## Being straight about what this means for any model's numbers

A published benchmark score, including any we or anyone else report, is an upper estimate for data
that looks like the benchmark. We say so about our own: of the six tasks in the jevos-v4 comparison,
five helped choose the released checkpoint, so jevos's scores there may be slightly optimistic; only
the patent-phrases task did not. Your data does not. The practical rule is the same for every model:
before relying on it, measure it on a private set of your own cases, split by
[kind of question](accuracy-by-kind-of-question.md), and plan with that number.

## Short answers to the questions that lead here

**What is benchmark contamination?** Test questions, or close copies, appearing in the data a model
learned from, which inflates its score on that test.

**How big is the effect?** It varies. The GSM1k study found drops of up to 8% for leading models on
fresh problems in the style of a public benchmark.

**How can I check a model for contamination without its training data?** Compare it on a fresh set
written in the same style, or use an ordering test on its probabilities.

**Is a held-out split of my own data enough?** Not always. A split made the same way as the tuning
data can still be optimistic; ours was by about ten points on the first jevos.

**Should I publish my test set?** Not the questions, if you want to keep using them. Publish the
method and the results.

**See also:** [evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md),
[LLM judge bias and how to control it](llm-judge-bias.md) and
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Zhang et al., "A Careful Examination of Large Language Model Performance on Grade School
  Arithmetic" (GSM1k), [arXiv:2405.00332](https://arxiv.org/abs/2405.00332), fetched 2026-09-29.
- Oren, Meister, Chatterji, Ladhak and Hashimoto, "Proving Test Set Contamination in Black Box
  Language Models", [arXiv:2310.17623](https://arxiv.org/abs/2310.17623), fetched 2026-09-29.
- BIG-bench README on the canary string,
  [github.com/google/BIG-bench](https://github.com/google/BIG-bench), fetched 2026-09-29.
- The ten-point gap between our held-out split (0.855) and independent questions (0.757): our
  measurements of the first jevos.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which keeps its hardest test set off the
web so that its numbers stay worth reporting.*
