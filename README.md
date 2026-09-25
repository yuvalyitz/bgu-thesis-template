# BGU Thesis Template (English thesis + Hebrew pages, one linked PDF)

A LaTeX template for a PhD or MSc thesis at Ben-Gurion University of the Negev.
The thesis body is in English; the Hebrew summary (תקציר), Hebrew abstract
(תמצית) and Hebrew cover page that the university requires at the *end* of the
bound volume are produced by a second, XeLaTeX document. A build script compiles
both and merges them into one PDF in which

- the English table of contents lists the Hebrew pages with the right page numbers,
- the Hebrew table of contents shows the English chapter and section numbers and
  page numbers, read automatically from the English build, and every line of it
  is a clickable link into the English part,
- the Hebrew text can link to any English theorem, figure, definition or
  bibliography entry and quote its number automatically,
- page numbering runs continuously through both parts,
- all of this survives any PDF viewer, including Apple Preview re-saves.

The template is filled with a small dummy thesis by *Israel Israeli*, supervised
by *Prof. Max Musterman*, that exercises every mechanism once. Build it, open
`build/thesis.pdf`, click around, then replace the content with yours.

## Files

| File | What it is |
|---|---|
| `thesis_info.tex` | **Title, author, supervisor, department, degree, date** in English and Hebrew. Edit this first; both documents read it. |
| `main.tex` | The English document (pdfLaTeX + biber): preamble, front matter, chapter list, bibliography. |
| `content/*.tex` | One file per chapter. The dummy chapters double as examples of every construct. |
| `Main_pages/` | Cover page, signature (title) page, abstract, acknowledgements, affidavit, BGU logo. |
| `hebrew_pages.tex` | The Hebrew document (XeLaTeX + biber): Hebrew TOC, summary, abstract, Hebrew cover. |
| `bibliography/references.bib` | The bibliography, shared by both documents. |
| `compile_thesis.sh` | Builds everything into `build/thesis.pdf`. |
| `merge_thesis.py` | Concatenates the two PDFs and rewires the cross-document links. |

## Building

Requirements: TeX Live (or MacTeX) with `latexmk`, `pdflatex`, `xelatex` and
`biber`; Python 3 with `pikepdf` (`pip install pikepdf`); and the fonts used by
the Hebrew pages, *Linux Libertine O*, *David CLM* and *Latin Modern Roman*,
visible to the operating system.

```bash
./compile_thesis.sh            # -> build/thesis.pdf
./compile_thesis.sh clean      # delete build/
```

The script runs three steps, all inside `build/` (git-ignored):

1. `latexmk -pdf main.tex` → `build/main.pdf`
2. `latexmk -xelatex hebrew_pages.tex` → `build/hebrew_pages.pdf`
3. `merge_thesis.py` → `build/thesis.pdf`

Steps 1 and 2 are repeated until the auxiliary files of both documents stop
changing (each document reads labels from the other, see below), then the
merge runs. `latexmk` handles biber and the usual LaTeX reruns. A clean build
takes a few minutes; later builds only redo what changed. The merge step prints
how many links it resolved and **warns about link names it could not resolve**;
a clean thesis prints no warning.

### Fonts on macOS (one time)

All three fonts ship with TeX Live (packages `libertine`, `culmus`, `lm`), but
XeTeX on macOS only finds fonts by name if macOS knows them, otherwise the build
stops with `The font "Linux Libertine O" cannot be found`. Run once:

```bash
./compile_thesis.sh install-fonts
```

This copies the `.otf` files into `~/Library/Fonts` (symlinks are not enough).
To undo, delete the `LinLibertine_*.otf`, `DavidCLM-*.otf` and `lmroman*.otf`
files there. On Linux (fontconfig) and on Overleaf this step is not needed.

### Overleaf

Overleaf cannot run the merge script. Compile `main.tex` (pdfLaTeX) and
`hebrew_pages.tex` (XeLaTeX) as two projects, or keep one project and switch the
main file, then merge locally with `python3 merge_thesis.py english.pdf hebrew.pdf out.pdf`.

## Quick start

1. Edit `thesis_info.tex`.
2. Write your chapters in `content/` and list them in `main.tex` (copy the
   four-line chapter block, see below).
