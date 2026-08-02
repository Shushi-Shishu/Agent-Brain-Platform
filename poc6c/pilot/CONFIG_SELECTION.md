# Search Configuration Selection Log

## Candidate 1 — evidence-marginal stopper

Batch 1 is a seen instrumentation/selection set and can never enter
confirmation.

The first configured candidate passed structural validation but underperformed
the strong generic control in the first blind diagnostic evaluation:

- generic mean quality: 84.6;
- configured mean quality: 76.5;
- paired configured-minus-generic mean: -8.1 points;
- configured wins/ties/losses: 0/0/10.

This is not an efficacy estimate. It is a configuration rejection signal.
Observed resource behavior also moved in the wrong quality/value direction:
the configured arm used fewer note reads (2.5 versus 4.2 per case), but its
answers frequently contained detail not covered by the supplied excerpts and
failed to declare those gaps.

The largest first-evaluator component difference was gap handling
(-6.3 points per case). The first rubric lacks numeric anchors, so a second
independent blind evaluator was run. It also rejected Candidate 1:

- generic mean quality: 87.2;
- configured mean quality: 80.6;
- paired configured-minus-generic mean: -6.6 points;
- configured wins/ties/losses: 0/1/9.

Across 20 blind answers, the evaluators' mean absolute total-score difference
was 4.45 points, their maximum difference was 10, and their within-task arm
preference agreed on 90% of cases. They agreed on all critical-failure flags.
The absolute scales are not calibrated, but the Candidate 1 rejection is not
an idiosyncrasy of one evaluator.

## Candidate 2 — evidence coverage

Candidate 2 changes the controller, not the task, data, tools, or budget:

- retrieval efficiency is subordinated to a quality floor;
- every substantive sentence receives an evidence check;
- every important partial/missing facet must enter the declared-gap ledger;
- stopping requires both sentence support and bounded unresolved facets.

Candidate 2 remains selection-only on Batch 1. It must be frozen before any
untouched confirmation run. If it does not beat or closely match the strong
generic control on the selection set, the platform must retain the generic
baseline for search rather than forcing a configured controller.

## Candidate 2 selection result

Candidate 2 passed the selection signal under two fresh blind evaluators:

- evaluator 1 paired mean: +6.0 points, 8 wins / 0 ties / 2 losses;
- evaluator 2 paired mean: +4.8 points, 9 wins / 0 ties / 1 loss;
- pair-preference agreement: 90%;
- no critical failures assigned by either evaluator.

Operationally, Candidate 2 used all 4 allowed searches per case, read 3.2 notes
per case versus the generic arm's 4.2, and declared 1.2 gaps per case versus
1.3. It therefore repaired Candidate 1's quality loss, but it did not
demonstrate a search-call saving. Provider token, latency, and cost telemetry
remain unavailable.

Absolute generic scores moved substantially between evaluator cohorts, which
confirms that unanchored LLM scores are not a stable absolute scale. The
within-pair preference and delta direction were consistent enough to select
Candidate 2 provisionally, not to claim efficacy.

Candidate 2 is now frozen for the next search stage. Before formal
confirmation, the rubric needs numeric anchors and the runtime must expose a
fixed model identity, usage telemetry, and stronger execution isolation. If
those controls remain unavailable, further search runs remain diagnostic.
