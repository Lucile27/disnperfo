#!/bin/bash
# Session health check — runs on every SessionStart.
# Prints a short status line. Fast (<2s). Never blocks.

set -e
echo "---"

# Git status (is the repo clean?)
if git rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git branch --show-current 2>/dev/null)
  dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "Git: branch=$branch dirty=$dirty files"
fi

# Disk
disk=$(df -h / 2>/dev/null | awk 'NR==2 {print $5}')
[[ -n "$disk" ]] && echo "Disk: $disk used"

# Project-specific checks — ADD YOURS HERE
# Examples:
# systemctl is-active dagster-daemon 2>/dev/null && echo "Dagster: active"
# pg_isready -h localhost 2>/dev/null && echo "Postgres: up"

echo "Session OK"
