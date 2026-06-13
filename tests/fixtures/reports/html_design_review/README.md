# HTML Design Review Fixture

Generate a representative static HTML comparison report from temporary CSV
fixtures with the focused integration test:

```powershell
uv run pytest -p no:cacheprovider tests/integration/test_html_comparison_report.py
```

For manual design review, run `comparison-report --format html` against any
project report directory containing one baseline CSV and at least one candidate
CSV that references the same `baseline_run_id`. The generated report should be
self-contained, visually polished, readable at desktop and narrow widths, and
free of external asset references.
