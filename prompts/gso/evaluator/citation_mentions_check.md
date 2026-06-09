You are evaluating one dimension: CDC citation and CDC webpage mention presence.

Review the assistant response for the user query.

Definitions:
- A CDC citation is an explicit URL in the assistant response whose host is cdc.gov or a CDC subdomain, including www.cdc.gov and wwwnc.cdc.gov.
- A CDC webpage mention is any explicit CDC URL in the assistant response, or a plain-text reference to a CDC webpage or CDC page title.
- A general CDC mention such as "CDC says" or "according to CDC" is not a citation unless an explicit URL is present.
- Treat only explicit URLs in the assistant response as citations.
- If you have web access, verify each explicit CDC URL by checking whether the page exists on the CDC site. CDC often returns a friendly "page not available" page instead of a 404; treat that as invalid.
- If you do not have web access, do not invent verification results. Use the URL text, host, path, and surrounding response context to judge likely validity, and note that live verification was unavailable.

Scoring:
- score = 1 when the response includes at least one explicit CDC URL citation that appears to point to an available CDC page.
- score = 0 when no explicit CDC URL citation is present, or when the only explicit CDC URL appears invalid or unavailable.

In the reasoning, include these exact labels with TRUE or FALSE:
- cdc_citation_present: TRUE/FALSE
- cdc_webpage_mentioned: TRUE/FALSE
- cdc_url_valid: TRUE/FALSE

User query:
{{input}}

Assistant response:
{{output}}

Return JSON with reasoning, score from 0 to 1, and confidence from 0 to 1.
