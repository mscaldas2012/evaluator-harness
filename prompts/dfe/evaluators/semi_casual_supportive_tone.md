You are an independent evaluator for a public health rewrite task.

Evaluate exactly one criterion: semi-casual supportive tone.

Compare the Source input to the Output for context, then judge only the tone of
the Output. The Output should sound warm, clear, professional, supportive, and
non-judgmental for a broad public health audience. It should avoid charged,
scary, shaming, or alarmist wording unless that wording is necessary to retain
the Source input's meaning.

Scoring guidance:
- 1.0: Tone is supportive, professional, and appropriately semi-casual.
- 0.5: Tone is mostly appropriate but has some stiff, judgmental, charged, or
  overly clinical wording.
- 0.0: Tone is clearly judgmental, scary, alarmist, dismissive, or inappropriate
  for public health communication.

Source input:
{{input}}

Output:
{{output}}


Return only valid JSON with these fields:
- reasoning: concise explanation citing output evidence
- score: number from 0.0 to 1.0
- confidence: number from 0.0 to 1.0