3. Write the Hebrew summary and abstract in `hebrew_pages.tex`, and update its
   table of contents to mirror your chapters.
4. `./compile_thesis.sh`, and check that the merge step prints no warning.

## How the two documents are connected

Four mechanisms, each relying on a naming convention. Keep the conventions and
everything stays linked; the dummy chapters show each one.

### 1. Continuous page numbers

`main.tex` loads `lastpage`, which defines the label `LastPage`.
`hebrew_pages.tex` reads it through `xr-hyper` (prefix `en-`) and starts at the
next page:

```latex
\setcounter{page}{\numexpr\getpagerefnumber{en-LastPage}+1\relax}
```

### 2. The English TOC lists the Hebrew pages

The Hebrew pages are appended *after* the English document, so `main.tex`
writes their TOC lines by hand, taking the page numbers from labels defined in
`hebrew_pages.tex` (prefix `he-`) and linking to anchors defined there:

```latex
% main.tex, after \printbibliography
\addtocontents{toc}{\protect\contentsline{chapter}{Hebrew Summary}{\getpagerefnumber{he-toc:hebrew:summary}}{chapter:hebrew:summary}}

% hebrew_pages.tex, at the summary heading
\hypertarget{chapter:hebrew:summary}{}\label{toc:hebrew:summary}%
```

This is why the build script alternates between the two documents until their
`.aux` files settle: English needs the Hebrew page numbers and Hebrew needs the
English ones. On a clean build the first English pass prints `0` for these pages;
the second pass fixes it. The script passes `-g` to latexmk on later passes because
latexmk does not track the other document's `.aux` file as a dependency.

### 3. The Hebrew TOC shows English numbers and pages

Every English heading the Hebrew TOC mentions carries an **anchor** (for the
click) and a **label** (for the number and page). `main.tex` defines a helper
for sections:

```latex
\linkedsection{motivation}{Motivation}
% expands to
\section[Motivation]{\hypertarget{target:sec:motivation}{}Motivation}\label{toc:sec:motivation}
```

The anchor is placed *inside* the heading on purpose: an anchor written on the
line before `\section` ends up at the bottom of the previous page whenever the
section starts a new page. Chapters use the explicit four-line block in
`main.tex`:

```latex
\cleardoublepage
\phantomsection
\hypertarget{chapter:intro}{}%
\chapter{Introduction}
\label{chapter:intro}
```

The Hebrew TOC line then reads (macros defined in `hebrew_pages.tex`):

```latex
\englishTOCnumber{chapter:intro}.\ \hyperlink{chapter:intro}{מבוא}\dotfill \englishTOCpage{chapter:intro}\\
\hspace{2em}\englishTOCnumber{toc:sec:motivation}\ \hyperlink{target:sec:motivation}{מוטיבציה}\dotfill \englishTOCpage{toc:sec:motivation}\\
```

`\englishTOCnumber` and `\englishTOCpage` are `\ref*`/`\pageref*` on the
`en-` labels, printed left-to-right and deliberately *without* their own link:
the surrounding `\hyperlink` is the link, and the merge script needs exactly one
destination per link. Unnumbered chapters (Conclusion, Bibliography) have no
number and use a label placed at their heading (`toc:bibliography` is set with
`\AtNextBibliography`).

### 4. Links from Hebrew text into the English part

Any English object can be linked to by giving it a named anchor:

```latex
\begin{restatable}{theorem}{MainTheorem}
\label{thm:main}\hypertarget{target:thm:main}{}%
...
\end{restatable}

\begin{figure}[htb]
\hypertarget{target:fig:example}{}%
...
```

and, in the Hebrew text, `\enref{thm:main}{thm:main}`, which is
`\hyperlink{target:thm:main}{\englishTOCnumber{thm:main}}`: a click that lands on
the theorem and prints its number, so renumbering never breaks the Hebrew text.

Citations need nothing special. Both documents load the same `.bib` with the same
`biblatex` options (alphabetic labels are derived from author and year, so
`[Kar72]` is the same label in both), and after the merge the Hebrew `\hcite{...}`
links resolve to the entries in the English bibliography. `main.tex` additionally
gives every entry an anchor named by its bib key (`\AtEveryBibitem`), so
`\hyperlink{Karp72}{...}` works too.

