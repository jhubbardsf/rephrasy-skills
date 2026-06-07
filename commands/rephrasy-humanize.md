---
description: Humanize AI-generated text via the Rephrasy Humanizer API (cloud, costs credits). Defaults to model v3 with style professional; both overridable. Output goes next to input as foo.txt -> foo_rephrasy.txt. Optionally verifies with the Rephrasy detector or iterates until a target score.
argument-hint: "<file-or-text> [--style professional|creative|journalistic] [--no-style] [--model MODEL] [--language NAME] [--verify] [--iterate] [--threshold N] [-o OUT] [--in-place]"
allowed-tools:
  - Skill(rephrasy-humanize)
  - Read
  - Bash(python3 *)
  - Bash(cat *)
  - Bash(jq *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(cp *)
  - Bash(mv *)
  - Bash(echo *)
  - Bash(wc *)
  - Bash(mktemp *)
---

# /rephrasy-humanize — humanize text via the Rephrasy API

Invoke the `rephrasy-humanize` skill with the arguments below. The skill drives the stdlib-only helper at `/Users/josh/Engineering/rephrasy-api-skills/scripts/rephrasy_humanize.py`.

Arguments: `$ARGUMENTS`

## Argument handling

- **A file path** → humanize it; output defaults to `foo_rephrasy.ext` next to the input.
- **Inline prose** → pass via `--text`; print the humanized result.
- **No arguments** → ask what to humanize: a file, pasted text, or the last text produced in this conversation.
- **Defaults (Josh's standing preference): model `v3`, style `professional`.** Only deviate when the user passes `--model`, `--style`, or `--no-style` explicitly.
- `--verify` → after humanizing, score the output with the detector and report before/after.
- `--iterate [--threshold N]` → follow the skill's iterate loop (default threshold 40, max 3 humanize passes total, keep the best-scoring version). `--verify`/`--iterate`/`--threshold` are workflow directives interpreted by the skill — never pass them to the humanize script.
- `--in-place` → only honor when the user passed it explicitly; never overwrite an input file on your own initiative.

## Reporting

Always report: output location, credits spent (the script prints `cost=` on stderr), flesch score, and detector scores when `--verify`/`--iterate` ran. This is a paid API — surface costs, don't bury them.
