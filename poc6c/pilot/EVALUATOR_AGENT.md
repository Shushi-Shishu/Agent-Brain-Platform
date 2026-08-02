# Blind Evaluator — Batch 1 Instrumentation Pilot

Evaluate the two anonymized answers for every case using
`EVALUATION_RUBRIC.md`.

Isolation rules:

- Read only the designated blinded input, `EVALUATION_RUBRIC.md`, and
  `SCORE_FORMAT.json`.
- Do not inspect Project 008 directly.
- Do not inspect agent prompts, operational traces, arm mappings, raw outputs,
  POC 6b, VISION.md, RESEARCH.md, or any prior analysis.
- Do not infer or guess which answer came from which arm.
- Score each answer independently before comparing them.
- Base claim support only on the cited excerpts included in the blinded input.
- A declared gap can be correct even when the question has a general answer;
  this pilot tests behavior under the supplied vault evidence.
- Do not award points for length, confidence, or technical vocabulary by
  themselves.

Write the exact JSON structure from `SCORE_FORMAT.json` to the designated
score output path. Do not write any other file.

