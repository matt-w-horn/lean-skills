---
name: lean-latex-sync
description: Keep LaTeX, README, and docstring prose truthful to the Lean code it describes. Use whenever writing or rewriting a paper, abstract, manuscript, README, or docstring that touches a formalization — "rewrite this section", "rewrite the abstract", "tighten this paragraph", "make this readable", "update the paper", "does the paper still match the code?", "resync the docs after this rename" — and whenever a Lean change lands that a document elsewhere describes. Use it especially when the request is to change only the wording and not the mathematics, since that is exactly where claims silently drift. This skill owns docstring-versus-statement auditing: checking that docstrings claim no more than their theorems prove belongs here, not in lean-verification. Also use for LaTeX tooling around Lean: syntax highlighting with listings or minted, Unicode math that will not compile, and `\lean{}`-style citation macros.
---

# Keeping prose true to the Lean

A sentence about a theorem is a claim about what the kernel checked. The
kernel does not read prose, so nothing catches an English sentence that says
more, less, or other than the statement supports. In a formalization project
this is the largest class of undetected defect, and it is introduced most often
during edits that felt purely editorial.

Two directions of work land here, and they have different risks:

- **Prose-only rewrite.** Nothing about the Lean changes. The risk is that
  rephrasing silently strengthens a claim — "when" becomes "exactly when", a
  bound becomes "the" bound, a sufficient condition reads as necessary.
- **Resync after a Lean change.** The statement moved and the document has to
  follow. The risk is missing a surface: a renamed declaration cited in three
  files gets fixed in one.

## Read before you write

Open the Lean. Every time. A claim about a declaration you have not read this
session is a guess, however confident it feels, and confident guesses about
formal statements are exactly the defect this work exists to prevent.

Also read the project's own rules first — `CLAUDE.md` at the repo root and in
the docs directory. Projects commonly freeze the manuscript outside deliberate
sync passes, fix an audience for a companion document, or forbid renaming
declarations an external document cites. None of that is visible in the LaTeX.

A few surfaces make claims about the whole development rather than about one
declaration, so no search over changed names leads to them. Read these in full
at the start of every pass, before editing anything:

- **The abstract.** It restates the entire contribution in a paragraph, so a
  change anywhere in the development can falsify it, and nothing in the diff
  points here.
- **The limitations, omissions, or future-work section.** It claims what the
  development does *not* do. Every addition is a candidate falsification.
- **The claim-to-declaration index**, where the document keeps one: a table or
  appendix mapping results to names. Deletions and renames break individual
  rows that read fine in isolation.
- **Any plain-language companion, in full.** It is usually short, and it
  usually cites no declaration names at all, which puts it beyond every
  mechanical check in this skill. It goes stale precisely because nothing
  points at it.

Everything else you reach from the change set.

## Edit by hand

Use the editing tool, one edit at a time. Do not reach for `sed -i`, `perl
-pi`, `awk -i`, or a script that rewrites the file. Naming the tools is
deliberate: "be careful with bulk edits" loses to a substitution command that
is always to hand and always reports success, so the rule has to be about which
tool you pick rather than about how carefully you use it.

A scripted substitution changes text you never read. A bare numeral replaced
everywhere hits the same digits inside a page reference, a citation key, a
version string, or a sentence where the old value was right. The one number you
meant to fix is indistinguishable to `sed` from the four you did not.

Read whole files rather than jumping to search hits. Grep finds lines, and the
defects here live in paragraphs: a sentence that has quietly stopped being true
contains no string you could have searched for, which is why the surfaces
listed above are read end to end.

The shell is for finding things and for building the document. Deciding whether
a sentence is still true needs a reader, and that is the whole job. When
checking your own work afterwards, read the final file rather than the diff: a
substitution that damaged a neighbouring line leaves the line you were looking
at perfectly correct.

## Quote both sides — including when you find nothing

A finding carries the prose line and the Lean statement, pasted in. So does a
clean result. "Checked, in sync" with nothing quoted is an assertion, not
evidence, and it is the shape of report that has been wrong before: mechanical
name-matching passes happily while the prose around the name has drifted.

