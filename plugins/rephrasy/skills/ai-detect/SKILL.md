---
name: ai-detect
description: Check whether text is AI-detectable using the Rephrasy Detector API. Use when (1) the user asks if text "sounds AI", "is AI-detectable", or wants an AI-detection score, (2) verifying humanized output before delivery. Scores 0 (human) to 100 (AI) with per-sentence breakdown. Requires the REPHRASY_API_KEY environment variable. Costs API credits per call.
argument-hint: "<file-or-text> [--mode depth|default] [--json] [--threshold N] [--top K]"
allowed-tools:
  - Read
  - Bash(python3 *)
  - Bash(cat *)
  - Bash(jq *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(echo *)
  - Bash(printf *)
  - Bash(wc *)
---

# ai-detect — score text for AI detectability

Drives the Rephrasy Detector API (`https://detector.rephrasy.ai/detect_api`) through a stdlib-only Python helper bundled with this plugin. No pip installs needed.

## Helper script

```bash
DETECT="${CLAUDE_PLUGIN_ROOT}/scripts/rephrasy_detect.py"

python3 "$DETECT" path/to/file.txt              # score a file (depth mode, default)
python3 "$DETECT" --text "literal text here"    # score a string
cat file.txt | python3 "$DETECT" -              # score stdin
python3 "$DETECT" file.txt --json               # raw API JSON (per-sentence map included)
python3 "$DETECT" file.txt --threshold 40       # exit 1 if overall > 40 (for loops)
python3 "$DETECT" file.txt --top 10             # show 10 most AI-flagged sentences
```

The script requires the `REPHRASY_API_KEY` environment variable (get a key at https://www.rephrasy.ai). If missing it exits with a clear error — never paste the key on the command line.

Exit codes: **0** = success (and under threshold, if given), **1** = score exceeded `--threshold`, **2** = any error (bad input, missing key, API/network failure). Loops can therefore tell "score too high" apart from "API is down" — never treat exit 2 as a scoring result.

The detector API returns no cost field (only the humanizer does), but detector calls still bill credits — don't re-score unchanged text.

## Workflow

1. If given a file path, confirm it exists; if given prose in the conversation, pass it with `--text` (or write a temp file for long text).
2. Run the helper. Default mode is `depth` — it returns finer-grained per-sentence scores than the default mode at the same cost (verified live: default mode rounds sentence scores to flat values).
3. Report to the user: the overall score, the verdict, and the most AI-flagged sentences (these are the rewrite targets).
4. If the user wants the text fixed, hand off to the `humanize` skill in this plugin.

## Interpreting scores — IMPORTANT

**0 = human, 100 = AI, in BOTH modes.** The public API docs claim non-depth modes are inverted ("100 indicates human") — this is wrong, verified empirically 2026-06-07 against known-human and known-AI samples.

Live calibration data (2026-06-07):

| Sample | Overall score |
|---|---|
| Blatant AI prose ("Moreover… In conclusion…") | 100.0 |
| Formal human writing (verified 100% human on GPTZero) | 70.28 |
| Rephrasy humanizer output (one no-style pass, a different short sample) | 55.21 |
| Casual human text (typos, slang) | 7.35 |

Consequences:

- **This detector runs hot on formal prose.** A 60–75 score on structured, professional writing does not necessarily mean AI. Look at the per-sentence breakdown before concluding.
- **Short texts score noisy.** Under ~50 words, treat the score as a rough signal only.
- A realistic "humanized enough" target after rewriting is **≤ 40–45**, not ≤ 10. Getting formal prose under 20 usually requires a casual register the user may not want.

## Failure modes

- Invalid key → **HTTP 400** `{"error":"Invalid API Key"}` in practice (the docs say 401; the script handles both). Check `echo ${REPHRASY_API_KEY:+set}`.
- `422` with `Field required` → empty/malformed body; the script guards against empty input before calling.
- All errors exit 2 with a one-line `error: ...` message — no tracebacks, including response-phase timeouts and non-JSON 200 bodies.

## Raw API reference (fallback if the script is unavailable)

```bash
jq -n --rawfile t file.txt '{text: $t, mode: "depth"}' | \
  curl -sS https://detector.rephrasy.ai/detect_api \
    -H "Authorization: Bearer $REPHRASY_API_KEY" \
    -H "Content-Type: application/json" -d @-
```

Response shape: `{"text": ..., "sentences": {"<sentence>": <score>, ...}, "scores": {"overall": <score>}}`.
Always build the JSON body with `jq` (`--rawfile`/`--arg`) — never interpolate raw text into a shell string.
