# Batch 1 Blind Search Evaluation Rubric

This is an instrumentation rubric, not a confirmation verdict.

The evaluator receives:

- the question;
- an anonymized answer;
- cited Project 008 passages;
- declared evidence gaps.

The evaluator must not receive the arm, agent prompt, operational trace,
POC 6b candidate labels, or assistant pre-review.

## Quality score — 100 points

| Component | Points | Meaning |
|---|---:|---|
| Claim support | 30 | Substantive claims are supported by the supplied cited passages |
| Question coverage | 20 | The answer addresses the important parts that the vault evidence can support |
| Gap handling | 15 | Missing or partial vault evidence is identified and uncertainty is bounded |
| Unsupported-claim avoidance | 15 | The answer does not silently extend beyond its evidence |
| Practical usefulness | 10 | The response is direct, structured, and usable |
| Citation precision | 10 | Citations are relevant to the nearby claims and not decorative |

## Deterministic checks outside the score

- cited path exists in the frozen indexed corpus;
- supporting excerpt is an exact substring of the indexed note body;
- cited note appears in `documents_read`;
- no web or out-of-scope source is cited;
- search and read budgets are respected;
- required output fields are present.

Any fabricated citation, prohibited external source, or hidden access to the
other arm/evaluator is a critical failure.

## Pilot interpretation

The pilot may identify:

- broken tracing or citation validation;
- rubric ambiguity;
- configured-prompt overhead;
- obvious answer/gap-handling differences;
- whether the agents can follow the matched output contract.

It may not establish efficacy, rank configurations, set final thresholds, or
support a market/value percentage. These cases are permanently excluded from
confirmation.
