# Mechanical sync checks

The checks below are scriptable, so they should be scripted — a human reading
476 citations will miss some, and will miss them inconsistently. What they
cannot do is judge meaning, which is why they run *before* the semantic pass
rather than instead of it.

## First: a check that inspects nothing still passes

The failure mode that makes these checks worse than useless is a check that
scans the wrong surface, finds nothing, and reports success. Four real
instances of that shape:

- A count-sync check scanned only the README and CLAUDE.md, which state no
  count, and reported "no stated count sites found" while four real sites sat
  in the LaTeX.
- A proof-token scanner treated `--` inside a string literal as a comment
  opener and discarded the rest of the line, hiding everything after it.
- A statement-freeze digest hashed declaration *header* lines while a
  definition *body* changed underneath it.
- A declaration-matching regex matched four docstring prose lines as
  declarations.

**When adding or changing a check, demonstrate it failing on a constructed bad
input and passing on the real tree.** Assertion is not evidence. Print the
number of sites inspected, so "0 problems" is distinguishable from "0 looked
at".

## Normalizing LaTeX names

Names inside LaTeX carry escapes, and line-breaking macros can appear inside
them. Normalize before matching or the check inspects nothing:

```sh
# \lean{Foo\_bar} and \lean{Foo\allowbreak\_bar} both denote Foo_bar
extract_lean_names() {
  grep -oh '\\lean{[^}]*}' "$@" \
    | sed 's/\\allowbreak//g; s/\\_/_/g; s/^\\lean{//; s/}$//' \
    | sort -u
}
extract_lean_names docs/paper/*.tex
```

Apply the same normalization to `\texttt{}`, `\mathtt{}`, or whatever macro the
document actually uses — read the preamble rather than assuming:

```sh
grep -n "newcommand" docs/paper/main.tex
```

## Check 1: every cited name resolves

```sh
# Names the document cites
extract_lean_names docs/paper/*.tex > /tmp/cited.txt

# Names the library declares
grep -rhoE '^\s*(theorem|lemma|def|abbrev|structure|class|instance|inductive|opaque)\s+[A-Za-z_][A-Za-z0-9_.'"'"']*' \
  YourLib/ | awk '{print $2}' | sort -u > /tmp/declared.txt

comm -23 /tmp/cited.txt /tmp/declared.txt
```

Two refinements that matter:

- **Namespaces.** A declaration inside `namespace Foo` is `Foo.bar`, but the
  source line says `theorem bar`. Either track the enclosing namespace when
  extracting, or match on the last component — and if you match on the last
  component, know that you have just made namespace moves invisible, and grep
  those by hand after any namespace change.
- **Module names.** Documents cite modules as well as declarations; allow both.

## Check 2: stated counts match the real count

Counts drift whenever anything is added, which makes this the single most
recurrent inconsistency in a formalization document.

Do not pattern-match the phrasings you expect. A check keyed to predicted
wording once matched zero of five real sites in a live paper: one said
`statements` where the pattern said `declarations`, one put the number after
the noun instead of before it, one had its qualifier on the previous line so a
line-based grep could never see the pair, and one was capitalized where the
pattern was not. Every site was plainly visible to a reader.

The reading pass is what updates these numbers. A paragraph stating a count is
a paragraph you are already reading against the code, so the count gets fixed
there. Run the sweep afterwards to prove you left no site behind; it is a
completeness check on the reading, not a way to find the sites in the first
place. Reaching for it first turns the job into skimming a few hundred
numerals, which is how the stale one survives.

```sh
# The authoritative count, wherever the build prints one
grep -oE '[0-9]+ declarations' "$BUILD_LOG" | head -1

# Every prose line carrying a numeral, to diff against what you just edited
grep -rnE '[0-9]' --include="*.tex" --include="*.md" docs/ README.md \
  | grep -vE '\\(cite|ref|label|includegraphics)\{|^[^:]*:[0-9]+:\s*%'
```

A document states more than one drifting number, and they move independently.
The declaration count changes when a result is added or deleted; the source-line
count changes whenever any line is written, including a proof golfed shorter.
Two of them sharing a single sentence is common, and fixing one while leaving
the other beside it is the usual way this defect survives review.

Record each recurring number once, with the command that regenerates it:

