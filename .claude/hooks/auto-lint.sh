#!/bin/bash
# PostToolUse(Edit|Write) — lint the file Claude just touched.
# Exit 1 reports a syntax error back to Claude so it can self-correct.

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
  *.py)
    python3 -m py_compile "$FILE" 2>&1 || {
      echo "SYNTAX ERROR in $FILE — please fix."
      exit 1
    }
    ;;
  *.json)
    jq empty "$FILE" 2>&1 || {
      echo "JSON PARSE ERROR in $FILE — please fix."
      exit 1
    }
    ;;
  *.sh)
    bash -n "$FILE" 2>&1 || {
      echo "SHELL SYNTAX ERROR in $FILE — please fix."
      exit 1
    }
    ;;
esac

exit 0
