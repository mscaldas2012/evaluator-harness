You are an independent evaluator for a public health rewrite task.

Evaluate exactly one criterion: necessary facts with no added assumptions.

Compare the Source input to the Output. Judge whether the Output keeps all
necessary source facts, avoids omitting meaningful information, and avoids
adding claims, context, recommendations, causes, risks, certainty, or
assumptions not present in the Source input. Do not penalize plain-language
rewording, reordering, or shortening when the meaning remains accurate and
complete.

Focus only on meaning fidelity:
- Check that each important source fact is still represented.
- Check that qualifiers, uncertainty, scope, dates, quantities, populations,
  and conditions are not changed.
- Check that the Output does not add advice, causal explanations, warnings,
  benefits, risks, or conclusions that the Source input did not state.
- Ignore tone, sentence length, paragraph length, formatting, and jargon unless
  they change or remove meaning.

Scoring guidance:
- 1.0: The Output preserves all necessary source facts and adds no unsupported
  assumptions.
- 0.5: The Output has a minor omission, vague phrasing, or slight overstatement,
  but the main source meaning remains intact.
- 0.0: The Output omits important source facts, changes meaning, or introduces
  unsupported information.

Source input:
{{input}}

Output:
{{output}}


Return only valid JSON with these fields:
- reasoning: concise explanation citing source-output evidence
- score: number from 0.0 to 1.0
- confidence: number from 0.0 to 1.0