Mathlib itself supplies the canonical illustration, in a declaration that has
been read by thousands of people:

<example>
**Claim** (docstring, `Mathlib/Topology/Order/Compact.lean:245`): "The
**extreme value theorem**: a continuous function realizes its maximum on a
compact set."

**Statement** (same file, line 246):
```lean
theorem IsCompact.exists_isMaxOn [ClosedIciTopology α] {s : Set β}
    (hs : IsCompact s) (ne_s : s.Nonempty) {f : β → α}
    (hf : ContinuousOn f s) : ∃ x ∈ s, IsMaxOn f s x
```

**Verdict**: the prose omits `ne_s : s.Nonempty`. The empty set is compact and
every function is continuous on it, but no `x ∈ ∅` exists — so the theorem as
stated in prose is false, while the theorem as formalized is true.

This is a mild and well-understood case: "realizes its maximum" arguably
presupposes there is something to maximize over. It illustrates the general
shape anyway — the hypothesis that rules out the degenerate case is exactly
the one prose drops, because it is the one that feels like bookkeeping.
</example>

## The rewrite protocol

For each paragraph you touch:

1. **Extract the claims.** One sentence can carry several. A claim is anything
   a reader could check against a statement.
2. **Locate each declaration.** Grep the library for the name; read the full
   statement including every hypothesis and binder.
3. **Compare on five axes** — the recurring drift classes:
   - *Quantifier*: does the prose universalize what the statement bounds?
   - *Hypothesis*: does the prose mention every side condition that matters?
   - *Direction*: `→` versus `↔`; necessary versus sufficient; the `.mp` versus
     the `.mpr`.
   - *Strength*: "the bound" versus "a bound"; "exactly" versus "at most".
   - *Existence*: does the cited name still exist, spelled that way?
4. **Write the verdict** before editing: supported, overclaim, underclaim, or
   stale reference.
5. **Edit the prose to match the statement** — or, when it is the statement
   that is wrong, stop and report it. Prose is cheap to change and statements
   are not; a project with a review process wants the statement change queued,
   not made in passing.

`references/claim-checking.md` has the full drift catalogue with worked
examples of each class.

## Rewriting or reorganizing a whole section

The protocol above compares paragraph against paragraph, which stops working
the moment paragraphs merge, split, or move. A rewrite needs an invariant that
survives reorganization, and there are two: the set of declarations the section
cites, and the set of claims it makes. Capture both from the original before
touching it.

The citation set is mechanical; the normalizer below produces it. The claim
inventory is not: one line per checkable assertion, each naming the declaration
that supports it or marked as carrying no formal support. Build it by reading
the original text, never from memory of what the section was about.

Rewrite freely. Then rebuild both from the new text and diff them against the
originals. Four buckets, each owed a verdict:

- **Citations dropped.** A result the section used to point at is now
  unmentioned. Deliberate, or lost in the rewrite? Only a human knows.
- **Citations added.** Check each against its statement. A name pulled in
  during a rewrite has been verified by nobody.
- **Claims dropped.** The same question, with no mechanical trace to find them
  by. This is what the inventory is for.
- **Claims added.** The dangerous bucket. Fluent prose invents connective
  tissue that reads as consequence: "and therefore the bound is tight", "which
  guarantees recovery". Every added claim needs a declaration behind it, or it
  is an overclaim the original never made.

Reorganization carries two hazards beyond rewriting. Anaphora break silently:
"in this regime", "the bound above", "as shown" each resolved against a
neighbour that has now moved, and the sentence still reads fine while pointing
at the wrong thing. Resolve every one by hand. Second, when docstrings cite
section numbers keyed to a map, reordering sections invalidates that map; the
citations still parse, now naming the wrong section, and no build catches it.

Calibrate the inventory before trusting it. Build it from the original and
check that it caught claims you already know are there. An extractor that
mis-parses known-good prose mis-parses the rewrite identically and then agrees
with itself, which is how a bulk rewrite passes every mechanical check while
carrying real defects.

