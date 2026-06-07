#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE_SOURCE="${REPHRASY_SKILLS_MARKETPLACE_SOURCE:-jhubbardsf/rephrasy-skills}"
MARKETPLACE_NAME="${REPHRASY_SKILLS_MARKETPLACE_NAME:-rephrasy-skills}"
PLUGIN_SPEC="${REPHRASY_SKILLS_PLUGIN_SPEC:-rephrasy@$MARKETPLACE_NAME}"
SCOPE="${REPHRASY_SKILLS_INSTALL_SCOPE:-user}"

usage() {
  cat <<'USAGE'
Usage:
  install.sh [--scope user|project|local]

Environment overrides:
  REPHRASY_SKILLS_MARKETPLACE_SOURCE  Marketplace source. Default: jhubbardsf/rephrasy-skills
  REPHRASY_SKILLS_MARKETPLACE_NAME    Marketplace name. Default: rephrasy-skills
  REPHRASY_SKILLS_PLUGIN_SPEC         Plugin spec. Default: rephrasy@rephrasy-skills
  REPHRASY_SKILLS_INSTALL_SCOPE       Install scope. Default: user
USAGE
}

while (($#)); do
  case "$1" in
    --scope)
      (($# >= 2)) || {
        echo "error: --scope requires user, project, or local" >&2
        exit 2
      }
      SCOPE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SCOPE" in
  user|project|local) ;;
  *)
    echo "error: invalid scope: $SCOPE" >&2
    exit 2
    ;;
esac

if ! command -v claude >/dev/null 2>&1; then
  echo "error: Claude Code CLI not found. Install Claude Code first." >&2
  exit 127
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "warning: python3 not found. The bundled helper scripts require Python 3." >&2
fi

if [[ -z "${REPHRASY_API_KEY:-}" ]]; then
  echo "warning: REPHRASY_API_KEY is not set. Get a key at https://www.rephrasy.ai and export it before use." >&2
fi

echo "Adding Claude plugin marketplace: $MARKETPLACE_SOURCE"
claude plugin marketplace add "$MARKETPLACE_SOURCE" --scope "$SCOPE"

echo "Installing plugin: $PLUGIN_SPEC"
claude plugin install "$PLUGIN_SPEC" --scope "$SCOPE"

cat <<EOF

Installed.

Open Claude Code, run /reload-plugins, then use:
  /rephrasy:ai-detect <file-or-text>
  /rephrasy:humanize <file-or-text>

EOF
