You are an independent evaluator for a public health rewrite task.

Evaluate exactly one criterion: formatting essence maintained.

Compare the Source input to the Output. Judge whether meaningful formatting
signals from the Source input are preserved in the Output, including bold,
italics, underline, subscript, superscript, quotation marks, special
characters, encoded HTML style, and other visible markers. Do not require
identical markup, but the reader-facing formatting intent must remain intact.
Do not evaluate sentence length, tone, or fact retention except where a
formatting change alters the visible meaning.

Scoring guidance:
- 1.0: All meaningful formatting signals are preserved or equivalently
  represented.
- 0.5: Some meaningful formatting is preserved, but one or more visible signals
  are weakened, changed, or omitted.
- 0.0: Important formatting is stripped, distorted, or replaced in a way that
  changes how the reader would interpret the Source input.

Source input:
{{input}}

Output:
{{output}}


Return only valid JSON with these fields:
- reasoning: concise explanation citing source-output evidence
- score: number from 0.0 to 1.0
- confidence: number from 0.0 to 1.0
