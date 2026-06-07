# rephrasy-api-skills

Claude Code skills and slash commands for the [Rephrasy](https://www.rephrasy.ai/api-solution) AI-detection and humanizer APIs. Repo is the single source of truth; the global `~/.claude` entries are symlinks into it.

## What's here

| Path | What it is |
|---|---|
| `scripts/rephrasy_detect.py` | Stdlib-only Python CLI for the Detector API |
| `scripts/rephrasy_humanize.py` | Stdlib-only Python CLI for the Humanizer API |
| `skills/rephrasy-detect/` | Skill: score text 0 (human) – 100 (AI) with per-sentence breakdown |
| `skills/rephrasy-humanize/` | Skill: rewrite AI text to read human (v3 + professional defaults) |
| `commands/ai-detect.md` | `/ai-detect` slash command → rephrasy-detect skill |
| `commands/rephrasy-humanize.md` | `/rephrasy-humanize` slash command → rephrasy-humanize skill |

Installed via symlinks:

```
~/.claude/skills/rephrasy-detect      -> skills/rephrasy-detect
~/.claude/skills/rephrasy-humanize    -> skills/rephrasy-humanize
~/.claude/commands/ai-detect.md       -> commands/ai-detect.md
~/.claude/commands/rephrasy-humanize.md -> commands/rephrasy-humanize.md
```

## Auth

`REPHRASY_API_KEY` — read from the environment, falling back to `~/.config/zsh/secrets.zsh`. Never passed on the command line, never logged.

## Usage

In any Claude Code session:

```
/ai-detect draft.md
/ai-detect "paste some prose here"
/rephrasy-humanize draft.md
/rephrasy-humanize draft.md --verify
/rephrasy-humanize draft.md --iterate --threshold 40
/rephrasy-humanize draft.md --style creative
```

Directly from a shell:

```bash
# Detect (depth mode default: per-sentence scores)
python3 scripts/rephrasy_detect.py draft.md
python3 scripts/rephrasy_detect.py --text "some text"
cat draft.md | python3 scripts/rephrasy_detect.py -
python3 scripts/rephrasy_detect.py draft.md --threshold 40 && echo "passes"

# Humanize (defaults: model v3, style professional)
python3 scripts/rephrasy_humanize.py draft.md            # -> draft_rephrasy.md
python3 scripts/rephrasy_humanize.py draft.md --in-place # atomic overwrite
python3 scripts/rephrasy_humanize.py --text "some text"  # -> stdout (-o FILE also works)
python3 scripts/rephrasy_humanize.py draft.md --no-style # v3 built-in behavior, ~3x cheaper
```

### Python API examples (for embedding elsewhere)

```python
import json, os, urllib.request

KEY = os.environ["REPHRASY_API_KEY"]

def rephrasy(url, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)

# Detect: 0 = human, 100 = AI (both modes -- the public docs are wrong about inversion)
scores = rephrasy("https://detector.rephrasy.ai/detect_api",
                  {"text": "...", "mode": "depth"})
print(scores["scores"]["overall"], scores["sentences"])

# Humanize: v3 + professional defaults
out = rephrasy("https://v2-humanizer.rephrasy.ai/api/",
               {"text": "...", "model": "v3", "style": "professional",
                "words": True, "costs": True})
print(out["output"], out["new_flesch_score"], out["costs"])
```

## API facts verified live (2026-06-07)

These differ from or go beyond the public docs:

- **Detector direction**: 0 = human, 100 = AI in **both** default and depth mode. The docs claim non-depth modes are inverted; they are not.
- Default mode also returns per-sentence scores, just coarser than `depth`. Use `depth`.
- Humanizer `costs` is a plain number of credits, not `{"total": ...}`.
- `new_flesch_score` can be negative for dense prose.
- The detector runs hot on formal prose: a verified-human (GPTZero 100%) formal sample scored **70.28**; casual human text scored **7.35**.
- `style: "professional"` costs ~3x a no-style call and yields more formal (hence more Rephrasy-detectable) output. GPTZero is the usual real target, so this is an accepted trade-off.

## Cost model

Word-based pricing is enabled by default (`words: true`). The marketing page quotes "0.1 credits flat + 0.1 per 100 words", but measured charges run far lower (0.000726–0.002178 credits for a 41-word humanize call) — trust the per-call `cost=` line the humanize script prints to stderr, not the formula. The detector API returns no cost field, but detector calls still bill credits. Skills are instructed to surface costs to the user.

## Exit codes

Both scripts: `0` = success, `2` = any error (bad input/flags, missing key, API or network failure — clean one-line messages, no tracebacks). The detect script additionally exits `1` when `--threshold N` is given and the score exceeds N, so loops can distinguish "score too high" (1) from "API is down" (2).
