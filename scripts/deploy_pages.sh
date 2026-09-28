#!/usr/bin/env bash
# Publish the website to GitHub Pages: copies site/ (with its generated, gitignored data/) into a fresh
# single-commit gh-pages branch and force-pushes it to origin. app.js and style.css get ?v=<commit> so
# browsers refetch them after each deploy. Run `s1000 site --profile 1000x1000` first if the data changed.
set -euo pipefail
root=$(git rev-parse --show-toplevel); cd "$root"
[ -f site/data/index.json ] || { echo "site/data is missing: run 's1000 site --profile 1000x1000' first" >&2; exit 1; }
if [ -n "$(git status --porcelain -- site src docs | grep -v '^??' || true)" ]; then
  echo "uncommitted changes under site/, src/ or docs/: commit them first" >&2; exit 1
fi
rev=$(git rev-parse --short HEAD); remote=$(git remote get-url origin)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
rsync -a --exclude '.DS_Store' site/ "$tmp/"
perl -pi -e "s/(style\.css|app\.js)\"/\$1?v=$rev\"/g" "$tmp/index.html"
touch "$tmp/.nojekyll"
cd "$tmp"
git init -q -b gh-pages
git add -A
git commit -qm "Site build from $rev"
git push -qf "$remote" gh-pages
echo "deployed $rev ($(du -sh . | cut -f1)) to gh-pages"
