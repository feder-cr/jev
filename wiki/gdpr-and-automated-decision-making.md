---
title: "GDPR and automated decision-making with an LLM"
description: "What GDPR Article 22 says about decisions based solely on automated processing, how a human review band fits, and what a local LLM does not change."
parent: "Local and private AI"
nav_order: 4
---

# GDPR and automated decision-making with an LLM

**Article 22(1) of the GDPR says that a person "shall have the right not to be subject to a
decision based solely on automated processing, including profiling, which produces legal
effects concerning him or her or similarly significantly affects him or her."** If an LLM's
output alone decides something of that weight about a person, you are inside Article 22
whether the model runs at a provider or on your own laptop. The official guidelines read the
article as a general prohibition with exceptions, and the exceptions come with safeguards, at
minimum a way to obtain human intervention, express a point of view and contest the decision.

This page is not legal advice. It is an engineer's reading of the article and of the European
guidelines on it. Whether your system falls under Article 22 is a question for your data
protection officer or a lawyer.

The non-obvious point: local processing and Article 22 are about different things. Running the
model on your own machine changes who else receives the text. It does not change whether the
decision is automated, how much it affects the person, or what you owe them.

This page is what "solely" and "significant" mean in the guidelines, the exceptions and
safeguards, how a review band maps onto them, and what a local model does and does not change.

## What the guidelines add to the article

All quotations here come from the Article 29 Working Party's guidelines on automated
decision-making (WP251rev.01), which the European Data Protection Board endorsed. They
summarise Article 22 in three parts:

> (i) as a rule, there is a general prohibition on fully automated individual decision-making,
> including profiling that has a legal or similarly significant effect;
> (ii) there are exceptions to the rule;
> (iii) where one of these exceptions applies, there must be measures in place to safeguard the
> data subject's rights and freedoms and legitimate interests.

The word "right" sounds like something a person must invoke. The guidelines say the
prohibition "applies whether or not the data subject takes an action regarding the processing
of their personal data." You cannot wait for a complaint to find out whether a flow is covered.

## When is a decision "based solely" on automated processing?

When "there is no human involvement in the decision process". A model output that is in effect
a recommendation, which a person reviews while taking "account of other factors in making the
final decision", is not solely automated. But, in the guidelines' words, "The controller
cannot avoid the Article 22 provisions by fabricating human involvement":

> To qualify as human involvement, the controller must ensure that any oversight of the
> decision is meaningful, rather than just a token gesture. It should be carried out by someone
> who has the authority and competence to change the decision.

A reviewer who sees only "P(yes) 0.83, approve?" and clicks through a queue is close to that
token gesture. A review screen that shows the original text, the questions asked and the
probabilities, and lets the reviewer decide the other way without friction, is closer to what
the sentence asks for. Logging how often reviewers override the model shows whether the review
is doing anything.

## Which decisions have "similarly significant" effects?

The wording, say the guidelines, makes clear that "only serious impactful effects will be
covered". Their examples include cancelling a contract, decisions that affect someone's
financial circumstances "such as their eligibility to credit", access to health services,
employment and education, and Recital 71's "automatic refusal of an online credit application"
and "e-recruiting practices without any human intervention".

Most uses of a yes/no model sit far from that line: routing a ticket to billing, tagging an
email as a newsletter, flagging an alert. Closing a customer's account, refusing a claim or
screening job applicants are the cases to take to your data protection officer before you
automate them.

## The exceptions, and the safeguards they bring

Article 22(2) allows such a decision where it is, in the guidelines' list, "(a) necessary for
the performance of or entering into a contract; (b) authorised by Union or Member State law
[...]; or (c) based on the data subject's explicit consent." Under (a) and (c), safeguards
"should include as a minimum a way for the data subject to obtain human intervention, express
their point of view, and contest the decision." Special categories of data have stricter
conditions under Article 22(4).

Transparency comes on top: "meaningful information about the logic involved", which is "not
necessarily a complex explanation of the algorithms used". A yes/no design helps here. "Does
the customer say the item was missing?" plus a policy written in code is a criterion you can
state in a sentence, which is one more reason to keep the rule explicit, as on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## Where a review band fits, and where it does not

The common pattern acts automatically when P(yes) is high, acts the other way when it is low,
and sends the middle to a person, as on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md). The
detail that matters for Article 22: the two automatic ends are still decisions based solely on
automated processing. The band handles the uncertain cases and does nothing for the confident
ones.

So choose which outcome you automate. A shape engineers often use lets the model grant the
favourable outcome alone and sends every adverse outcome to a person: refunds approved
automatically, refusals always reviewed. Whether that is enough in your case is a legal
question, but it keeps the adverse decisions in human hands by construction.

The direction of the model's mistakes matters too. On 999 questions written after training,
jevos gave 152 wrong yeses against 91 wrong noes, as measured on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md). If "yes" is the
adverse answer ("Is this claim fraudulent?"), that lean points at the person, and the bar for
acting on yes belongs higher, as on
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md). To handle a
later challenge you need the questions, probabilities, threshold, model file hash and the
reviewer's action on record: [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## What running the model locally changes, and what it does not

It changes the data flow. The text is not sent to a model provider, so that provider is not a
party you describe, contract with and trust for this step. If "local" is a rented server, the
hosting company is still in the picture. More on
[a private LLM for text classification](private-llm-for-text-classification.md).

It changes nothing above. Whether a decision is solely automated, whether its effect is
significant, which exception applies, what you tell the person and how they contest it are the
same for a model on your laptop and one behind an API. The guidelines also point to a Data
Protection Impact Assessment for processing "likely to result in a high risk", and where the
model runs does not remove that step. Nor does it make the model more accurate: a wrong refusal
computed locally is still a wrong refusal.

## Short answers to the questions that lead here

**Does the GDPR ban AI decisions?** Not in general. Article 22 covers decisions based solely on
automated processing with legal or similarly significant effects, and it has exceptions that
come with safeguards.

**Does a human reviewer take a decision out of Article 22?** Only if the involvement is
meaningful: someone with "the authority and competence to change the decision", not a token
gesture.

**Is a local LLM GDPR compliant?** No model is compliant by itself. A local model removes a
third party from the data flow; lawful basis, transparency, Article 22 and security remain
your work.

**Is a probability a decision?** Do not rely on the distinction. If your code acts on a
threshold with no person involved, the threshold is the decision.

**Is this legal advice?** No. Ask your data protection officer or a lawyer about your system.

**See also:** [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md),
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md) and
[a private LLM for text classification](private-llm-for-text-classification.md).

## Sources

- Article 29 Data Protection Working Party, *Guidelines on Automated individual decision-making
  and Profiling for the purposes of Regulation 2016/679* (WP251rev.01), last revised and adopted
  6 February 2018, endorsed by the EDPB:
  [EDPB page](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/automated-decision-making-and-profiling_en)
  and [document](https://ec.europa.eu/newsroom/article29/items/612053), fetched 2026-09-29.
  Every quotation here, including Article 22(1) and the Recital 71 examples, is from it.
- The regulation: [EUR-Lex, Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng).
  Our fetch on 2026-09-29 returned no text, so nothing is quoted from it directly.
- Error counts (152 and 91): our measurement on 999 questions, `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We are engineers, not lawyers, and
this is the page where we most want you to check our reading.*
