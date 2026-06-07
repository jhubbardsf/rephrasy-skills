# rephrasy-skills

Claude Code plugin marketplace wrapping the Rephrasy AI-detector and humanizer APIs, published as `jhubbardsf/rephrasy-skills`. See README.md for layout, verified API behavior, and usage.

## Dual layout — public plugin vs personal install

- `plugins/rephrasy/` is the **public, portable plugin** (marketplace name `rephrasy-skills`, plugin name `rephrasy`). Its skills reference scripts via `${CLAUDE_PLUGIN_ROOT}` and must contain nothing machine-specific.
- Root `skills/` and `commands/` are **Josh's personal install** — symlinked into `~/.claude/skills/rephrasy-{detect,humanize}` and `~/.claude/commands/{ai-detect,rephrasy-humanize}.md`. They reference scripts by absolute path (`/Users/josh/Engineering/rephrasy-api-skills/plugins/rephrasy/scripts/`) and may carry personal context (StealthHumanizer cross-reference, secrets.zsh fallback).
- The Python scripts exist **once**, in `plugins/rephrasy/scripts/` — both layers share them.
- **Sync rule**: when changing skill content, edit the plugin version first, then mirror substantive changes into the personal version (minus `${CLAUDE_PLUGIN_ROOT}` and plus personal context). Calibration tables and API-quirk notes must stay identical between the two.

## Working on this repo

- `plugins/rephrasy/scripts/*.py` are **stdlib-only by design** — no pip dependencies, ever. They must run on a bare macOS `python3`.
- **Standing defaults (Josh's explicit preference): model `v3`, style `professional`.** `resolve_style()` in `rephrasy_humanize.py` implements this — professional is applied only for v3, never sent to other models. Don't change defaults without asking.
- Detector score direction is 0 = human, 100 = AI in **both** modes — verified live 2026-06-07 against known-human/known-AI samples. The public docs claim non-depth modes are inverted; they are wrong. Don't "fix" the scripts to match the docs.
- Calibration data in the SKILL.md files (70.28 for formal human prose, 7.35 casual human, 99.87/92.60 single-pass humanize comparison) came from live calls on 2026-06-07. If Rephrasy retrains, re-run the calibration before editing those tables.
- Output naming uses the `_rephrasy` suffix deliberately — the local StealthHumanizer project already owns `_humanized`, and the two must not clobber each other.
- **Exit-code contract**: both scripts exit 2 on any error (via the `die()` helper); detect exits 1 only for `--threshold` exceeded. Iterate loops depend on this to avoid burning paid passes during API outages — don't collapse errors back to exit 1.
- Network handlers must catch `OSError` after `HTTPError`/`URLError`: response-phase timeouts raise raw `TimeoutError` (not wrapped in `URLError`), and that's the likeliest real-world failure for the humanizer, which works server-side before responding.
- Every API call costs credits. When testing changes, use short texts and prefer the free validation paths (arg errors, `--help`) where possible.

## Publishing

- Marketplace manifest: `.claude-plugin/marketplace.json` (marketplace `rephrasy-skills`); plugin manifest: `plugins/rephrasy/.claude-plugin/plugin.json`. Bump `version` in plugin.json on user-facing changes.
- Install flow users follow: `/plugin marketplace add jhubbardsf/rephrasy-skills` → `/plugin install rephrasy@rephrasy-skills`. `install.sh` automates this via the `claude` CLI.
- GitHub Pages serves `docs/index.html` from `/docs` on `main`.
- Validate before pushing: `claude plugin validate .` (if available) plus `python3 -m py_compile plugins/rephrasy/scripts/*.py`.

## Testing changes

```bash
# Free (no API call): validation/error paths
python3 plugins/rephrasy/scripts/rephrasy_humanize.py --text "hi" --style creative --no-style  # expect error, exit 2
python3 plugins/rephrasy/scripts/rephrasy_detect.py --text "   "                              # expect error, exit 2

# Paid (tiny): end-to-end
python3 plugins/rephrasy/scripts/rephrasy_detect.py --text "some sample text to score"
python3 plugins/rephrasy/scripts/rephrasy_humanize.py --text "some sample text to rewrite"
```
