# LaTeX tooling for Lean

Two problems recur when a document contains Lean: syntax highlighting the code,
and getting Unicode mathematical symbols to compile at all. Lean source is
dense with characters (`ℝ`, `≤`, `∀`, `⟨⟩`, `↔`, `𝓝`) that a default pdfLaTeX
setup cannot typeset.

## Choosing between `listings` and `minted`

| | `listings` | `minted` |
|---|---|---|
| Setup | Copy one file, no external tools | Needs Python + Pygments ≥ 2.18 |
| Unicode | Restricted; needs per-character declarations | Unrestricted with XeLaTeX or LuaLaTeX |
| Compilation | Plain `pdflatex` | Requires `--shell-escape` |
| Best for | Short snippets, conventional symbols | Heavy Unicode, long listings |

Pick `listings` when the Lean you are showing is light on exotic notation and
you want the build to stay dependency-free. Pick `minted` when the code is
full of mathematical Unicode, which in Mathlib-based projects it usually is.

## `listings`

Download `lstlean.tex` from the Lean 4 repository, which defines the Lean
language for the `listings` package — keywords, tactics, comments, symbols,
sorts, and attributes, each with its own colour.

```latex
\usepackage[utf8]{inputenc}   % [utf8x] on older LaTeX installations
\usepackage{listings}
\usepackage{color}
\input{lstlean.tex}
\lstset{language=lean}
```

Then compile with `pdflatex test.tex`. With `\lstset{language=lean}` in the
preamble, `\begin{lstlisting}` blocks and `\lstinputlisting{File.lean}` both
pick up Lean highlighting without further annotation.

The restriction to know about: `listings` and LaTeX handle Unicode by
declaration, so a symbol nobody declared comes out wrong or breaks the build.
See the fallback section below.

## `minted`

`minted` wraps Pygments, which already knows Lean 4 and handles Unicode
without per-character work.

```latex
\usepackage{minted}
\usepackage{fontspec}
\setmonofont{FreeMono}    % a monospace font with wide mathematical coverage
```

```sh
pip install 'Pygments>=2.18'
xelatex --shell-escape test.tex     # or lualatex --shell-escape
```

Three requirements, all of which produce confusing failures when missed:

- **Pygments 2.18 or newer** — older versions predate the current Lean 4 lexer.
- **XeLaTeX or LuaLaTeX** — pdfLaTeX cannot do the Unicode part, which is the
  reason to use `minted` at all.
- **`--shell-escape`** — `minted` shells out to `pygmentize`. Without the flag
  the build fails with a permission-flavoured error that does not mention
  Pygments. Some CI images and Overleaf configurations disable shell escape;
  check before committing to `minted`.

## Missing Unicode symbols

When a character typesets as a blank, a box, or a build error, map it
explicitly with `newunicodechar` — either to a font that has it, or to a LaTeX
construction:

```latex
\usepackage{newunicodechar}

% route one character through a font that covers it
\newunicodechar{𝓝}{{\fontspec{DejaVu Sans}𝓝}}

% or substitute a LaTeX equivalent
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{∀}{\ensuremath{\forall}}
\newunicodechar{⟨}{\ensuremath{\langle}}
\newunicodechar{⟩}{\ensuremath{\rangle}}
```

Work from the actual failures rather than pre-declaring a large table: compile,
collect the characters that broke, and map those. Fonts with good coverage for
Lean source: FreeMono, DejaVu Sans Mono, JuliaMono, STIX Two Math.

## Citing declarations by name

Documents that reference Lean declarations usually define a macro so the
citations are greppable and restylable in one place:

```latex
\newcommand{\lean}[1]{\texttt{#1}}
```

Two consequences for anything that checks these citations:

- Underscores are escaped (`\lean{Nat.sub\_add\_cancel}`), and line-breaking
  macros can appear *inside* a name
  (`\lean{IsCompact.exists\allowbreak\_isMaxOn}`). Normalize both before
  matching — `sync-checks.md` has the sed pipeline.
- Read the preamble to learn the real macro name before scripting anything
  against it. Not every project calls it `\lean`.

## Building

```sh
tectonic docs/paper/main.tex          # self-contained; fetches its TeX bundle
latexmk -xelatex -shell-escape main.tex   # traditional, handles reruns
```

`tectonic` downloads its bundle over the network on first run, so a sandboxed
build fails until that cache exists. That failure looks like a LaTeX error and
is not one.

For `minted`, `latexmk` needs `-shell-escape` passed through, and the cached
`_minted-*` directory should be gitignored along with the usual `.aux`,
`.log`, `.out`, `.bbl`, `.blg`.

## Keeping code listings honest

A Lean snippet pasted into a document is a copy, and copies drift. Two ways to
keep them true:

- `\lstinputlisting[firstline=42, lastline=58]{../../YourLib/File.lean}` pulls
  from the source, so the document cannot show code the library does not have.
  Line numbers drift, so anchor on stable boundaries where possible.
- If snippets must be pasted, treat them as claims: they belong in the same
  audit as prose, and the check is that the pasted text still appears verbatim
  in the source.

```sh
# crude but effective: does each displayed declaration still exist as shown?
grep -oE 'theorem [a-zA-Z_][a-zA-Z0-9_.]*' docs/paper/main.tex | sort -u
```