## After a Lean change, resync every surface

Start from the change set, not from a name you happen to remember. If the
project keeps a statement lock or freeze file, its diff is the authoritative
list of what moved; otherwise diff the Lean sources between the last synced
commit and now. When the change set is a *stream* of commits — the repo
moved many times while the document stood still —
`references/commit-stream-sync.md` comes first: the frontier to sync from,
why the net diff and never a per-commit replay, and how the work differs by
commit kind. Sort the result into three kinds, because they need different
work and only the first is greppable:

- **Deleted or renamed.** Citations of the old name now dangle. Grep finds
  every one, and this is the case the commands below serve.
- **Restated.** The name survives, the type moved. Grep still finds the
  citations, but the name is not the finding: re-read each claim against the
  new statement, because the sentence parses and names something real while
  saying something false.
- **Added.** Grep finds nothing, and this is the category that gets missed. A
  new result falsifies prose that scopes what the development does *not* do:
  an omissions list, a "we prove only the weaker form" concession, a
  limitations paragraph, an abstract hedging what the artifact covers. Read
  every such passage after any addition, whether or not it names a
  declaration.

Then read the prose paragraph by paragraph rather than searching it. A
paragraph whose subject moved is stale even when every name in it still
resolves, and the sentences that go wrong most carry no declaration name at
all: they describe an approach, a limitation, or a decision not to prove
something. Nothing in `references/sync-checks.md` can see those, which is why
those checks verify what the reading already did and never replace it.

Enumerate the surfaces before fixing any of them, because fixing one and
declaring victory is the common failure:

```sh
# every mention of the old name, anywhere prose lives
grep -rn "old_declaration_name" --include="*.tex" --include="*.md" \
  --include="*.lean" --include="*.bib" .
```

Names inside LaTeX are escaped, so a raw grep misses them. Normalize first:

```sh
# \lean{Foo\_bar} and \lean{Foo\allowbreak\_bar} both mean Foo_bar
grep -o '\\lean{[^}]*}' docs/paper/*.tex \
  | sed 's/\\allowbreak//g; s/\\_/_/g; s/\\lean{//; s/}$//' | sort -u
```

That normalization is not optional bookkeeping — it is the difference between a
check that inspects something and one that reports success having matched
nothing.

## Prose conventions for statement-bearing text

These differ from ordinary style advice, and deliberately:

- **One term per concept, repeated.** Lexical variety is a defect here. A
  reader tracking a formal argument should not have to derive that two words
  denote the same object.
- **Present tense, active voice.** "The theorem bounds" rather than "a bound is
  obtained".
- **Keep em-dashes out of lines carrying symbols.** They break the parse when
  the line is already dense with notation.
- **State the referent.** "The dashboard speaks three units" gestures at a
  meaning it never gives. If a reader cannot name what a phrase refers to,
  either name it or cut it.
- **Every number is unchecked text.** Recompute each one, or promote it to a
  Lean `example` so the kernel carries it. Find them by sweeping every numeral
  in the prose, not by looking where you expect numbers to be: a document
  usually states several that drift independently, and the one nobody thought
  to name is the one that rots. `references/sync-checks.md` has the sweep and
  the table to record each number's source in. A matrix witness that was wrong
  sat in both a docstring and a paper through several reviews, because nothing
  mechanical could catch it.

## References

| File | Read it when |
|---|---|
| `references/claim-checking.md` | Auditing prose against statements; you need the drift catalogue |
| `references/sync-checks.md` | Scripting the mechanical checks — name resolution, counts, orphan references |
| `references/commit-stream-sync.md` | Catching prose up to many Lean commits at once — frontiers, net diffs, commit taxonomy, multi-agent findings |
| `references/latex-tooling.md` | Setting up Lean syntax highlighting, Unicode symbols, or building the document |

Sibling skills: **`lean-proving`** when the Lean itself needs to change, and
**`lean-verification`** for auditing whether a proof establishes what is
claimed — this skill assumes the Lean is right and asks whether the prose
matches it.
