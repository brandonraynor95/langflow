#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
EXAMPLES_DIR="$SCRIPT_DIR"
TEST_SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

MODE="syntax"
EXECUTION_TIER="readonly"

print_help() {
  cat <<'EOF'
Usage:
  test-curl-examples.sh [--execute] [--tier readonly|mutating|destructive|all]

Modes:
  (default)            Syntax check only (bash -n)
  --execute            Execute examples after syntax checks

Execution tiers (used only with --execute):
  readonly             Run only read-only examples (GET/HEAD/OPTIONS)
  mutating             Run read-only + mutating examples (POST/PUT/PATCH)
  destructive          Run everything, including DELETE examples
  all                  Alias of destructive

Optional per-file override:
  Add this comment to a .sh example:
    # @safety=readonly|mutating|destructive
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      MODE="execute"
      shift
      ;;
    --tier)
      if [[ -z "${2:-}" ]]; then
        echo "Missing value for --tier"
        exit 1
      fi
      EXECUTION_TIER="$2"
      shift 2
      ;;
    --help|-h)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      print_help
      exit 1
      ;;
  esac
done

if [[ "$EXECUTION_TIER" == "all" ]]; then
  EXECUTION_TIER="destructive"
fi
if [[ "$EXECUTION_TIER" != "readonly" && "$EXECUTION_TIER" != "mutating" && "$EXECUTION_TIER" != "destructive" ]]; then
  echo "Invalid --tier '$EXECUTION_TIER' (expected readonly|mutating|destructive|all)"
  exit 1
fi

if [[ ! -d "$EXAMPLES_DIR" ]]; then
  echo "Examples directory not found: $EXAMPLES_DIR"
  exit 1
fi

SH_FILES=()
while IFS= read -r line; do
  if [[ "$line" == "$SCRIPT_DIR/$TEST_SCRIPT_NAME" ]]; then
    continue
  fi
  SH_FILES+=("$line")
done < <(python3 - "$EXAMPLES_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
for p in sorted(root.rglob("*.sh")):
    print(p)
PY
)

if [[ ${#SH_FILES[@]} -eq 0 ]]; then
  echo "No .sh examples found in $EXAMPLES_DIR"
  exit 1
fi

PASS=0
FAIL=0
SKIP=0

echo "Testing ${#SH_FILES[@]} curl shell examples in '$MODE' mode..."
if [[ "$MODE" == "execute" ]]; then
  echo "Execution tier: $EXECUTION_TIER"
fi

safety_level_for_file() {
  python3 - "$1" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

override = re.search(r'^\s*#\s*@safety=(readonly|mutating|destructive)\s*$', text, re.M)
if override:
    print(override.group(1))
    sys.exit(0)

method_match = re.search(r'--request\s+([A-Za-z]+)|-X\s+([A-Za-z]+)', text)
method = (method_match.group(1) or method_match.group(2)).upper() if method_match else "GET"

if method in {"GET", "HEAD", "OPTIONS"}:
    print("readonly")
elif method == "DELETE":
    print("destructive")
else:
    print("mutating")
PY
}

should_run_for_tier() {
  local file_tier="$1"
  local requested_tier="$2"
  case "$requested_tier" in
    readonly) [[ "$file_tier" == "readonly" ]] ;;
    mutating) [[ "$file_tier" == "readonly" || "$file_tier" == "mutating" ]] ;;
    destructive) [[ "$file_tier" == "readonly" || "$file_tier" == "mutating" || "$file_tier" == "destructive" ]] ;;
    *) return 1 ;;
  esac
}

for file in "${SH_FILES[@]}"; do
  rel="${file#"$ROOT_DIR"/}"
  safety_tier="$(safety_level_for_file "$file")"

  if ! bash -n "$file"; then
    echo "FAIL  $rel (bash -n)"
    ((FAIL+=1))
    continue
  fi

  if [[ "$MODE" == "execute" ]]; then
    if [[ -z "${LANGFLOW_API_KEY:-}" || ( -z "${LANGFLOW_URL:-}" && -z "${LANGFLOW_SERVER_URL:-}" ) ]]; then
      echo "SKIP  $rel (set LANGFLOW_API_KEY and LANGFLOW_URL or LANGFLOW_SERVER_URL to execute)"
      ((SKIP+=1))
      continue
    fi

    if ! should_run_for_tier "$safety_tier" "$EXECUTION_TIER"; then
      echo "SKIP  $rel (tier=$safety_tier, requested=$EXECUTION_TIER)"
      ((SKIP+=1))
      continue
    fi

    if ! bash "$file" >/tmp/langflow-curl-example.out 2>/tmp/langflow-curl-example.err; then
      echo "FAIL  $rel (execution, tier=$safety_tier)"
      ((FAIL+=1))
      continue
    fi
  fi

  echo "PASS  $rel (tier=$safety_tier)"
  ((PASS+=1))
done

echo
echo "Summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP TOTAL=${#SH_FILES[@]}"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
