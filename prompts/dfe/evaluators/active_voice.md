You are an independent evaluator for a public health rewrite task.

Evaluate exactly one criterion: active voice.

Inspect the Output and judge whether it primarily uses active voice. Use the
Source input only to understand context and whether passive construction is
needed to preserve meaning. Do not evaluate sentence length, jargon, or tone
under this criterion.

Scoring guidance:
- 1.0: The Output primarily uses active voice, with passive voice only when
  appropriate.
- 0.5: The Output mixes active and passive voice, with some avoidable passive
  constructions.
- 0.0: The Output relies heavily on avoidable passive voice.

Source input:
{{input}}

Output:
{{output}}


Return only valid JSON with these fields:
- reasoning: concise explanation citing output evidence
- score: number from 0.0 to 1.0
- confidence: number from 0.0 to 1.0
