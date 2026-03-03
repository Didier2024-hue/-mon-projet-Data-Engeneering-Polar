#!/usr/bin/env bash
set -e

cd /home/datascientest/cde/polar || exit 1

if [[ -n $(git status --porcelain) ]]; then
    git add -u
    git commit -m "${1:-update}"
    git push origin dev
    echo "✅ Pushed sur dev"
else
    echo "ℹ️ Rien à commit"
fi