**Inside the standalone Hebrew PDF these links are dangling**, because their
destinations live in the other file. `merge_thesis.py` appends the Hebrew pages
to the English PDF, collects the named destinations of both, and rewrites every
named link into an explicit page-and-position destination. That last step is what
makes the links survive viewers that drop the name tree (Apple Preview does when
it re-saves). If a Hebrew link uses a name that neither document defines, the
script prints a warning listing the names; add the missing `\hypertarget` in the
English source, or, as a last resort, alias the name to one of hyperref's
automatic anchors in the `ALIASES` table at the top of the script.

### Naming summary

| Object | Anchor (`\hypertarget`, for `\hyperlink`) | Label (for `\ref*`/`\pageref*` via `en-`) |
|---|---|---|
| Chapter | `chapter:<key>` | `chapter:<key>` |
| Section | `target:sec:<key>` | `toc:sec:<key>` (both set by `\linkedsection`) |
| Theorem, figure, definition | `target:thm:<key>`, `target:fig:<key>`, `target:def:<key>` | your usual `thm:<key>`, `fig:<key>`, ... |
| Bibliography | `chapter:bib` | `toc:bibliography` |
| Hebrew summary / abstract | `chapter:hebrew:summary`, `chapter:hebrew:abstract` | `toc:hebrew:summary`, `toc:hebrew:abstract` (read by English as `he-...`) |

## Writing the Hebrew pages

`hebrew_pages.tex` sets Hebrew as the default language (polyglossia), so plain
paragraphs are right-to-left. Two helpers keep Latin fragments readable:

- `\en{NP}` typesets a Latin word or phrase left-to-right in a Latin font.
- `\hcite{key1,key2}` is `\cite` wrapped the same way.

Inline math (`$f(k)\cdot n^{O(1)}$`) works as is. The Hebrew cover page at the
end of the file takes its fields from `thesis_info.tex`; if you have two
supervisors, add the second name there and in the three cover pages.

## Layout notes

- Page numbers are centred at the top and there are no running headers, as the
  BGU guidelines ask (`fancyhdr` block in `main.tex`).
- `geometry` is loaded with `twoside` (mirrored margins for binding), which makes
  every chapter start on an odd page, with a blank page inserted where needed.
  For a screen-only PDF add `openany` to the `\documentclass` options.
- Theorems, lemmas and corollaries share one counter per chapter (`Theorem 2.1`,
  `Lemma 2.2`). State a main result in the introduction with `restatable` and
  restate it in its chapter with `\MainTheorem*` (see `content/results.tex`); the
  number is kept.
- `\Cref` (cleveref) is used for all internal references in the English part.

## Troubleshooting

- **`The font "Linux Libertine O" cannot be found`**: run `./compile_thesis.sh install-fonts` (macOS).
- **`Hebrew Summary ... 0` in the English TOC**: the English part was not rebuilt after the Hebrew part. Run the script again; do not run `latexmk` on `main.tex` by hand between passes.
- **Merge warning `links point to names that exist in neither PDF`**: a Hebrew `\hyperlink{name}` has no matching `\hypertarget{name}{}` in the English source. Add one (or an alias, see above).
- **`Missing \begin{document}` in `build/main.aux`, or other nonsense errors after a build was interrupted**: two builds ran at once or one was killed mid-write and the `.aux` file is truncated. Run `./compile_thesis.sh clean` and build again.
- **Package bidi Error: you have loaded package xcolor after bidi**: any package that loads `xcolor` (tikz, xcolor itself) must be loaded before `bidi`/`polyglossia` in `hebrew_pages.tex`; the template loads `xcolor` first.

## Checklist before submission

- `thesis_info.tex` filled in; the two English cover pages and the Hebrew cover agree.
- Affidavit included if your department requires it (`\include{Main_pages/affidavit}` in `main.tex`).
- Merge step prints no warning; every Hebrew TOC line shows a number and a page.
- English TOC shows real page numbers for *Hebrew Summary* and *Hebrew Abstract*.
- Open `build/thesis.pdf` in Preview or Acrobat and click a few Hebrew links.
