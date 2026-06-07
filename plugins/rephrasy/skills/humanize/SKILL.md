---
name: humanize
description: Humanize AI-generated text via the Rephrasy Humanizer API (cloud service, costs credits per call). Use when (1) the user asks to humanize text or make it pass AI detectors, (2) text flagged by the ai-detect skill needs rewriting. Defaults to model v3 with style professional. Output goes next to input as foo.txt -> foo_rephrasy.txt. Supports verify (re-detect) and iterate-until-threshold. Requires the REPHRASY_API_KEY environment variable.
argument-hint: "<file-or-text> [--style professional|creative|journalistic] [--no-style] [--model MODEL] [--language NAME] [--verify] [--iterate] [--threshold N] [-o OUT] [--in-place]"
allowed-tools:
  - Read
  - Bash(python3 *)
  - Bash(cat *)
  - Bash(jq *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(cp *)
  - Bash(mv *)
  - Bash(echo *)
  - Bash(printf *)
  - Bash(wc *)
  - Bash(mktemp *)
---

# humanize — rewrite AI text to read as human via the Rephrasy API

Drives the Rephrasy Humanizer API (`https://v2-humanizer.rephrasy.ai/api/`) through a stdlib-only Python helper bundled with this plugin. **Every call costs credits** — don't re-humanize unchanged text, and tell the user the cost after each run. (The marketing page quotes "0.1 credits flat + 0.1 per 100 words", but measured charges were far lower: 0.000726–0.002178 credits for a 41-word call. Trust the per-call `cost=` the script prints, not the formula.)

## Defaults — do not change unless asked

- **Model: `v3`** (Rephrasy's best model for GPTZero).
- **Style: `professional`** (this plugin's standing default). The script applies it automatically; only override when the user explicitly asks for `creative`, `journalistic`, or no style (`--no-style`).
- Word-based pricing on, costs reported, language auto-detected.

## Helper script

```bash
HUMANIZE="${CLAUDE_PLUGIN_ROOT}/scripts/rephrasy_humanize.py"
DETECT="${CLAUDE_PLUGIN_ROOT}/scripts/rephrasy_detect.py"

python3 "$HUMANIZE" draft.txt                    # -> draft_rephrasy.txt (v3, professional)
python3 "$HUMANIZE" draft.txt -o final.txt       # explicit output
python3 "$HUMANIZE" draft.txt --in-place         # overwrite input (confirm with user first)
python3 "$HUMANIZE" --text "literal text"        # string -> stdout (-o FILE also works)
cat draft.txt | python3 "$HUMANIZE" -            # stdin -> stdout
python3 "$HUMANIZE" draft.txt --style creative   # explicit style override
python3 "$HUMANIZE" draft.txt --model "Undetectable Model v2"  # style auto-dropped for non-v3
```

The script requires the `REPHRASY_API_KEY` environment variable (get a key at https://www.rephrasy.ai). Cost/flesch metadata prints to stderr; humanized text or `Wrote: <path>` to stdout. Exit codes: 0 = success, 2 = any error. `-o` works with every input form (file, `--text`, stdin); `--in-place` writes atomically and conflicts with `-o`/`--stdout`.

Note: `--verify`, `--iterate`, and `--threshold` are **skill-level directives** (they shape the workflow below), not flags the humanize script accepts — don't pass them to it. `--threshold` belongs to the detect script.

## Workflow

1. **Locate input.** File path → verify it exists and is text. Inline prose → use `--text` (or a temp file via `mktemp` for long text).
2. **Humanize** with defaults. Never `--in-place` without the user asking for it — the default `foo_rephrasy.txt` output is non-destructive.
3. **Verify (recommended, costs one detector call).** Score the output:
   ```bash
   python3 "$DETECT" draft_rephrasy.txt
   ```
4. **Report**: output path, before/after detector scores if both known, cost, and flesch score.

## Iterate mode (only when the user asks for it)

Re-humanize until the detector score is at or under threshold (default **40**), with a hard cap of **3 humanize passes total**. Drive the loop yourself, one pass at a time — do not script it blind:

1. Pass N: `python3 "$HUMANIZE" <latest> -o work/passN.txt` (numbered files — never `--in-place` — so every version survives).
2. Score it: `python3 "$DETECT" work/passN.txt --json | jq '.scores.overall'`. Record the score.
3. Decide: score ≤ threshold → stop. Detect/humanize exited 2 (API/key/network error) → **abort immediately**, don't burn more paid passes. Otherwise, if fewer than 3 passes done, feed `passN.txt` into pass N+1.
4. Finish: copy the **best-scoring** pass (not necessarily the last — passes can regress) to the final output path. Report every pass's score and the summed cost.

Both scripts exit **2** on errors and the detect script exits **1** only for threshold-exceeded, so error-vs-score is always distinguishable.

## Score expectations (calibrated live 2026-06-07)

Detector scale: 0 = human, 100 = AI. Controlled single-pass comparison on the same ~40-word formal AI sample:

| Variant | Rephrasy detector score | Cost (credits) |
|---|---|---|
| v3 + `professional` (default) | 99.87 | 0.002178 |
| v3 no style | 92.60 | 0.000726 |

Takeaways:

- **Short formal texts stay hot on Rephrasy's own detector even after humanizing.** The detector overrates formality (verified-human formal prose scores 60–75). Longer texts fare better; a different short sample scored 55 after one no-style pass.
- **`professional` style costs ~3x** the no-style call. It stays the default (GPTZero — not this detector — is the usual real target, and formal output is usually what users want), but mention the trade-off if the user is iterating on cost.
- A threshold of **≤ 40** is a realistic multi-pass target for normal-length documents; chasing ≤ 10 usually requires a casual register. For short snippets, judge by trend across passes rather than absolute score, and don't burn more than 3 passes. See the `ai-detect` skill for the full calibration table.

## API response quirks (verified live)

- `costs` is a **plain number** (credits), not the `{"total": ...}` object the marketing page shows.
- `new_flesch_score` can be **negative** for dense prose — not an error.
- `language` is auto-detected when omitted; only pass it if detection gets it wrong.
- `style` is **v3-only**; the API may 4xx if sent to other models. The script drops the default style automatically for non-v3 models.

## Failure modes

- Invalid key → **HTTP 400** `{"error":"Invalid API Key"}` in practice (the docs say 401; the script handles both). Check `echo ${REPHRASY_API_KEY:+set}`.
- `422` → empty/malformed input; the script guards against empty text before calling.
- Very large files: the API has no documented size limit, but split anything over ~5,000 words into sections (paragraph boundaries) and humanize each — also keeps a failed call from wasting the whole budget.

## Raw API reference (fallback if the script is unavailable)

```bash
jq -n --rawfile t draft.txt \
  '{text: $t, model: "v3", style: "professional", words: true, costs: true}' | \
  curl -sS https://v2-humanizer.rephrasy.ai/api/ \
    -H "Authorization: Bearer $REPHRASY_API_KEY" \
    -H "Content-Type: application/json" -d @-
```

Response shape: `{"output": "<humanized text>", "new_flesch_score": <float>, "costs": <float>}`.
Always build the JSON body with `jq` (`--rawfile`/`--arg`) — never interpolate raw text into a shell string.
