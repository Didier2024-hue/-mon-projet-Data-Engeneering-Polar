#!/bin/bash

cd /home/datascientest/cde/polar

git add .
git commit -m "${1:-update}"
git push origin dev

echo "✅ Pushed sur dev"