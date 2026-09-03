#!/usr/bin/env sh
# Build tests/fixtures/paper.pdf from paper.tex with pdflatex.
#
# Needs a TeX distribution (TeX Live / MiKTeX) with amsmath, booktabs and
# geometry - all in the base install. Run twice so \ref and \eqref resolve.
# Then: python tests/regress.py --update paper  (and review the output).
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT

cp "$here/paper.tex" "$build/"
cd "$build"
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >/dev/null
mkdir -p "$here/../fixtures"
cp paper.pdf "$here/../fixtures/paper.pdf"
echo "wrote tests/fixtures/paper.pdf"
