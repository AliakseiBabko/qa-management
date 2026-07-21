# Operator telemetry run note: <run_id>

- case_id: <case_id>
- date: <YYYY-MM-DD>
- runtime: <Codex | Claude Code | Antigravity | manual_script>
- model_label: <model label, if known>
- command_name: <redacted command label, e.g. "qa_manage.py guide">
- baseline_command: <baseline command label, if this case has one>

## What was measured

<one or two sentences on what this run measured and why - no real
names/projects/output text, counts and labels only>

## Result summary

- status: <ok | error>
- elapsed_ms: <number>
- output_chars: <number>
- approximate_output_tokens: <number>
- result_count: <number, if applicable>
- truncated: <yes | no>
- reduction_ratio_vs_baseline: <number, if a baseline was measured in the same pass>

## Token telemetry

- actual_input_tokens: <number, if extracted/measured>
- actual_output_tokens: <number, if extracted/measured>
- actual_cache_creation_tokens: <number, if available>
- actual_cache_read_tokens: <number, if available>
- estimated_cost_usd: <number, if pricing known for model_label>

## Notes

<free text - redacted, no real command output/names/projects>

---
This file is a template. Live run notes are written under `tmp/telemetry/`
(gitignored) by `measure_operator_outputs.py` - they are never committed.
Only use a committed copy of this template's *structure* (not filled-in
content) if you need to hand-author a fully redacted note for the repo.
