#!/usr/bin/env python3
"""Humanize AI-generated text via the Rephrasy Humanizer API.

Stdlib only -- no pip installs required. The API key is read from the
REPHRASY_API_KEY environment variable, falling back to parsing
~/.config/zsh/secrets.zsh.

Defaults: model "v3" with style "professional". Override with --model /
--style, or pass --no-style for v3's built-in default behavior.

Usage:
  rephrasy_humanize.py FILE                      # writes FILE_rephrasy.ext next to input
  rephrasy_humanize.py FILE -o out.txt           # explicit output path
  rephrasy_humanize.py FILE --in-place           # overwrite the input file (atomic)
  rephrasy_humanize.py --text "some text"        # humanize a literal string -> stdout
  rephrasy_humanize.py --text "some text" -o out.txt  # ... or to a file
  cat file.txt | rephrasy_humanize.py -          # stdin -> stdout
  rephrasy_humanize.py FILE --style creative     # override the default style

Exit codes: 0 = success; 2 = error (bad input/flags, missing key,
API/network failure).

Costs: word-based pricing is enabled by default. The actual charge is
reported to stderr after every call (including --json runs).

Response notes (verified empirically 2026-06-07): `costs` comes back as a
plain number (e.g. 0.000666), not the `{"total": ...}` object shown in the
marketing docs. `new_flesch_score` can be negative for dense prose.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request

API_URL = "https://v2-humanizer.rephrasy.ai/api/"
SECRETS_FILE = os.path.expanduser("~/.config/zsh/secrets.zsh")
TIMEOUT_SECONDS = 300
VALID_STYLES = ("creative", "journalistic", "professional")


def die(message):
    """Errors exit 2, matching rephrasy_detect.py's exit-code contract."""
    print(message, file=sys.stderr)
    sys.exit(2)


def resolve_api_key():
    key = os.environ.get("REPHRASY_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(SECRETS_FILE, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"""\s*(?:export\s+)?REPHRASY_API_KEY=["']?([^"'\s;]+)""", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    die(
        "error: REPHRASY_API_KEY not set and not found in "
        f"{SECRETS_FILE}. Export it or add it to the secrets file."
    )


def read_text(args):
    if args.text is not None and args.input is not None:
        die("error: provide either FILE or --text, not both.")
    if args.text is not None:
        return args.text
    if args.input is None:
        die("error: provide FILE, '-' for stdin, or --text. See --help.")
    if args.input == "-":
        return sys.stdin.read()
    try:
        with open(args.input, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        die(f"error: {args.input} is not valid UTF-8 text.")
    except OSError as exc:
        die(f"error: cannot read {args.input}: {exc}")


def default_output_path(input_path):
    root, ext = os.path.splitext(input_path)
    return f"{root}_rephrasy{ext}"


def resolve_style(args):
    """Default to 'professional' on v3; never send style to non-v3 models."""
    if args.no_style and args.style:
        die("error: --style and --no-style are mutually exclusive.")
    if args.no_style:
        return None
    if args.style:
        if args.model != "v3":
            die("error: --style is only supported by the v3 model.")
        return args.style
    return "professional" if args.model == "v3" else None


def resolve_output_path(args):
    """Where the humanized text should be written; None means stdout.

    Precedence: --in-place > -o/--output > default _rephrasy path for file
    input > stdout. --stdout forces stdout (text printing) for file input.
    """
    file_input = args.input not in (None, "-") and args.text is None
    if args.in_place and not file_input:
        die("error: --in-place requires a real input file.")
    if args.in_place and args.output:
        die("error: --in-place and -o/--output are mutually exclusive.")
    if args.stdout and (args.in_place or args.output):
        die("error: --stdout conflicts with --in-place and -o/--output.")
    if args.in_place:
        return args.input
    if args.output:
        return args.output
    if file_input and not args.stdout:
        return default_output_path(args.input)
    return None


def write_atomic(path, content):
    """Write via a same-directory temp file + os.replace so a failed write
    never truncates an existing file (matters for --in-place)."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".rephrasy-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            if not content.endswith("\n"):
                fh.write("\n")
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        die(f"error: cannot write {path}: {exc}")


def call_api(args, text, api_key, style):
    body = {
        "text": text,
        "model": args.model,
        "words": not args.no_words,
        "costs": True,
    }
    if style:
        body["style"] = style
    if args.language:
        body["language"] = args.language
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            die("error: 401 Unauthorized -- check REPHRASY_API_KEY.")
        if exc.code == 422:
            die(f"error: 422 invalid input: {detail}")
        die(f"error: HTTP {exc.code} from humanizer API: {detail}")
    except urllib.error.URLError as exc:
        die(f"error: cannot reach humanizer API: {exc.reason}")
    except OSError as exc:
        # Response-phase timeouts/resets raise raw OSError subclasses
        # (TimeoutError, ConnectionResetError) that URLError does not wrap.
        # Likely here: the humanizer works server-side before responding.
        die(f"error: network failure talking to humanizer API: {exc}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        die(f"error: non-JSON response from humanizer API: {raw[:300]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", help="file to humanize, or '-' for stdin")
    parser.add_argument("--text", help="literal text to humanize instead of a file")
    parser.add_argument("-o", "--output", help="output file path")
    parser.add_argument(
        "--in-place", action="store_true", help="overwrite the input file"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print humanized text to stdout instead of writing a file",
    )
    parser.add_argument(
        "--model",
        default="v3",
        help="'v3' (default), 'Undetectable Model v2', 'Undetectable Model', "
        "'SEO Model', or a saved Writing Style ID",
    )
    parser.add_argument(
        "--style",
        choices=VALID_STYLES,
        help="v3-only style (default: professional). "
        "Use --no-style for v3's built-in default behavior.",
    )
    parser.add_argument(
        "--no-style",
        action="store_true",
        help="do not send a style parameter (v3 default behavior)",
    )
    parser.add_argument(
        "--language", help="language name (e.g. 'English'); auto-detected if omitted"
    )
    parser.add_argument(
        "--no-words",
        action="store_true",
        help="disable word-based pricing (words: false)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print raw API JSON to stdout (file output, if any, still written)",
    )
    args = parser.parse_args()

    style = resolve_style(args)
    out_path = resolve_output_path(args)

    text = read_text(args)
    if not text.strip():
        die("error: input text is empty.")

    data = call_api(args, text, resolve_api_key(), style)
    output = data.get("output")
    if not output:
        die(f"error: unexpected API response: {json.dumps(data)[:500]}")

    if out_path:
        write_atomic(out_path, output)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        if out_path:
            print(f"Wrote: {out_path}", file=sys.stderr)
    elif out_path:
        print(f"Wrote: {out_path}")
    else:
        print(output)

    # Report metadata to stderr so stdout stays pipeable. Always printed,
    # including --json runs -- this is a paid API and costs must surface.
    flesch = data.get("new_flesch_score")
    costs = data.get("costs")
    meta = []
    if flesch is not None:
        meta.append(f"flesch={flesch:.1f}")
    if costs is not None:
        meta.append(f"cost={costs} credits")
    meta.append(f"words_in={len(text.split())}")
    meta.append(f"words_out={len(output.split())}")
    print(f"[rephrasy] {' | '.join(meta)}", file=sys.stderr)


if __name__ == "__main__":
    main()
