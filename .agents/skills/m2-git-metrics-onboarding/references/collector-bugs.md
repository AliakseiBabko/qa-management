# Collector Defects That Change What The Numbers Mean

Scope: three verified defects in the collector, what each one does to a
person's figures, and the concrete per-repository checks to run during
workflow step 5 before a key is handed over. Load this module on every
issue pass and whenever asked whether a collector-derived anomaly is
trustworthy.

All three were verified by direct inspection of the collector source and
by running the equivalent git queries against real repositories. They are
not hypotheses. Each one has a per-person mitigation that is cheap to run
once, at onboarding, and expensive to discover later - after a wrong
number has already reached a report or a review.

## Defect 1 - Trunk Detection Falls Back To Your Checkout

**What the code does.** The collector's trunk-detection helper looks for a
branch literally named `main`, then one named `master`. If neither exists,
it falls back to **whatever branch is currently checked out** and grades
against that.

**Why it bites.** A repository whose trunk is `develop` (or `trunk`, or a
release branch) is never detected, so the graded branch becomes whichever
feature branch the person happened to leave checked out when the collector
ran. What that distorts is review hygiene, churn, PR counts and cycle
times - everything derived from the trunk's first-parent history.

It does **not** change who appears in the payload: contributor discovery
is a separate `git log --all` pass over every ref, so the contributor set
is the same on any branch. Do not reach for a branch change as a way to
control whose data is sent (see `precondition-gate.md`'s caution) - the
only lever there is repository scope.
Verified in practice: a repository with neither `main` nor `master` had a
long-lived feature branch checked out, and the collector would have graded
the whole window against it. Two runs a week apart, on different
branches, produce different numbers for the same period with no
indication that anything changed. There is no configuration option to
name the trunk.

**Check, per repository in scope.** Establish the real trunk and whether
the collector can see it:

```bash
git -C <repo> branch --format='%(refname:short)' | grep -Ex 'main|master' || echo 'NO TRUNK DETECTED'
git -C <repo> symbolic-ref --short refs/remotes/origin/HEAD   # the actual default branch
git -C <repo> rev-parse --abbrev-ref HEAD                     # what would be graded on fallback
```

**Record** in the registry row: `Trunk branch` (per repo, e.g.
`<repo-a>: develop; <repo-b>: main`) and `Trunk auto-detected`
(`Y` / `N (graded on checkout)`).

**Mitigation, in order of preference.**

1. If the trunk is `main`/`master`, nothing to do - this repo is fine.
2. If not: exclude the repository from the collector's scope. Partial,
   honest coverage beats checkout-dependent numbers.
3. If it cannot be excluded (it is the project's only repository), the
   person must check the trunk out and leave it checked out before every
   run, the row's `Metrics validity` becomes `Branch-dependent`, and the
   handoff says so explicitly. Do not skip the registry note on the
   grounds that the person "knows to switch branches" - the point of the
   note is that whoever later reads the report does not.
4. Ask the app owner for a configurable trunk-branch setting. This is the
   real fix and worth raising once, on behalf of everyone being onboarded,
   rather than per person.

## Defect 2 - "Direct To Main" Misfires On Squash-Merge Repositories

**What the code does.** A commit is counted as reviewed only if it is
reached through a merge commit, or if its subject line literally contains
a merge/PR reference of the form `!123`, `(pull request #N)`, or `(#N)`.
Everything else counts as a direct push. A separate squash-workflow
detector exists to compensate - but it flips a repository to "all
reviewed" **only when the last 200 first-parent commits on the graded
branch contain zero review markers**, regardless of date.

**Why it bites.** That leaves a wide and very common middle case: a
repository that squash-merges everything (so almost no commit carries a
merge commit or a PR reference) but happens to contain *a few* review
markers anywhere in that 200-commit slice - a period of normal merges
before the team switched strategy, a couple of manual merges, a revert, an
initial import. The detector does not flip, and every bare commit in the
metrics window gets labelled a direct push. The person's direct-to-main percentage goes near-total, the app
raises its "Direct to main" anomaly chip, and the generated summary
recommends tightening branch protections that are already in place.

This is not theoretical: a real per-person report reached a
direct-to-main figure above 90% this way, with a recommendation to
strictly disable direct pushes. A second repository was first assessed as
flipping correctly, on the basis that its 30-day window held no merge
commits and no PR references at all - and that assessment was wrong: its
last 200 first-parent commits held 42 merge commits, so the detector does
not flip and its every recent bare commit is mislabelled. That is the
mistake the slice warning below exists to prevent.

**Check, per repository in scope.** The detector and the metrics window
look at *different slices*, and this is the single easiest thing to get
wrong. The detector reads the **last 200 first-parent commits on the
graded branch regardless of date**; the mislabelling then happens to the
commits inside the 30-day metrics window. Checking markers only inside
the window - the intuitive thing to do - gives the wrong answer whenever
a repo merged normally in the past and has been landing bare commits
recently, which is a very common shape.

Run the detector's own query, verbatim:

```bash
R=<repo>; T=<branch the collector will actually grade>
OUT=$(git -C "$R" log "$T" --first-parent -n 200 --pretty=format:'%P|%s' --)
printf '%s
' "$OUT" | awk -F'|' '{n=split($1,a," "); if(n>=2) c++} END{print "multi_parent:", c+0}'
printf '%s
' "$OUT" | cut -d'|' -f2- | grep -cE '![0-9]+|\(pull request #[0-9]+\)|\(#[0-9]+\)'
```

Zero multi-parent commits **and** zero PR refs over those 200 means the
detector flips to "all reviewed" and the chip is suppressed. Any marker at
all, however old, means it does not flip. Then size the damage inside the
window:

```bash
W="30 days ago"
git -C "$R" log --since="$W" --oneline "$T" | wc -l                          # commits at risk
git -C "$R" log --since="$W" --merges --oneline "$T" | wc -l                 # of which reviewed via merge
git -C "$R" log --since="$W" --no-merges --format=%s "$T"   | grep -cE '![0-9]+|\(pull request #[0-9]+\)|\(#[0-9]+\)'               # of which reviewed via PR ref
```

Read the result:

| Markers in last 200 first-parent | Bare commits in window | Verdict |
| :--- | :--- | :--- |
| 0 | any | Detector flips; chip suppressed |
| **> 0** | **> 0** | **False-positive zone - every bare commit mislabelled direct** |
| > 0 | 0 | Chip is meaningful (everything in window really was reviewed) |
| Not checked | any | Treat as the false-positive zone until established |

**Record** in the registry row: `Squash-merge` (`Y` / `N` / `Unknown`) and
`Review markers present` (`Y` / `N`, meaning over the detector's 200-commit
slice, not the window), and set `Metrics validity` to
`Direct-to-main unreliable` when the pair lands in the false-positive
zone.

> [!CAUTION]
> **Fixing defect 1 can activate defect 2.** These two interact, and the
> interaction has been observed on a real repository. A repo whose trunk
> the collector cannot detect gets graded on a checked-out feature branch;
> that branch is often marker-free, so the detector flips and the chip
> stays suppressed. Check the real trunk out to fix the branch problem and
> the graded branch changes to one that *does* carry historical merge
> commits - the detector stops flipping, and every bare commit in the
> window is suddenly labelled a direct push. So always run the detector
> query against **the branch that will actually be graded after the
> defect-1 mitigation is applied**, not the branch checked out today, or
> the row records a suppressed chip that is about to start firing.

### The Other Side Of The Same Detector - PR Count Becomes Commit Count

When the detector *does* flip, every bare commit on the graded branch is
counted as one landed PR. So `pr_count` equals the commit count and
`review_hygiene` reads `direct: 0`, which looks like flawless review
discipline and is actually the absence of any review signal at all.

Verified 2026-09-03 on a real dry run: the operator's own row came back
with 265 commits and exactly 265 PRs, `via_merge: 265`, `direct: 0`, on a
feature branch the collector graded by fallback. Nobody opened 265 pull
requests.

This is the mirror image of the false-positive zone and it is easier to
miss, because the number flatters rather than accuses. Read the pair
together: `pr_count == commit_count` with `direct: 0` is a flipped
detector, not a track record. A row in that shape is `Direct-to-main
unreliable` for the same reason a red chip is - the review-hygiene split
carries no information either way - and its PR count must not reach
`individual_metrics` as a delivery figure.

The complementary shape is worth the same suspicion: a `configured`
contributor with real commits but `pr_count: 0` and zeros across
`review_hygiene` and `churn_pct` has had none of their window's work land
on the graded branch. Observed on a real submission (23 commits, 0 PRs,
all zeros) while auto-discovered peers in the same payload showed PRs, so
the person's own row read worse than everyone around them for reasons
unrelated to their work. Check this at handoff, from the person's own dry
run, before their first submission rather than after a report is written
from it.

**Mitigation.** The number cannot be fixed from outside the app, so the
mitigation is entirely about containment, and it has to happen *before*
the first submission rather than after someone reads the chip:

- Pre-empt it with the person at handoff. They will see a red chip about
  their own discipline that is an artifact; being told in advance is the
  difference between a shrug and a grievance.
- The registry row is the record that overrides the app. When anyone asks
  about that chip - the person, another manager, a review - the answer is
  the row, not the app.
- A `Direct-to-main unreliable` row must not reach `individual_metrics`,
  a risk level, a per-employee internal note in the app, a status report,
  or anything compensation-adjacent. Not softened, not caveated: not at
  all.
- Report the heuristic to the app owner with the repository shape that
  triggers it. Suppressing the chip for repositories detected as
  squash-merging, rather than only for repositories with no markers at
  all, is the fix.

## Defect 3 - Discovery Scope Trap

**What the code does.** The collector walks the configured root and
auto-discovers every git repository several levels deep, adding every
contributor it finds to that project's submission.

**Why it bites.** A developer's code folder is typically flat and shared
across clients - dozens of repositories spanning several unrelated
engagements is normal, not unusual. One key pointed at that folder
attributes every one of those clients' contributors to a single project.
The submission succeeds, the numbers look plausible, and nothing surfaces
the mistake.

**Check.** Enumerate what a candidate root would actually discover before
using it:

```bash
find <candidate-root> -maxdepth 4 -name .git -type d -printf '%h\n' | sort
```

Every path on that list must belong to `<Project>`. Anything else means
the root is wrong.

**Mitigation.** A per-client scoped root, always - never the person's code
folder. This is gate item 2, not a recommendation; see
`precondition-gate.md`. If the person's repositories are not already
arranged so a per-client root is possible, arranging them is part of the
onboarding, before the key is issued.

## Deriving `Metrics validity`

Combine the per-repository findings into one row value:

- `Reliable` - every repository in scope has a detected trunk, and none is
  in the direct-to-main false-positive zone.
- `Branch-dependent` - at least one repository grades on the checkout.
- `Direct-to-main unreliable` - at least one repository is in the
  false-positive zone.
- `Both` - both of the above.

Only `Reliable` permits the `individual_metrics` cascade edge. The other
three values are what the registry exists to carry: they are the reason a
number in the app is not automatically a fact about a person.
