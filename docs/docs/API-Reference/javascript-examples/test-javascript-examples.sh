#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
EXAMPLES_DIR="$SCRIPT_DIR"
TEST_SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

MODE="syntax"
EXECUTION_TIER="readonly"

print_help() {
  cat <<'EOF'
Usage:
  test-javascript-examples.sh [--execute] [--tier readonly|mutating|destructive|all]

Modes:
  (default)            Syntax check only (`node --check`)
  --execute            Execute examples after syntax checks

Execution tiers (used only with --execute):
  readonly             Run only read-only examples
  mutating             Run read-only + mutating examples
  destructive          Run everything including deletes
  all                  Alias of destructive

Optional per-file override:
  // @safety=readonly|mutating|destructive
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

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required to test JavaScript examples."
  exit 1
fi

JS_FILES=()
while IFS= read -r line; do
  if [[ "$(basename "$line")" == "$TEST_SCRIPT_NAME" ]]; then
    continue
  fi
  JS_FILES+=("$line")
done < <(python3 - "$EXAMPLES_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
for p in sorted(root.rglob("*.js")):
    print(p)
PY
)

if [[ ${#JS_FILES[@]} -eq 0 ]]; then
  echo "No .js examples found in $EXAMPLES_DIR"
  exit 1
fi

PASS=0
FAIL=0
SKIP=0

echo "Testing ${#JS_FILES[@]} JavaScript examples in '$MODE' mode..."
if [[ "$MODE" == "execute" ]]; then
  echo "Execution tier: $EXECUTION_TIER"
fi

safety_level_for_file() {
  python3 - "$1" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
override = re.search(r'^\s*//\s*@safety=(readonly|mutating|destructive)\s*$', text, re.M)
if override:
    print(override.group(1))
    raise SystemExit(0)

method = "GET"
m = re.search(r"method:\s*['\"]([A-Za-z]+)['\"]", text)
if m:
    method = m.group(1).upper()

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

has_placeholder_file_inputs() {
  python3 - "$1" <<'PY'
import sys
text = open(sys.argv[1], encoding="utf-8").read()
needles = ("FILE_NAME", "PATH/TO/FILE", "<file contents>")
print("yes" if any(n in text for n in needles) else "no")
PY
}

for file in "${JS_FILES[@]}"; do
  rel="${file#"$ROOT_DIR"/}"
  safety_tier="$(safety_level_for_file "$file")"

  if ! node --check "$file" >/tmp/langflow-js-check.out 2>/tmp/langflow-js-check.err; then
    echo "FAIL  $rel (node --check)"
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

    if [[ "$(has_placeholder_file_inputs "$file")" == "yes" ]]; then
      echo "SKIP  $rel (placeholder file input values)"
      ((SKIP+=1))
      continue
    fi

    if ! node "$file" >/tmp/langflow-js-example.out 2>/tmp/langflow-js-example.err; then
      echo "FAIL  $rel (execution, tier=$safety_tier)"
      ((FAIL+=1))
      continue
    fi
  fi

  echo "PASS  $rel (tier=$safety_tier)"
  ((PASS+=1))
done

echo
echo "Summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP TOTAL=${#JS_FILES[@]}"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
