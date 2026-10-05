---
title: "Document classification with a local LLM"
description: "Sort invoices, contracts, reports and letters with a local LLM: one yes/no question per type, the first page instead of the whole file, and an other bin."
parent: "Use cases"
nav_order: 16
---

# Document classification with a local LLM

**To classify documents with a small local LLM, ask one yes/no question per document type
("Is this document an invoice?", "Is this document a contract between two parties?") about the
first page or the first few hundred words, and pick the type from the probabilities, with an
"other" bin when none is high.** No training data is needed, a new type is a new question, and
the text stays on your machine. What you have to handle yourself is getting text out of the file
and deciding how much of it to send, because the text plus each question holds at most 8,192
tokens and every token costs time.

The non-obvious part is that more text rarely helps. A document announces its type early: the
header, the title, the first paragraph. Sending the whole file makes each request slower and
buries the signal among clauses and tables.

This page is the questions, how much of the document to send, how to turn probabilities into a
label, documents that are two things at once, the step before the model, and how to check the
result on your own archive.

## One question per type

Write each type as a question about what the document is, with the distinguishing feature in
the question:

```json
{
  "model": "jev-latest",
  "state": {
    "file_name": "scan_0412.pdf",
    "first_page": "INVOICE No. 2026-118. Bill to: ... Item, quantity, unit price ... Total due within 30 days."
  },
  "questions": {
    "invoice":  {"type": "noul", "instructions": "Is this document an invoice asking for payment?"},
    "contract": {"type": "noul", "instructions": "Is this document a contract or agreement between parties?"},
    "report":   {"type": "noul", "instructions": "Is this document a report that presents findings or results?"},
    "receipt":  {"type": "noul", "instructions": "Is this document a receipt confirming a payment already made?"},
    "letter":   {"type": "noul", "instructions": "Is this document a letter addressed to a person or organisation?"}
  }
}
```

"Invoice asking for payment" and "receipt confirming a payment already made" differ in one
feature, and naming it is what separates them. Each question comes back as its own `noul`, and
questions in the same request share the text, which is read once. The general method, with the
pitfalls of a plain argmax, is on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## First page or the whole document?

The first page, almost always. Three reasons.

- **Speed.** On our reference laptop the cost grows with the text: a long request
  read from scratch took 130 ms. A first page of 400 to 600 tokens takes longer, and a
  whole report longer still; the numbers behind that are on
  [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).
- **Limit.** jevos reads at most 8,192 tokens per question, the text plus that question, by
  default. Many documents are longer.
- **Signal.** Type is a property of the whole document that is visible at the start. A contract
  says "Agreement" in its title and names the parties in its first lines.

Two useful additions: the file name, which often carries a hint, and a short sample from the
last page, where signatures, totals and "Yours sincerely" live. If a type is only visible deep
inside (an appendix that turns a letter into a claim form), classify by passage and combine,
as on [yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## From probabilities to one label

A workable rule in code:

1. Take the type with the highest probability.
2. If it is below a threshold you chose on labelled documents, the label is "other" and the file
   goes to a person or a default folder.
3. If two types are both high, record both and let the workflow decide (see the next section).

The threshold does most of the work. A low one fills folders with wrong files; a high one sends
too many to "other". Choose it by looking at a few dozen labelled documents near the boundary,
not by default at 0.5.

## Documents that are two things

Real archives are messy: an email with an invoice pasted in, a report with a contract attached,
a letter that is also a complaint. Forcing one label hides the second. Two approaches:

- **Allow several labels.** If both "invoice" and "letter" are above the threshold, file it under
  both, or route it by the one your process cares about more.
- **Ask what it mainly is.** "Is this document mainly an invoice?" pushes the model toward the
  primary purpose. The wording pattern is on
  [mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).

## The step before the model

jevos reads text. It does not open PDFs, run OCR on scans or read tables as images. Before the
request you need a text extraction step: the PDF's own text layer when it has one, OCR when it
does not. Extraction quality sets an upper bound on classification quality, and a scanned page
with bad OCR is where most errors in a pipeline like this come from. Check a sample of extracted
text by eye before you tune any threshold.

It also reads English only. A mixed-language archive needs a translation step or a multilingual
model, as discussed on
[using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).

## Checking it on your archive

Take a hundred or two documents you have already filed, with their correct types. Run the
questions, and look at three things: the confusion between similar pairs (invoice and receipt,
report and letter), the share that lands in "other", and the documents where two types were high.
Then change the wording of the confused pair, not the threshold, first. On our 999
hand-written questions, the first jevos answered stated facts right 0.954 of the time (per-kind numbers for
jevos-v4 are not published), and "is
this an invoice" is usually a question of that kind when the header says so. We have not
measured document classification as such, so your archive is the only accuracy figure that
counts. A method for the test set is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md).

Once a document has a type, the next questions are often about its content. For contracts,
that is [contract clause detection with a local LLM](contract-clause-detection-with-a-local-llm.md).

## Short answers to the questions that lead here

**Can a local LLM classify documents without training?** Yes, if each type is a yes/no question.
A new type is a new question, not a new model.

**How much of the document should I send?** Usually the first page, plus the file name and
perhaps a sample of the last page. The limit is 8,192 tokens for the text plus each question.

**Can it read PDFs or scans?** Not directly. Extract the text first, with OCR for scans.

**What about documents that match no type?** Use a threshold: when no type is high enough, the
label is "other".

**Is it fast enough for a backlog?** A long request took 130 ms on a laptop CPU.
Time a few of your own first pages; a backlog is a batch job.

**See also:** [product categorization with yes/no questions](product-categorization-with-yes-no-questions.md),
[jevos vs bart-large-mnli for zero-shot classification](jevos-vs-bart-large-mnli.md) and
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

## Sources

- Our measurements: context, latency and the reference laptop from the
  [jev README](https://github.com/feder-cr/jev); accuracy on stated facts from our 999
  hand-written questions, measured on the first jevos. No document classification measurement exists; none is claimed.
- No external facts are stated on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The invoice and receipt pair is in the example on purpose: they differ by one
feature, and the question has to name it.*
