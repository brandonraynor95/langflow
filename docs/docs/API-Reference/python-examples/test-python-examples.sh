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
  test-python-examples.sh [--execute] [--tier readonly|mutating|destructive|all]

Modes:
  (default)            Syntax check only (py_compile)
  --execute            Execute examples after syntax checks

Execution tiers (used only with --execute):
  readonly             Run only read-only examples
  mutating             Run read-only + mutating examples
  destructive          Run everything including deletes
  all                  Alias of destructive

Optional per-file override:
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

PY_FILES=()
while IFS= read -r line; do
  if [[ "$(basename "$line")" == "$TEST_SCRIPT_NAME" ]]; then
    continue
  fi
  PY_FILES+=("$line")
done < <(python3 - "$EXAMPLES_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
for p in sorted(root.rglob("*.py")):
    print(p)
PY
)

if [[ ${#PY_FILES[@]} -eq 0 ]]; then
  echo "No .py examples found in $EXAMPLES_DIR"
  exit 1
fi

PASS=0
FAIL=0
SKIP=0

echo "Testing ${#PY_FILES[@]} Python examples in '$MODE' mode..."
if [[ "$MODE" == "execute" ]]; then
  echo "Execution tier: $EXECUTION_TIER"
fi

safety_level_for_file() {
  python3 - "$1" <<'PY'
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
override = re.search(r'^\s*#\s*@safety=(readonly|mutating|destructive)\s*$', text, re.M)
if override:
    print(override.group(1))
    raise SystemExit(0)

method = "GET"
m = re.search(r'requests\.request\(\s*["\']([A-Za-z]+)["\']', text)
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

for file in "${PY_FILES[@]}"; do
  rel="${file#"$ROOT_DIR"/}"
  safety_tier="$(safety_level_for_file "$file")"

  if ! python3 -m py_compile "$file"; then
    echo "FAIL  $rel (py_compile)"
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

    if ! python3 "$file" >/tmp/langflow-python-example.out 2>/tmp/langflow-python-example.err; then
      echo "FAIL  $rel (execution, tier=$safety_tier)"
      ((FAIL+=1))
      continue
    fi
  fi

  echo "PASS  $rel (tier=$safety_tier)"
  ((PASS+=1))
done

echo
echo "Summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP TOTAL=${#PY_FILES[@]}"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
