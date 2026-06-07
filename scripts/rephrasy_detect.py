#!/usr/bin/env python3
"""Check text for AI detectability via the Rephrasy Detector API.

Stdlib only -- no pip installs required. The API key is read from the
REPHRASY_API_KEY environment variable, falling back to parsing
~/.config/zsh/secrets.zsh.

Usage:
  rephrasy_detect.py FILE                 # score a file (depth mode)
  rephrasy_detect.py --text "some text"   # score a literal string
  cat file.txt | rephrasy_detect.py -     # score stdin
  rephrasy_detect.py FILE --json          # raw API response
  rephrasy_detect.py FILE --threshold 40  # exit 1 if overall score > 40

Exit codes: 0 = success (and under threshold, if given);
            1 = score exceeded --threshold;
            2 = error (bad input, missing key, API/network failure).

Score direction (verified empirically 2026-06-07): 0 = human, 100 = AI,
in BOTH default and depth modes. The public docs claim non-depth modes
are inverted; live testing shows they are not.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = "https://detector.rephrasy.ai/detect_api"
SECRETS_FILE = os.path.expanduser("~/.config/zsh/secrets.zsh")
TIMEOUT_SECONDS = 120


def die(message):
    """Errors exit 2 so shell loops can tell them apart from exit-1 threshold failures."""
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


def call_api(text, mode, api_key):
    payload = json.dumps({"text": text, "mode": mode}).encode("utf-8")
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
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            die("error: 401 Unauthorized -- check REPHRASY_API_KEY.")
        die(f"error: HTTP {exc.code} from detector API: {detail}")
    except urllib.error.URLError as exc:
        die(f"error: cannot reach detector API: {exc.reason}")
    except OSError as exc:
        # Response-phase timeouts/resets raise raw OSError subclasses
        # (TimeoutError, ConnectionResetError) that URLError does not wrap.
        die(f"error: network failure talking to detector API: {exc}")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        die(f"error: non-JSON response from detector API: {body[:300]}")


def verdict(score):
    # Bands calibrated against live results on 2026-06-07. The detector
    # runs hot on formal prose: a verified-human formal writing sample
    # scored 70.28, while casual human text scored 7.35.
    if score < 20:
        return "reads human"
    if score < 45:
        return "mostly human / mixed signals"
    if score < 70:
        return "suspect -- formal human prose often lands here"
    if score < 90:
        return "likely AI (or very formal human writing)"
    return "flagged as AI"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", help="file to score, or '-' for stdin")
    parser.add_argument("--text", help="literal text to score instead of a file")
    parser.add_argument(
        "--mode",
        default="depth",
        choices=["depth", "default"],
        help="'depth' (default) gives finer per-sentence scores",
    )
    parser.add_argument("--json", action="store_true", help="print raw API JSON")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="N",
        help="exit 1 if overall score > N (errors exit 2, so loops can "
        "distinguish a failing score from a failing API)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="K",
        help="show the K most AI-flagged sentences (default 5, 0 to hide)",
    )
    args = parser.parse_args()

    text = read_text(args)
    if not text.strip():
        die("error: input text is empty.")

    mode = "" if args.mode == "default" else args.mode
    data = call_api(text, mode, resolve_api_key())

    overall = data.get("scores", {}).get("overall")
    if overall is None:
        die(f"error: unexpected API response: {json.dumps(data)[:500]}")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        words = len(text.split())
        sentences = data.get("sentences", {})
        print(f"Overall AI score: {overall:.2f} / 100  (0 = human, 100 = AI)")
        print(f"Verdict: {verdict(overall)}")
        print(f"Words: {words} | Sentences scored: {len(sentences)}")
        if sentences and args.top > 0:
            ranked = sorted(sentences.items(), key=lambda kv: kv[1], reverse=True)
            print(f"\nMost AI-flagged sentences (top {min(args.top, len(ranked))}):")
            for sent, score in ranked[: args.top]:
                snippet = sent if len(sent) <= 100 else sent[:97] + "..."
                print(f"  {score:6.2f}  {snippet}")

    if args.threshold is not None and overall > args.threshold:
        sys.exit(1)


if __name__ == "__main__":
    main()
