#!/usr/bin/env bash
set -euo pipefail

msg="${1:-}"
pathspec="${2:-.}"

if [[ -z "$msg" ]]; then
	echo "Usage: $0 \"commit message\" [pathspec]"
	exit 2
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "[error] not inside a git repository"
	exit 2
fi

# Configure remote without embedding credentials in the URL.
git_user="${GIT_USER:-Garcia-INPE}"
git_prj="${GIT_PRJ:-DB-Search}"
origin_url="https://github.com/${git_user}/${git_prj}.git"

if git remote get-url origin >/dev/null 2>&1; then
	git remote set-url origin "$origin_url"
else
	git remote add origin "$origin_url"
fi

git add "$pathspec"

if git diff --cached --quiet; then
	echo "[info] nothing to commit"
	exit 0
fi

git commit -m "$msg"

branch="$(git rev-parse --abbrev-ref HEAD)"
git push -u origin "$branch"

echo "[done] pushed ${branch} to origin"
