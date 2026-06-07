# rephrasy-skills

Score text for AI detectability and humanize AI-generated text, without leaving Claude Code.

`rephrasy-skills` packages two Claude Code skills backed by the [Rephrasy API](https://www.rephrasy.ai/api-solution): `/rephrasy:ai-detect` scores any text 0 (human) to 100 (AI) with a per-sentence breakdown, and `/rephrasy:humanize` rewrites AI-flavored text to read as human (Rephrasy's v3 model with the professional style by default). The skills encode live-verified API behavior — including the places where the API's real behavior diverges from its public docs.

## Installation

### Claude Code plugin

From inside Claude Code:

```text
/plugin marketplace add jhubbardsf/rephrasy-skills
/plugin install rephrasy@rephrasy-skills
/reload-plugins
```

Then run:

```text
/rephrasy:ai-detect <file-or-text>
/rephrasy:humanize <file-or-text>
```

Claude Code plugin install specs use `plugin@marketplace`. Here, `rephrasy` is the plugin name and `rephrasy-skills` is the marketplace name from `.claude-plugin/marketplace.json`. Plugin skills are namespaced by plugin name.

### One-line installer

```bash
curl -fsSL https://raw.githubusercontent.com/jhubbardsf/rephrasy-skills/main/install.sh | bash
```

To install at project or local scope:

```bash
curl -fsSL https://raw.githubusercontent.com/jhubbardsf/rephrasy-skills/main/install.sh | bash -s -- --scope project
```

## Requirements

- Claude Code with plugin support
- `python3` (the bundled helpers are stdlib-only — zero pip dependencies)
- A `REPHRASY_API_KEY` environment variable ([get a key](https://www.rephrasy.ai) — this is a paid API; every call costs credits)

## Usage

```text
/rephrasy:ai-detect draft.md
/rephrasy:ai-detect "paste some prose here"
/rephrasy:humanize draft.md                       # -> draft_rephrasy.md next to the input
/rephrasy:humanize draft.md --verify              # re-score the result with the detector
/rephrasy:humanize draft.md --iterate --threshold 40
/rephrasy:humanize draft.md --style creative      # override the professional default
/rephrasy:humanize draft.md --model "Undetectable Model v2"
```

The humanize skill defaults to **model `v3` + style `professional`** and never overwrites the input unless `--in-place` is passed explicitly. `--iterate` re-humanizes up to 3 passes, keeps the best-scoring version, and aborts (rather than burning paid passes) if the API errors.

## Helper CLIs

The plugin bundles two stdlib-only Python scripts that also work standalone from any shell:

```bash
python3 plugins/rephrasy/scripts/rephrasy_detect.py FILE [--mode depth|default] [--json] [--threshold N] [--top K]
python3 plugins/rephrasy/scripts/rephrasy_humanize.py FILE [-o OUT] [--in-place] [--style STYLE] [--no-style] [--model MODEL] [--language NAME] [--json]
```

Both accept a file path, `-` for stdin, or `--text "literal text"`.

| Behavior | Detail |
| --- | --- |
| Exit codes | `0` success · `1` over `--threshold` (detect only) · `2` any error — loops can distinguish "score too high" from "API is down" |
| Output naming | `foo.txt` → `foo_rephrasy.txt` (non-destructive by default); `--in-place` writes atomically via temp file + rename |
| Cost reporting | The humanizer prints `cost=… credits` to stderr after every call, including `--json` runs |
| Errors | Clean one-line `error: …` messages — no tracebacks, including response-phase timeouts and non-JSON 200 bodies |

## API facts verified live (2026-06-07)

These differ from, or go beyond, Rephrasy's public docs — the skills encode the observed behavior:

- **Detector direction**: 0 = human, 100 = AI in **both** default and depth mode. The docs claim non-depth modes are inverted; they are not.
- Default mode also returns per-sentence scores, just coarser than `depth`. The skills always use `depth`.
- **The detector runs hot on formal prose**: a verified-human (GPTZero 100%) formal sample scored **70.28**; casual human text scored **7.35**. The skills' verdict bands account for this.
- Humanizer `costs` is a plain number of credits, not the `{"total": ...}` object shown in the docs.
- `new_flesch_score` can be negative for dense prose.
- An invalid key returns **HTTP 400** `{"error":"Invalid API Key"}`, not the documented 401 (both are handled).
- `style: "professional"` costs ~3x a no-style call and yields more formal (hence more Rephrasy-detectable) output. It stays the default because GPTZero — not Rephrasy's own detector — is the usual real target.

## Configuration

```bash
export REPHRASY_API_KEY=...   # required
```

Everything else is per-invocation flags. The humanize defaults (v3 + professional) are set in the skill and overridable with `--model` / `--style` / `--no-style`.

## Repository layout

```
.claude-plugin/marketplace.json     # marketplace manifest (name: rephrasy-skills)
plugins/rephrasy/                   # the plugin (name: rephrasy)
├── .claude-plugin/plugin.json
├── scripts/                        # stdlib-only Python helpers
└── skills/
    ├── ai-detect/SKILL.md
    └── humanize/SKILL.md
skills/, commands/                  # author's personal (non-plugin) install; same scripts
docs/index.html                     # GitHub Pages site
```

## GitHub Pages

The project site lives in `docs/index.html`. Configure GitHub Pages to serve from `/docs` on the default branch.

## Troubleshooting

### `/plugin` is not recognized

Update Claude Code. Plugin commands require a recent Claude Code release.

### `error: REPHRASY_API_KEY not set`

Export the key in the shell Claude Code runs from, or add it to your shell profile.

### Scores seem high on text a human wrote

Expected — see the calibration table in the `ai-detect` skill. Formal, structured prose scores 60–75 on this detector even when verified human. Read the per-sentence breakdown instead of trusting the single number.

## Disclaimer

Independent client — not affiliated with or endorsed by Rephrasy. API usage is billed to your Rephrasy account.

## License

MIT
