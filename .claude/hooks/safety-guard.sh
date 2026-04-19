#!/bin/bash
# PreToolUse(Bash) — refuse dangerous commands before they run.
# Reads tool input as JSON on stdin. Exit 1 blocks the tool call.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Patterns to block
BLOCKED_PATTERNS=(
  'rm -rf /'
  'rm -rf ~'
  'rm -rf \*'
  'git push.*--force.*main'
  'git push.*--force.*master'
  'git push.*-f.*main'
  'git reset --hard'
  'git checkout -- \.'
  'git clean -f'
  'chmod -R 777'
  'curl .* \| sudo bash'
  'curl .* \| sudo sh'
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qE "$pattern"; then
    echo "BLOCKED by safety-guard.sh: matched pattern \"$pattern\"" >&2
    echo "Command was: $CMD" >&2
    exit 1
  fi
done

exit 0
