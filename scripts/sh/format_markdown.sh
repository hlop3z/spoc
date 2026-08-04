#!/usr/bin/env sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

cd "$REPO_ROOT"

find . \
  \( -path './node_modules' \
     -o -path './.git' \
     -o -path './dist' \
     -o -path './.docusaurus' \) -prune \
  -o \( -name '*.md' -o -name '*.mdx' \) -exec \
    npx --yes prettier --write --prose-wrap preserve {} +