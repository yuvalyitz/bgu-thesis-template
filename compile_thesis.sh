#!/usr/bin/env bash
# Build the full thesis: English part (pdfLaTeX) + Hebrew pages (XeLaTeX),
# merged into build/thesis.pdf. See README.md.
#
# Usage:
#   ./compile_thesis.sh          # incremental build
#   ./compile_thesis.sh clean    # delete build/
set -euo pipefail
cd "$(dirname "$0")"

BUILD=build
ENGLISH_SRC="main.tex"
HEBREW_SRC="hebrew_pages.tex"
HEBREW_JOB="hebrew_pages"   # jobname, so the PDF is build/hebrew_pages.pdf
OUT="$BUILD/thesis.pdf"

if [[ "${1:-}" == "clean" ]]; then
    rm -rf "$BUILD"
    echo "removed $BUILD/"
    exit 0
fi

# The Hebrew pages load "Linux Libertine O", "David CLM" and "Latin Modern Roman"
# by name. They ship with TeX Live, but XeTeX on macOS only finds fonts by name
# if the OS knows them, so copy them into ~/Library/Fonts (one-time step;
# macOS does not register symlinked fonts).
if [[ "${1:-}" == "install-fonts" ]]; then
    FONT_DIR="$HOME/Library/Fonts"
    mkdir -p "$FONT_DIR"
    for probe in LinLibertine_R.otf DavidCLM-Medium.otf lmroman10-regular.otf; do
        src=$(kpsewhich "$probe") || { echo "error: $probe not in TeX Live (install libertine / culmus / lm)" >&2; exit 1; }
        case "$probe" in
            LinLibertine*) pattern="LinLibertine_*.otf" ;;
            DavidCLM*)     pattern="DavidCLM-*.otf" ;;
            lmroman*)      pattern="lmroman*.otf" ;;
        esac
        for f in "$(dirname "$src")"/$pattern; do
            cp -f "$f" "$FONT_DIR/$(basename "$f")"
        done
    done
    echo "fonts copied into $FONT_DIR (delete the LinLibertine_*, DavidCLM-*, lmroman* files to undo)"
    exit 0
fi

for tool in latexmk pdflatex xelatex biber python3; do
    command -v "$tool" >/dev/null || { echo "error: '$tool' not found in PATH" >&2; exit 1; }
done
python3 -c "import pikepdf" 2>/dev/null \
    || { echo "error: python module 'pikepdf' missing (pip install pikepdf)" >&2; exit 1; }

# \include{Main_pages/...} writes its .aux into the same subfolder of the output dir
mkdir -p "$BUILD/Main_pages"

# Cross-document references need a second English build after Hebrew headings
# move. Repeat complete pairs until both auxiliary files stop changing.
previous_refs=""
settled=false
for pass in 1 2 3 4 5; do
    echo "==> [1/3] English part (reference pass $pass): $ENGLISH_SRC"
    # -g on later passes: the cross-document .aux files are not tracked as
    # dependencies by latexmk, so force the run instead of trusting it.
    latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
        $( [[ $pass -gt 1 ]] && echo -g ) -outdir="$BUILD" "$ENGLISH_SRC"

    echo "==> [2/3] Hebrew pages (reference pass $pass): $HEBREW_SRC"
    latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error \
        $( [[ $pass -gt 1 ]] && echo -g ) -outdir="$BUILD" -jobname="$HEBREW_JOB" "$HEBREW_SRC"

    current_refs=$(shasum "$BUILD/main.aux" "$BUILD/$HEBREW_JOB.aux")
    if [[ "$current_refs" == "$previous_refs" ]]; then
        settled=true
        break
    fi
    previous_refs="$current_refs"
done
if [[ "$settled" != true ]]; then
    echo "error: English/Hebrew references did not settle after five passes" >&2
    exit 1
fi

echo "==> [3/3] Merging into $OUT"
python3 merge_thesis.py "$BUILD/main.pdf" "$BUILD/$HEBREW_JOB.pdf" "$OUT"

echo "done: $OUT"
