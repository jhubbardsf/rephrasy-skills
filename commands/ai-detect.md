---
description: Check whether text is AI-detectable via the Rephrasy Detector API. Scores 0 (human) to 100 (AI) with a per-sentence breakdown of the most AI-flagged lines. Accepts a file path, '-' for piped text, or inline prose. Costs API credits per call.
argument-hint: "<file-or-text> [--mode depth|default] [--json] [--threshold N] [--top K]"
allowed-tools:
  - Skill(rephrasy-detect)
  - Read
  - Bash(python3 *)
  - Bash(cat *)
  - Bash(jq *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(echo *)
  - Bash(wc *)
---

# /ai-detect — score text for AI detectability (Rephrasy)

Invoke the `rephrasy-detect` skill with the arguments below. The skill drives the stdlib-only helper at `/Users/josh/Engineering/rephrasy-api-skills/plugins/rephrasy/scripts/rephrasy_detect.py`.

Arguments: `$ARGUMENTS`

## Argument handling

- **A file path** → pass it through to the skill as-is.
- **Inline prose** (no path-like token) → pass it via `--text`.
- **No arguments** → ask what to score: a file, pasted text, or the last text produced in this conversation.
- All flags (`--mode`, `--json`, `--threshold`, `--top`) pass through unchanged. Default mode is `depth` (finer per-sentence scores, same cost).

## Reporting

Report the overall score with direction (0 = human, 100 = AI), the verdict, and the top AI-flagged sentences. Remember this detector runs hot on formal prose — a verified-human formal sample scored 70, so interpret 60–75 scores on professional writing with that context (full calibration table lives in the skill).

If the score is high and the user wants it fixed, offer `/rephrasy-humanize`.
