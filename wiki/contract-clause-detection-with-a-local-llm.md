---
title: "Contract clause detection with a local LLM"
description: "Find auto-renewal, limitation of liability and other clauses in contracts with local yes/no questions. Presence is reading; legal review stays human."
parent: "Use cases"
nav_order: 18
---

# Contract clause detection with a local LLM

**A small local LLM can tell you whether a contract appears to contain a given clause, such as
automatic renewal, a limitation of liability or termination for convenience, by asking one
yes/no question per clause about each section of the text.** Presence is a reading question,
and reading is what a small model does best. Whether the clause is enforceable, fair, standard
for your industry or acceptable to your company is not a reading question, and it stays with a
lawyer. The model's job is to point a reviewer at the right pages faster, on your own machine.

The design choice that matters most is the direction of the error. In clause detection a
missed clause is usually worse than a false alarm: a reviewer can dismiss a highlighted
paragraph in seconds, but nobody reviews a clause they were told is not there.

This page is the questions, the request for one section, long contracts, what not to ask, how to
set thresholds so "not found" means something, and where the legal review sits.

## Which clause questions work?

Questions about whether the text says something, one clause per question:

| Clause | Question |
|---|---|
| automatic renewal | Does this section say the agreement renews automatically unless someone gives notice? |
| limitation of liability | Does this section limit or cap the amount one party can be liable for? |
| termination for convenience | Does this section allow a party to end the agreement without giving a reason? |
| exclusivity | Does this section prevent a party from working with competitors or other suppliers? |
| governing law | Does this section say which country's or state's law governs the agreement? |
| assignment | Does this section restrict a party from transferring the agreement to someone else? |

Each question describes what the clause does, not its name. Contracts rarely use the same
heading twice, and "Does this section contain a limitation of liability clause?" leans on the
label, while "Does this section limit or cap the amount one party can be liable for?" asks about
the content. On our 999-question test set written after training, stated facts were answered
right 0.954 of the time and paraphrase questions 0.893. Clause detection is mostly those two
skills: the clause is stated, in words that differ from yours.

## The request for one section

```json
{
  "model": "jev-latest",
  "state": {
    "document": "Master services agreement",
    "section": "12. Term. This Agreement starts on the Effective Date and continues for twelve months. It will then extend for further periods of twelve months each unless either party gives written notice at least sixty days before the end of the current period."
  },
  "questions": {
    "auto_renewal": {"type": "noul", "instructions": "Does this section say the agreement renews automatically unless someone gives notice?"},
    "liability_cap": {"type": "noul", "instructions": "Does this section limit or cap the amount one party can be liable for?"},
    "termination_convenience": {"type": "noul", "instructions": "Does this section allow a party to end the agreement without giving a reason?"}
  }
}
```

The section never says "renew". A question about the effect ("renews automatically unless
someone gives notice") is what lets the model match "will then extend for further periods".
Each question returns its own `noul`, and several questions about one section cost little more
than one, because the section is read once.

## Long contracts: split, ask, combine

Each question's prompt, the text plus that question, holds at most 8,192 tokens by default, and
on our reference laptop latency grows with the text:
about 26 ms for 30 tokens, 112 ms for 191 tokens read from scratch. A long agreement with schedules will not fit, and even when it fits, one
question about a hundred pages is worse than the same question about each section.

Split on the contract's own structure (numbered sections or clauses), ask every clause question
about every section, and combine with OR: the contract contains the clause if any section does.
Keep the section number with each answer, so a reviewer goes straight to it. The method is on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md), and the logic
of combining answers in code on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

If the first job is to tell a contract from an invoice or a letter, do that first with
[document classification with a local LLM](document-classification-with-a-local-llm.md).

## What should you not ask the model?

- **Legal judgments.** "Is this clause enforceable?", "Is this cap reasonable?", "Is this
  unusual for a software contract?" These need legal knowledge, jurisdiction and context the
  text does not contain.
- **Numbers and dates.** "Is the notice period longer than 30 days?" "Does the cap exceed the
  annual fees?" Extract the figure and compare in code. On the same test set, number against
  threshold questions were right 0.654 of the time and dates 0.598.
- **Absence in one go.** "Does this contract lack a liability cap?" is a negated question about
  a whole document. Ask the positive question per section and conclude absence in code when no
  section says yes. Why negation needs care is on
  [negation in yes/no questions](negation-in-yes-no-questions.md).

## Making "not found" mean something

Because a missed clause is the costly mistake, set a low threshold for highlighting a section,
well below 0.5, and accept more false highlights. Then check what "not found" means on your own
contracts: take a few dozen agreements where a lawyer has already marked the clauses, run the
questions, and count how many marked clauses scored below your threshold. That count, not a
general accuracy figure, tells you whether "no auto-renewal found" is safe to show. We have not
measured jevos on contracts, and the 999-question figures describe kinds of questions, not this
task.

The general reasoning on asymmetric thresholds is on
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md);
here it runs the other way, since the wrong no is the expensive one.

## Where does the legal review sit?

At the end, and always. The model can shorten the path to the relevant paragraphs; it cannot
read a contract for you in the sense that matters. OWASP's guidance on overreliance on model
output recommends human oversight and fact-checking "especially for critical or sensitive
information", and a contract a company is about to sign is that. A sensible pipeline:

1. Split the contract into sections and ask the clause questions locally.
2. Show the reviewer every section above the highlight threshold, grouped by clause, with the
   section number.
3. The reviewer reads the highlights and the parts of the contract the checklist does not cover.
4. The reviewer, not the model, records the conclusion.

Running locally is a real benefit here: draft contracts are confidential, and a model on your
own CPU sends them nowhere. It does not change who is responsible for the review.

## Short answers to the questions that lead here

**Can an LLM find clauses in a contract?** It can answer whether each section appears to contain
a clause you describe, which is a reading task. It should point a reviewer at sections, not
replace the review.

**Can it tell me whether a clause is enforceable?** No. That is legal advice and it stays with a
lawyer.

**How do I handle a 60-page contract?** Split it by section, ask each clause question per section,
and combine with OR in code. The text plus each question has to fit in 8,192 tokens.

**What threshold should I use?** A low one for highlighting, because a missed clause costs more
than a false highlight. Check it on contracts a lawyer has already marked.

**Is it safe for confidential drafts?** The model runs on your machine and sends nothing out. Your
own storage and access rules still apply.

**See also:** [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md),
[ask whether the text says it at all](ask-whether-the-text-says-it.md) and
[a private LLM for text classification](private-llm-for-text-classification.md).

## Sources

- Our measurements: context and latency from the
  [jev README](https://github.com/feder-cr/jev); accuracy by kind of question from our
  999-question test set on `jevos-q4_k_m`. No contract measurement exists; none is claimed.
- OWASP GenAI Security Project,
  [LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/),
  overreliance and human oversight, fetched 2026-09-29.
- This page is not legal advice.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The renewal clause in the example never uses the word "renew", which is why
every question on this page describes what a clause does, not what it is called.*
