#!/usr/bin/env bash
# Strip Cursor co-author / Made-with trailers from all commits in current repo.
set -euo pipefail
FILTER='sed -e "/^Co-authored-by: Cursor <cursoragent@cursor.com>$/d" \
  -e "/^Co-authored-by: Cursor$/d" \
  -e "/^Made-with: Cursor$/d"'
before=$(git log --all --format=%B | grep -cE "Co-authored-by: Cursor|Made-with: Cursor" || true)
if [ "$before" -eq 0 ]; then
  echo "Already clean (no Cursor attribution in history)."
  exit 0
fi
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter "$FILTER" -- --all
git for-each-ref --format='%(refname)' refs/original/ 2>/dev/null | while read -r ref; do
  git update-ref -d "$ref" 2>/dev/null || true
done
git reflog expire --expire=now --all
git gc --prune=now --quiet
after=$(git log --all --format=%B | grep -cE "Co-authored-by: Cursor|Made-with: Cursor" || true)
echo "Stripped $before -> $after Cursor attribution lines."
