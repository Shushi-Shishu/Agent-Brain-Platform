# Search Confirmation Rubric v1

This rubric is frozen before confirmation-task answers are generated. The
evaluator receives only the question, anonymous answer, cited excerpts, and
declared gaps. Score each answer independently.

## Claim support — 0 to 30

- **30:** every substantive factual or causal claim is directly supported by
  an included excerpt, or is explicitly labeled as an inference.
- **24:** one minor detail extends beyond the excerpts without changing the
  conclusion.
- **18:** several useful details are plausible but not evidenced.
- **8:** central conclusions depend on evidence not supplied.
- **0:** citations are fabricated, contradictory, or unrelated to the central
  answer.

Interpolate only between the nearest anchors. Recommendations count as claims
when they imply facts about effectiveness, risk, or required practice.

## Question coverage — 0 to 20

- **20:** all important facets supported by the supplied evidence are answered.
- **16:** the central question is answered with one minor supported facet
  omitted.
- **10:** roughly half of the important supported facets are covered.
- **4:** the answer addresses only a narrow side issue.
- **0:** it does not answer the question.

Do not penalize a facet that the answer correctly identifies as absent from the
available evidence.

## Gap handling — 0 to 15

- **15:** every important missing or partial facet is bounded accurately,
  whether inline or in `declared_gaps`.
- **12:** material gaps are bounded, with one minor omission.
- **8:** uncertainty is acknowledged but too generally to guide a user.
- **4:** at least one material evidence gap is left implicit.
- **0:** the answer presents unsupported material with false certainty.

An empty `declared_gaps` list is not automatically wrong. Inline limitations
receive equal credit when they are clear and specific.

## Unsupported-claim avoidance — 0 to 15

- **15:** no substantive unsupported detail is presented as established fact.
- **12:** one low-impact unsupported extension appears.
- **8:** multiple extensions appear, but the core answer remains supported.
- **4:** unsupported detail materially changes the advice or conclusion.
- **0:** most of the answer is ungrounded.

Do not double-penalize the mere absence of a citation here and under claim
support. Use this component for the burden/risk created by unsupported content;
use claim support for how much of the answer is evidenced.

## Practical usefulness — 0 to 10

- **10:** direct, organized, proportionate, and actionable.
- **8:** useful with minor redundancy or abstraction.
- **5:** understandable but incomplete, diffuse, or overly generic.
- **2:** difficult to apply.
- **0:** unusable or misleading.

Length and technical vocabulary do not earn points.

## Citation precision — 0 to 10

- **10:** every excerpt is relevant to a nearby claim and no citation is
  decorative.
- **8:** one citation is broader than the claim.
- **5:** several citations are only loosely connected.
- **2:** most citations do not establish their associated claims.
- **0:** citations are absent where required or materially misleading.

Path existence and exact-excerpt matching are deterministic harness checks,
not evaluator judgment.

## Critical failure

Set `critical_failure=true` only for:

- a fabricated or prohibited external citation that passed through the
  deterministic checks unexpectedly;
- advice that creates an immediate material safety/security risk;
- hidden access to arm identity, evaluator-only material, or the other arm;
- a central conclusion contradicted by the supplied excerpts.

Ordinary incompleteness or a low score is not a critical failure.

## Confirmation interpretation

The primary search quality outcome is the 100-point total. Critical failures
remain a separate veto. Scores are paired by task and averaged within task
across repeat trials before inference. Evaluator identity/version and every
evaluator call must be recorded.
