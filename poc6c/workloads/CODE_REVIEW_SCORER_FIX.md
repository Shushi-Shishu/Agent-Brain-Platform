# Code-review scorer repair log

During the first CRV-P001 pair, both agents identified the two intended defect
locations. Each used the reasonable category label `authentication` for the
case-sensitive bearer-token defect, while the private inventory used
`security`.

The original scorer required exact category-string equality even though the
public output contract intentionally allowed open-vocabulary lowercase
categories. It therefore reported recall 0.4 and one false positive for both
arms. That score was an evaluator artifact, not agent behavior.

Repair:

- matching now uses the locked file and line tolerance;
- category synonyms no longer turn a correctly located defect into a false
  positive;
- fixture tests now require correct matching under alternate valid category
  names;
- the first pre-repair P001 score reports are retained with
  `pre_scorer_fix` in their names and excluded from summaries;
- P001 is rerun as a fresh matched pair after the repair.

The repair was made before scoring CRV-P002–P005. It changes no public source,
task, agent prompt, finding budget, defect location, or severity weight.

## Schema duplicate repair

CRV-P002 exposed a second contract defect. The inventory intentionally combines
two missing validations at one source line. Both agents reasonably reported
the page and size validations separately, using the same file, line, and
category. The validator rejected them as duplicates even though their
explanations and impacts were distinct.

The validator now rejects exact duplicate finding objects. Findings that share
a location/category but describe distinct actionable defects pass the JSON
contract and are left to the private scorer to match or count as review noise.
The existing exact-duplicate regression still passes. CRV-P002 generic is
rerun on a fresh workspace after this repair; pre-repair reports are excluded.
