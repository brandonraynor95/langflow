#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
EXAMPLES_DIR="$SCRIPT_DIR"
TEST_SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

MODE="syntax"

load_repo_env() {
  local env_file="$ROOT_DIR/.env"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$env_file"
    set +a
  fi
}

print_help() {
  cat <<'EOF'
Usage:
  test-python-examples.sh [--execute]

Modes:
  (default)            Syntax check only (py_compile)
  --execute            Execute examples after syntax checks

EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      MODE="execute"
      shift
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
  load_repo_env
fi

has_placeholder_file_inputs() {
  python3 - "$1" <<'PY'
import sys
text = open(sys.argv[1], encoding="utf-8").read()
needles = ("FILE_NAME", "PATH/TO/FILE", "<file contents>")
print("yes" if any(n in text for n in needles) else "no")
PY
}

has_missing_required_env() {
  python3 - "$1" <<'PY'
import os
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
vars_to_check = ["FLOW_ID", "PROJECT_ID", "FOLDER_ID", "SESSION_ID", "JOB_ID", "USER_ID"]

for name in vars_to_check:
    if re.search(rf"os\.getenv\(\s*['\"]{name}['\"]", text) and not os.getenv(name):
        print(name)
        raise SystemExit(0)

print("")
PY
}

for file in "${PY_FILES[@]}"; do
  rel="${file#"$ROOT_DIR"/}"

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

    if [[ "$(has_placeholder_file_inputs "$file")" == "yes" ]]; then
      echo "SKIP  $rel (placeholder file input values)"
      ((SKIP+=1))
      continue
    fi

    missing_env="$(has_missing_required_env "$file")"
    if [[ -n "$missing_env" ]]; then
      echo "SKIP  $rel (missing required env: $missing_env)"
      ((SKIP+=1))
      continue
    fi

    if ! python3 "$file" >/tmp/langflow-python-example.out 2>/tmp/langflow-python-example.err; then
      echo "FAIL  $rel (execution)"
      ((FAIL+=1))
      continue
    fi
  fi

  echo "PASS  $rel"
  ((PASS+=1))
done

echo
echo "Summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP TOTAL=${#PY_FILES[@]}"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