| Number | Appears in | Regenerate with |
|---|---|---|
| declarations audited | abstract, introduction, validation section | the count the build prints |
| lines of source | introduction, companion document | `git ls-files '<lib>/**/*.lean' \| xargs wc -l` |

A number with no named source cannot be rechecked, only re-guessed. Decide what
the denominator includes (library only, or library plus test tooling) and write
it down, because two readings that differ by hundreds of lines are both
defensible until someone states which one the paper means.

Enumerate the sites the check inspected in its output. A count check that finds
no sites has told you nothing, and should say so loudly rather than exiting 0.

## Check 3: cross-reference keys resolve

When docstrings cite sections (`§3`, `\ref{sec:foo}`) keyed to a map that lives
in one canonical place, every citation should resolve there.

```sh
# sections cited in Lean docstrings
grep -rhoE '§[0-9]+(\.[0-9]+)*' YourLib/ | sort -u > /tmp/cited-secs.txt
# sections the canonical map defines
grep -oE '§[0-9]+(\.[0-9]+)*' README.md | sort -u > /tmp/map-secs.txt
comm -23 /tmp/cited-secs.txt /tmp/map-secs.txt
```

## Check 4: no declaration is cited nowhere

The inverse direction — declarations no prose surface mentions. Useful for
finding dead code, with one caveat that must be stated wherever the output is
read: **textual matching misses dot-notation consumption**, so `hs.exists_isMaxOn`
does not register as a mention of `IsCompact.exists_isMaxOn`. Treat the output
as candidates for a human to look at, never as a deletion list.

Every surface that carries citations counts as a billing surface. Miss one and
live declarations look dead.

## Check 5: `sorry` and placeholders

```sh
grep -rn "\\\\sorry\|\\\\lean{sorry}\|TODO\|TBD\|XXX" --include="*.tex" .
grep -rn "\bsorry\b" --include="*.lean" YourLib/ | grep -v -E ':[0-9]+:[[:space:]]*--'
```

The filter drops whole-line comments only. A `sorry` beside a trailing
comment (`exact sorry -- FIXME`) still surfaces; a `sorry` mentioned inside
a trailing comment false-positives, which errs in the right direction.

A document citing `\lean{sorry}` deliberately (to discuss it) is fine; one
citing it accidentally is claiming a proof exists that does not.

## Check 6: statement freeze, for noticing unintended changes

The strong form freezes **elaborated** statements: a small executable loads
the library's environment and writes every declaration's pretty-printed type
(plus the body, for definition kinds) to a tracked lock file, and the check
fails on removals, changes, and additions alike. Working code and the full
rationale live in `lean-refactoring/references/statement-freeze.md`; if the
project can build itself, use that form.

The weak form — when the toolchain is out of reach — hashes source text.
What to hash differs by declaration kind, because "the statement" lives in a
different place:

- `theorem` / `lemma` — the header up to `:=`. Proof refactors then do not fire.
- `def` / `abbrev` / `structure` / `class` / `instance` / `inductive` /
  `opaque` — the header **and the body**, because for these the body *is* the
  statement. A header-only digest once reported no drift while a definition's
  body gained a conjunct that changed the meaning of every consumer.

Key each entry by its fully qualified name, so a namespace move registers.
Strip comments and docstrings before hashing, so prose edits are not reported
as drift.

Three holes of the weak form, worth stating wherever its output is read —
the elaborated lock closes all three: `variable` binders (changing one
alters what many theorems mean with no drift reported), truncation of long
headers, and additions (a digest that only diffs known keys never reports a
new declaration).

## Running order

1. Build the Lean. A document synced against code that does not compile is
   synced against nothing.
2. Run the mechanical checks; fix what they find.
3. Only then do the semantic pass from `claim-checking.md`, scoped to the
   declarations that changed since the last verified state.

Mechanical green is a precondition for the semantic pass, not a substitute. The
build verifies proofs, not meaning: a statement can be wrong while every check
above is green.

## If the project already has a verify script

Use it rather than reimplementing. Look for `.claude/verify/`, `scripts/`,
`Makefile` targets, or a repo-local skill; a project that has invested in these
checks has usually also encoded which surfaces count, and that list is hard-won.
