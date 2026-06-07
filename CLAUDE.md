# rephrasy-api-skills

Claude Code skills + slash commands wrapping the Rephrasy AI-detector and humanizer APIs. See README.md for layout, verified API behavior, and usage.

## Working on this repo

- `scripts/*.py` are **stdlib-only by design** — no pip dependencies, ever. They must run on a bare macOS `python3`.
- The repo is the source of truth; `~/.claude/skills/rephrasy-*` and `~/.claude/commands/{ai-detect,rephrasy-humanize}.md` are symlinks into it. Edit here, never edit the symlink targets' copies elsewhere.
- **Standing defaults (Josh's explicit preference): model `v3`, style `professional`.** `resolve_style()` in `rephrasy_humanize.py` implements this — professional is applied only for v3, never sent to other models. Don't change defaults without asking.
- Detector score direction is 0 = human, 100 = AI in **both** modes — verified live 2026-06-07 against known-human/known-AI samples. The public docs claim non-depth modes are inverted; they are wrong. Don't "fix" the scripts to match the docs.
- Calibration data in the SKILL.md files (70.28 for formal human prose, 7.35 casual human, 99.87/92.60 single-pass humanize comparison) came from live calls on 2026-06-07. If Rephrasy retrains, re-run the calibration before editing those tables.
- Output naming uses the `_rephrasy` suffix deliberately — the local StealthHumanizer project already owns `_humanized`, and the two must not clobber each other.
- **Exit-code contract**: both scripts exit 2 on any error (via the `die()` helper); detect exits 1 only for `--threshold` exceeded. Iterate loops depend on this to avoid burning paid passes during API outages — don't collapse errors back to exit 1.
- Network handlers must catch `OSError` after `HTTPError`/`URLError`: response-phase timeouts raise raw `TimeoutError` (not wrapped in `URLError`), and that's the likeliest real-world failure for the humanizer, which works server-side before responding.
- Every API call costs credits. When testing changes, use short texts and prefer the free validation paths (arg errors, `--help`) where possible.

## Testing changes

```bash
# Free (no API call): validation/error paths
python3 scripts/rephrasy_humanize.py --text "hi" --style creative --no-style  # expect error
python3 scripts/rephrasy_detect.py --text "   "                              # expect error

# Paid (tiny): end-to-end
python3 scripts/rephrasy_detect.py --text "some sample text to score"
python3 scripts/rephrasy_humanize.py --text "some sample text to rewrite"
```
